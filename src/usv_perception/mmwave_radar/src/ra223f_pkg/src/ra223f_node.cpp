#include "rclcpp/rclcpp.hpp"
#include "rclcpp/executors/multi_threaded_executor.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"
#include "sensor_msgs/point_cloud2_iterator.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "geometry_msgs/msg/twist_stamped.hpp"

#include <cstdint>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <vector>
#include <string>

#include <chrono>
#include <cmath>
#include <cctype>
#include <iostream>

#include "udp_interface.h"
#include "visualization_msgs/msg/marker.hpp"
#include "visualization_msgs/msg/marker_array.hpp"

// 将秒和纳秒转换为 ROS 时间
rclcpp::Time ptp_to_system_time(int64_t seconds, int64_t nanoseconds) {
    return rclcpp::Time(seconds, nanoseconds);
}

// 用于处理协议中“4字节浮点”与“字节数组”的转换
typedef union{
    uint8_t data_u8[4];
    float data_float;
}union_conv_t; 

// 点云单点的解析缓存
struct RadarPoint {
    float range = 0.0f;
    float amb_rangerate = 0.0f;
    float unamb_rangerate = 0.0f;
    float azimuth_deg = 0.0f;
    float elevation_deg = 0.0f;
    float snr = 0.0f;
    float rcs = 0.0f;
    float confidence = 0.0f;
    uint8_t unamb_rangeratemask = 0U;
    float snr_azi = 0.0f;
};

// 单目标的解析缓存
struct RadarObject {
    uint8_t track_id = 0U;
    float xpos_vcs = 0.0f;
    float ypos_vcs = 0.0f;
    float zpos_vcs = 0.0f;
    float xvel_abs = 0.0f;
    float yvel_abs = 0.0f;
    float xacc_abs = 0.0f;
    float yacc_abs = 0.0f;
    float heading_angle = 0.0f;
    float box_width = 0.0f;
    float box_length = 0.0f;
    float box_heigh = 0.0f;
    uint8_t classify_type = 0U;
    float classify_prob = 0.0f;
    uint16_t objmotion_status = 0U;
    uint16_t obstacle_prob = 0U;
};

// UDP 端点（IP + 端口）
struct UdpEndpoint {
    std::string ip;
    uint16_t port = 0U;
};

class mmw_radar:public rclcpp::Node {
private:
    std::string frame_id_ = "mmw_radar";
    // UDP 接收缓冲与来源地址（组播接收）
    struct sockaddr_in source_address;
    char rec_data[40000];
    int recv_len;

    // 生产者/消费者队列
    std::queue<std::vector<char>> data_queue_;          // 数据队列
    std::mutex queue_mutex_;                            // 队列互斥锁
    std::condition_variable queue_cv_;                  // 条件变量

    // UDP 管理：同时承担“组播接收端(socket_server_fd)”与“单播发送端(socket_client_fd)”
    UdpInterface udp_io;

    // 发布：点云 PointCloud2
    rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pub_pointPtr_PointCloud2_;
    // 发布：目标列表（PointCloud2 表达）
    rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pub_object_pc2_;

    // 发布：目标方框 MarkerArray（RViz 绘制用）
    rclcpp::Publisher<visualization_msgs::msg::MarkerArray>::SharedPtr pub_object_marker_;

    // Odometry -> 雷达姿态/车速注入（UDP 单播发送）
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_subscription_;

    // 外部车速/角速度（yawRate）来源：用于替代/补全 Odometry 中的 speed/yawRate
    rclcpp::Subscription<geometry_msgs::msg::TwistStamped>::SharedPtr vehicle_speed_subscription_;
    rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr imu_subscription_;

    std::mutex odom_mutex_;
    std::mutex motion_mutex_;
    std::mutex inject_mutex_;                       // 保护注入序号与 UDP 发送，避免并发回调冲突
    nav_msgs::msg::Odometry latest_odom_;
    bool has_odom_ = false;
    uint64_t odom_recv_count_ = 0U;                 // 统计收到 odom 的次数（调试用）
    bool udp_unicast_warned_once_ = false;          // UDP未初始化时只报警一次（避免刷屏）
    double latest_speed_mps_ = 0.0;
    bool has_speed_ = false;
    double latest_yaw_rate_radps_ = 0.0;
    bool has_yaw_rate_ = false;
    double latest_longitudinal_accel_mps2_ = 0.0;
    bool has_longitudinal_accel_ = false;

    // 单播发送是否初始化成功：失败则禁用注入
    bool udp_unicast_ok_ = false;
    // 0xAA31 包序号
    uint16_t inject_package_num_ = 0U;
    // 0xAA31 协议中 data_buf[16..17]：与雷达/项目约定一致
    // 当前实现：0 = 倒挡（纵向速度为负），1 = 前进/空挡等（纵向速度非负）；默认 1
    int16_t ego_gear_status_ = 1;
    // 无 odom 时：仅当 VCU 车速为带符号纵向速度（倒车为负）才可用 speed_mps 更新挡位；默认 false
    bool vehicle_speed_is_signed_longitudinal_ = false;

    // 协议校验：对 data_buf[0..last_index] 逐字节求和并取 uint8
    static uint8_t calc_checkSum(const uint8_t* p_data_buf, uint16_t last_index) {
        uint16_t check_sum = 0;
        for (uint16_t index = 0U; index <= last_index; index++) {
            check_sum += p_data_buf[index];
        }
        return static_cast<uint8_t>(check_sum);
    }

    void odom_callback(const nav_msgs::msg::Odometry::SharedPtr msg) {
        {
            std::lock_guard<std::mutex> lk(odom_mutex_);
            latest_odom_ = *msg;
            has_odom_ = true;
        }
        odom_recv_count_++;
        send_inject_packet_from_cache();
        // RCLCPP_INFO(this->get_logger(),"odo 注入!..........");
    }

    // 车速：geometry_msgs/TwistStamped，twist.linear.x 为 kph → m/s（÷3.6）
    void vehicle_speed_callback(const geometry_msgs::msg::TwistStamped::SharedPtr msg) {
        {
            std::lock_guard<std::mutex> lk(motion_mutex_);
            latest_speed_mps_ = static_cast<double>(msg->twist.linear.x) / 3.6;
            has_speed_ = true;
        }
        send_inject_packet_from_cache();
        // RCLCPP_INFO(this->get_logger(),"twis 注入!..........");
    }

    void imu_callback(const sensor_msgs::msg::Imu::SharedPtr msg) {
        {
            std::lock_guard<std::mutex> lk(motion_mutex_);
            latest_yaw_rate_radps_ = static_cast<double>(msg->angular_velocity.z);
            latest_longitudinal_accel_mps2_ = static_cast<double>(msg->linear_acceleration.x);
            has_yaw_rate_ = true;
            has_longitudinal_accel_ = true;
        }
        send_inject_packet_from_cache();
        // RCLCPP_INFO(this->get_logger(),"imu 注入!..........");
    }

    void send_inject_packet_values(double speed_mps, double yaw_rate_radps) {
        if (!udp_unicast_ok_) {
            if (!udp_unicast_warned_once_) {
                udp_unicast_warned_once_ = true;
                RCLCPP_WARN(this->get_logger(), "UDP单播未初始化成功：跳过注入(speed/yawRate -> radar)");
            }
            return;
        }

        // 如果回调由多线程执行器触发，注入序号与 UDP 发送要序列化
        std::lock_guard<std::mutex> lk(inject_mutex_);

        int16_t yaw_rate_int = static_cast<int16_t>(yaw_rate_radps * 10000.0);
        int16_t speed_int = static_cast<int16_t>(speed_mps * 100.0);

        uint8_t data_buf[32] = {0x00};
        data_buf[0] = 0xAA;
        data_buf[1] = 0x31;
        data_buf[2] = 0x00;
        data_buf[3] = 32;

        //姿态包发送计数
        data_buf[4] = static_cast<uint8_t>((inject_package_num_ & 0xFF00) >> 8);
        data_buf[5] = static_cast<uint8_t>(inject_package_num_ & 0x00FF);

        //rawRate
        data_buf[6] = static_cast<uint8_t>((yaw_rate_int & 0xFF00) >> 8);
        data_buf[7] = static_cast<uint8_t>(yaw_rate_int & 0x00FF);

        //vehicleSpeed
        data_buf[8] = static_cast<uint8_t>((speed_int & 0xFF00) >> 8);
        data_buf[9] = static_cast<uint8_t>(speed_int & 0x00FF);

        //move_direction 0:R  1:... : N/D/M/S
        data_buf[16] = static_cast<uint8_t>((ego_gear_status_ & 0xFF00) >> 8);
        data_buf[17] = static_cast<uint8_t>(ego_gear_status_ & 0x00FF);

        data_buf[31] = calc_checkSum(data_buf, 31);
        (void)udp_io.sendToRadar(reinterpret_cast<const char*>(data_buf), 32, 200);
        inject_package_num_ = static_cast<uint16_t>(inject_package_num_ + 1U);
    }

    // 事件触发：上述三路话题任一收到消息时调用；按当前缓存合成一包 0xAA31（非互斥、互补填包）
    void send_inject_packet_from_cache() {
        double speed_mps = 0.0;
        double yaw_rate = 0.0;
        {
            std::lock_guard<std::mutex> lk(motion_mutex_);
            speed_mps = latest_speed_mps_;
            yaw_rate = latest_yaw_rate_radps_;
            ego_gear_status_ = (speed_mps < 0.0) ? static_cast<int16_t>(0) : static_cast<int16_t>(1);
        }

        //判断odm话题是否触发
        nav_msgs::msg::Odometry odom;
        bool has_odom = false;
        {
            std::lock_guard<std::mutex> lk(odom_mutex_);
            has_odom = has_odom_;
            if (has_odom) {
                odom = latest_odom_;
                has_odom_ = false;
            }
        }

        //odm话题触发注入功能
        if (has_odom) {
            const double vx = odom.twist.twist.linear.x;
            const double vy = odom.twist.twist.linear.y;
            speed_mps = std::sqrt(vx * vx + vy * vy);
            yaw_rate = odom.twist.twist.angular.z;
            ego_gear_status_ = (vx < 0.0) ? static_cast<int16_t>(0) : static_cast<int16_t>(1);
        }

        //向雷达转发相关姿态信息
        send_inject_packet_values(fabsf(speed_mps), yaw_rate);
    }

    // 将指定 Odometry 打包为 0xAA31 并通过 UDP 单播发送给雷达
    void send_inject_packet(const nav_msgs::msg::Odometry& odom) {
        // 线速度：取平面速度模长（适用于车辆常见里程计定义）
        const double vx = odom.twist.twist.linear.x;
        const double vy = odom.twist.twist.linear.y;
        const double speed = std::sqrt(vx * vx + vy * vy);
        
        // 角速度：直接使用 yaw 角速度（rad/s）
        const double yaw_rate = odom.twist.twist.angular.z;

        // 用车体纵向速度 vx 符号推断：0=倒挡，1=前进等（与 send_inject_packet_from_cache 一致）
        ego_gear_status_ = (vx < 0.0) ? static_cast<int16_t>(0) : static_cast<int16_t>(1);
        send_inject_packet_values(speed, yaw_rate);
    }

    //构建udp的生产者与消费者线程
    std::thread udp_thread;
    std::thread udp_doWork_thread;

public:
    ~mmw_radar(){
        udp_io.closeAllSockets();

        //释放线程资源，线程中有超时机，等待线程结束
        if(udp_thread.joinable()){
            udp_thread.join();
        }

        if(udp_doWork_thread.joinable()) {
            udp_doWork_thread.join();
        }
    }

    explicit mmw_radar(
        const std::string& node_name,
        const UdpEndpoint& multicast_endpoint,
        const UdpEndpoint& unicast_endpoint,
        
        int local_port_start = 50000,
        int local_port_end = 65535,
        std::string odom_topic = "/mavros/local_position/odom",                 //注意根据不同的姿态传感器发生的话题不同进行对应更改话题名
        std::string vehicle_speed_topic = "/VCU_status/vehicle_feedback",
        std::string imu_topic = "/imu/data",
        std::string pointCloud_topicName = "/mmw_radar/pointcloud_topic",
        std::string object_topicName = "/mmw_radar/objectList_topic",
        std::string object_marker_topicName = "/mmw_radar/object_marker",
        std::string frame_id = "mmw_radar",
        std::string use_networkCard_Ip = "0.0.0.0",                             //在多网卡时需要设置待使用网卡对应的ip地址，默认系统只有一张网卡
        bool vehicle_speed_is_signed_longitudinal = false
    ) : Node(node_name) {
        frame_id_ = frame_id;
        //创建基于sensor_msgs_pointcloud2类型的点云话题
        pub_pointPtr_PointCloud2_ = this->create_publisher<sensor_msgs::msg::PointCloud2>(pointCloud_topicName, 10);
        
        // 初始化航迹 PointCloud2 发布者（话题名：/ra223f/object_pointcloud2）
        pub_object_pc2_ = this->create_publisher<sensor_msgs::msg::PointCloud2>(object_topicName, 10);

        // 初始化航迹方框 MarkerArray 发布者（话题名：/ra223f/object_marker）
        pub_object_marker_ = this->create_publisher<visualization_msgs::msg::MarkerArray>(object_marker_topicName, 10);

        // ====================== UDP 单播客户端（用于向雷达注入 Odometry）======================
        int ret_unicast = -1;
        for (int attempt = local_port_start; attempt <= local_port_end; attempt++) {
            ret_unicast = udp_io.initUdpUnicastClient(unicast_endpoint.ip, static_cast<int>(unicast_endpoint.port), attempt);
            if (ret_unicast == 0) {
                udp_unicast_ok_ = true;
                RCLCPP_INFO(this->get_logger(), "UDP单播初始化成功: %s:%d, local_port=%d",
                            unicast_endpoint.ip.c_str(), static_cast<int>(unicast_endpoint.port), attempt);
                break;
            }
        }
        if (!udp_unicast_ok_) {
            RCLCPP_WARN(this->get_logger(), "UDP单播初始化失败，将不会注入Odometry到雷达");
        }

        // ====================== 订阅 Odometry 并即时注入 =======================
        const std::string odom_topic_effective =
            this->declare_parameter<std::string>("odom_topic", odom_topic);

        // 与 /mavros/* 的 rosbag 发布端可能使用 BestEffort QoS 对齐，避免 RELIABILITY 不兼容导致收不到消息
        rclcpp::QoS qos_odom(rclcpp::KeepLast(10));
        qos_odom.best_effort();
        odom_subscription_ = this->create_subscription<nav_msgs::msg::Odometry>(
            odom_topic_effective, qos_odom, std::bind(&mmw_radar::odom_callback, this, std::placeholders::_1));

        // ====================== 订阅车速（VCU feedback） =======================
        // geometry_msgs/TwistStamped：twist.linear.x 为 kph，回调内 ÷3.6 转为 m/s
        const std::string vehicle_speed_topic_effective =
            this->declare_parameter<std::string>("vehicle_speed_topic", vehicle_speed_topic);

        vehicle_speed_is_signed_longitudinal_ =
            this->declare_parameter<bool>("vehicle_speed_is_signed_longitudinal", vehicle_speed_is_signed_longitudinal);

        vehicle_speed_subscription_ = this->create_subscription<geometry_msgs::msg::TwistStamped>(
            vehicle_speed_topic_effective, 10,
            std::bind(&mmw_radar::vehicle_speed_callback, this, std::placeholders::_1));

        // ====================== 订阅 IMU（yawRate、纵向加速度） =======================
        const std::string imu_topic_effective =
            this->declare_parameter<std::string>("imu_topic", imu_topic);
        imu_subscription_ = this->create_subscription<sensor_msgs::msg::Imu>(
            imu_topic_effective, 10,
            std::bind(&mmw_radar::imu_callback, this, std::placeholders::_1));

        //配置组播通信
        const std::string multicast_interface_ip =
            this->declare_parameter<std::string>("multicast_interface_ip", use_networkCard_Ip);
        if (!multicast_interface_ip.empty() && multicast_interface_ip != "0.0.0.0") {
            RCLCPP_INFO(this->get_logger(), "组播接口IP: %s", multicast_interface_ip.c_str());
        } else {
            RCLCPP_INFO(this->get_logger(), "组播接口IP: auto(0.0.0.0)");
        }

        int ret = udp_io.initUdpMulticastServer(
            multicast_endpoint.ip,
            static_cast<int>(multicast_endpoint.port),
            multicast_interface_ip
        );
        if(ret == 0) {
            //创建udp数据接受与处理的生产者与消费者模式线程
            RCLCPP_INFO(
                this->get_logger(),
                "[%s] 组播初始化成功: %s:%u (iface=%s)",
                this->get_name(),
                multicast_endpoint.ip.c_str(),
                static_cast<unsigned>(multicast_endpoint.port),
                multicast_interface_ip.c_str()
            );
            udp_thread = std::thread(&mmw_radar::udp_recv_callback,this);
            udp_doWork_thread = std::thread(&mmw_radar::udp_recv_doWork,this);
        }
        else {
            RCLCPP_WARN(
                this->get_logger(),
                "[%s] 组播初始化失败: %s:%u (iface=%s)",
                this->get_name(),
                multicast_endpoint.ip.c_str(),
                static_cast<unsigned>(multicast_endpoint.port),
                multicast_interface_ip.c_str()
            );
        }
    }

    //udp数据接受处理线程（生产者）
    void udp_recv_callback(void) {
        udp_io.setNonBlocking(0);

        //接受udp缓冲区中的相关数据并将这些数据添加到队列中
        while(rclcpp::ok()) {
            udp_io.receiveWithTimeout(&source_address, rec_data, recv_len, 1000);
            
            if(recv_len > 0) {
                std::vector<char> buffer(rec_data, rec_data + recv_len);
                {
                    std::lock_guard<std::mutex> lock(queue_mutex_);
                    data_queue_.push(buffer);
                }
                queue_cv_.notify_one();
            }
            else {
                continue;
            }
        }
    }

    //执行数据的解析操作 (消费者)
    void udp_recv_doWork(void) {
        uint16_t pointcloud_frame_id = 0;
        uint16_t pointcloud_num = 0;
        uint16_t pointcloud_timestamp = 0;
        float pointcloud_max_unamb_speed = 0.0f;
        uint8_t pointcloud_workmode = 0U;
        uint64_t pointcloud_ptp_s = 0U;
        uint32_t pointcloud_ptp_ns = 0U;
        std::vector<RadarPoint> points;

        uint16_t object_frame_id = 0;
        uint8_t object_num = 0U;
        std::vector<RadarObject> objects;
        RadarPoint t_PointCloud;
        RadarObject t_ObjectAtt;
        RadarPoint* p_PointCloud = nullptr;
        RadarObject* p_ObjectAtt = nullptr;

        uint16_t messageType;       //报文类型
        uint16_t messageLen;        //报文数据长度

        // uint8_t checkSum = 0x00; //校验和

        union_conv_t union_conv;    //多字节数据转换工具

        uint16_t savePointCloudCount = 0;
        uint16_t saveObjectNum = 0;

        uint16_t numPointCloudInPackage = 0;
        uint16_t numObjectInPackage = 0;

        uint8_t *p_data = nullptr;

        volatile uint8_t findPointCloudHeader = 0x00;
        volatile uint8_t findObjectHeader = 0x00;
        uint8_t *data_recvBuf = nullptr;

        uint64_t ptp_s;
        uint32_t ptp_ns;

        //系统时间
        rclcpp::Time radar_ptp_time;

        //解析线程主题
        while (rclcpp::ok()) {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            bool hs_data = queue_cv_.wait_for(lock,std::chrono::milliseconds(100),[this]{
                return !data_queue_.empty(); 
            });

            if(!hs_data) {
                //超时触发，没有数据继续检查推出条件
                lock.unlock();
                continue;  
            }
            
            //有数据，读取出相关数据进行数据处理解析操作
            auto data = data_queue_.front();
            data_queue_.pop();
            lock.unlock();

            //进行数据解析逻辑
            data_recvBuf = (uint8_t*)&data[0];
            messageType = (uint16_t)(data_recvBuf[0] << 8 |  data_recvBuf[1]);
            messageLen = (uint16_t) (data_recvBuf[2] << 8 |  data_recvBuf[3]);
            //checkSum = (uint8_t) data_recvBuf[messageLen - 1U];   //获取当前帧的校验和

            switch(messageType) {
                //解析点云头信息
                case 0xAA80:
                    //清空点云临时缓冲区
                    pointcloud_frame_id = 0;
                    pointcloud_num = 0;
                    pointcloud_timestamp = 0;
                    points.clear();

                    //设置当前帧接受到的点云数量与帧id
                    pointcloud_frame_id = static_cast<uint16_t>(data_recvBuf[6] << 8 | data_recvBuf[7]);           //循环计数0~65535
                    pointcloud_num = static_cast<uint16_t>(data_recvBuf[8] << 8 | data_recvBuf[9]);                 //当前帧最大点云数量
                    pointcloud_timestamp = static_cast<uint16_t>(data_recvBuf[10] << 8 | data_recvBuf[11]);         //内部计数器时间戳,0~65535 精度1ms

                    //嵌入式传入错误，嵌入式为小端模式(历史数据兼容问题)
                    union_conv.data_u8[0] = data_recvBuf[15]; 
                    union_conv.data_u8[1] = data_recvBuf[14]; 
                    union_conv.data_u8[2] = data_recvBuf[13]; 
                    union_conv.data_u8[3] = data_recvBuf[12]; 
                    pointcloud_max_unamb_speed = union_conv.data_float;               //当前帧最大非模糊速度 m/s
                    
                    //解析雷达的工作模式
                    pointcloud_workmode = data_recvBuf[16];                           //工作模式 0 1  100模式 300m模式

                    RCLCPP_DEBUG(
                        this->get_logger(),
                        "PointCloud header: frame_id=%u num=%u ts=%u(ms) max_unamb_speed=%.3f(m/s) mode=%u",
                        static_cast<unsigned>(pointcloud_frame_id),
                        static_cast<unsigned>(pointcloud_num),
                        static_cast<unsigned>(pointcloud_timestamp),
                        static_cast<double>(pointcloud_max_unamb_speed),
                        static_cast<unsigned>(pointcloud_workmode)
                    );

                    //解析ptp时间 秒(s)
                    pointcloud_ptp_s =  ((uint64_t)data_recvBuf[52] << 56) |
                                        ((uint64_t)data_recvBuf[53] << 48) |
                                        ((uint64_t)data_recvBuf[54] << 40) |
                                        ((uint64_t)data_recvBuf[55] << 32) |
                                        ((uint64_t)data_recvBuf[56] << 24) |
                                        ((uint64_t)data_recvBuf[57] << 16) |
                                        ((uint64_t)data_recvBuf[58] << 8)  |
                                        (uint64_t)data_recvBuf[59];

                    //解析ptp时间ns(ns)
                    pointcloud_ptp_ns = ((uint32_t)data_recvBuf[60] << 24) |
                                        ((uint32_t)data_recvBuf[61] << 16) |
                                        ((uint32_t)data_recvBuf[62] << 8) |
                                        ((uint32_t)data_recvBuf[63]);

                    //同步保存点云的ptp时间信息用于objectList的ptp时间戳填充
                    ptp_s = pointcloud_ptp_s;
                    ptp_ns = pointcloud_ptp_ns;

                    //输出时间戳信息,调试用
                    // RCLCPP_INFO(this->get_logger(),"s: %ld, ns: %d", ptp_s,ptp_ns);
                    radar_ptp_time = ptp_to_system_time(ptp_s,ptp_ns);

                    savePointCloudCount = 0;
                    findPointCloudHeader = 0x01;
                break;

                //解析点云信息
                case 0xAA81:
                    if(0x01 == findPointCloudHeader) {

                        numPointCloudInPackage = (messageLen - 9) / 20;   //获取当前报文里面含有点云个数
                        if(savePointCloudCount < pointcloud_num) {
                            for(uint16_t idx = 0; idx < numPointCloudInPackage; idx++) {
                                p_PointCloud = &t_PointCloud;
                                //设置点云的相应熟悉
                                p_data = &data_recvBuf[8 + idx * 20];

                                p_PointCloud->range = static_cast<uint32_t>(p_data[0] << 24 | p_data[1] << 16 | p_data[2] << 8 | p_data[3]) * 0.01f; // 径向距离 m
                                p_PointCloud->amb_rangerate = static_cast<int16_t>(p_data[4] << 8 | p_data[5]) * 0.01f;        //模糊速度   m/s 点云算法处理结果
                                p_PointCloud->unamb_rangerate = static_cast<int16_t>(p_data[6] << 8 | p_data[7]) * 0.01f;      //非模糊速度  m/s 数据处理算法结果 解模糊操作
                                p_PointCloud->azimuth_deg = static_cast<int16_t>(p_data[8] << 8 | p_data[9]) * 0.01f;          //方位角 度
                                p_PointCloud->elevation_deg = static_cast<int16_t>(p_data[10] << 8 | p_data[11]) *0.01f;       //抚养角 度
                                p_PointCloud->snr = static_cast<int16_t>(p_data[12] << 8 | p_data[13]) * 0.01f;                //信噪比 RD域结果
                                p_PointCloud->rcs = static_cast<int16_t>(p_data[14] << 8 | p_data[15]) * 0.0039f;              //rcs
                                p_PointCloud->confidence = p_data[16] * 0.01f;
                                p_PointCloud->unamb_rangeratemask = p_data[17];                                     //数据处理点云是否速度解模糊成功标志 0x00:成功 0x01:可能成功也可能失败 0x02:失败
                                p_PointCloud->snr_azi = static_cast<int16_t>((p_data[18] << 8) | (p_data[19])) * 0.01f;        //信噪比 方位维

                                points.push_back(t_PointCloud);
                            }

                            savePointCloudCount += numPointCloudInPackage;
                        }
                        
                        // 点云数据解析完毕：使用 points.size() 判断是否凑够一帧
                        // 原实现用 savePointCloudCount == pointcloud_num，过于严格；
                        // 在不同端口/报文长度计算存在细微差异时，可能导致整帧不发布。
                        if(pointcloud_num > 0 && points.size() >= static_cast<size_t>(pointcloud_num)) {   
                            findPointCloudHeader = 0x00;

                            
                            // 检查点数量是否有效
                            if (pointcloud_num == 0) {
                                RCLCPP_WARN(this->get_logger(), "No valid points, skip publishing PointCloud2");
                                break;
                            }

                            sensor_msgs::msg::PointCloud2 cloud_msg;    //用于发布点云相关信息

                            // 初始化PointCloud2消息
                            cloud_msg.header.stamp = radar_ptp_time;
                            cloud_msg.header.frame_id = frame_id_;
                            cloud_msg.width = pointcloud_num;
                            cloud_msg.height = 1;
                            cloud_msg.is_dense = false;
                            cloud_msg.is_bigendian = false;

                            // ====================== 点云字段：发布协议解析得到的所有字段 ======================
                            // x/y/z 为转换后的笛卡尔坐标；其余字段与协议字段一一对应（统一用 float32 发布，便于 RViz/下游解析）
                            sensor_msgs::msg::PointField field_x;
                            field_x.name = "x";
                            field_x.offset = 0;
                            field_x.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_x.count = 1;

                            sensor_msgs::msg::PointField field_y;
                            field_y.name = "y";
                            field_y.offset = 4;
                            field_y.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_y.count = 1;

                            sensor_msgs::msg::PointField field_z;
                            field_z.name = "z";
                            field_z.offset = 8;
                            field_z.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_z.count = 1;

                            sensor_msgs::msg::PointField field_range;
                            field_range.name = "range";
                            field_range.offset = 12;
                            field_range.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_range.count = 1;

                            sensor_msgs::msg::PointField field_amb_rangerate;
                            field_amb_rangerate.name = "amb_rangerate";
                            field_amb_rangerate.offset = 16;
                            field_amb_rangerate.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_amb_rangerate.count = 1;

                            sensor_msgs::msg::PointField field_unamb_rangerate;
                            field_unamb_rangerate.name = "unamb_rangerate";
                            field_unamb_rangerate.offset = 20;
                            field_unamb_rangerate.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_unamb_rangerate.count = 1;

                            // 兼容字段：保持原先的 rangerate（= unamb_rangerate）
                            sensor_msgs::msg::PointField field_rangerate;
                            field_rangerate.name = "rangerate";
                            field_rangerate.offset = 24;
                            field_rangerate.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_rangerate.count = 1;

                            sensor_msgs::msg::PointField field_azimuth_deg;
                            field_azimuth_deg.name = "azimuth_deg";
                            field_azimuth_deg.offset = 28;
                            field_azimuth_deg.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_azimuth_deg.count = 1;

                            sensor_msgs::msg::PointField field_elevation_deg;
                            field_elevation_deg.name = "elevation_deg";
                            field_elevation_deg.offset = 32;
                            field_elevation_deg.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_elevation_deg.count = 1;

                            sensor_msgs::msg::PointField field_snr;
                            field_snr.name = "snr";
                            field_snr.offset = 36;
                            field_snr.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_snr.count = 1;

                            sensor_msgs::msg::PointField field_rcs;
                            field_rcs.name = "rcs";
                            field_rcs.offset = 40;
                            field_rcs.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_rcs.count = 1;

                            sensor_msgs::msg::PointField field_confidence;
                            field_confidence.name = "confidence";
                            field_confidence.offset = 44;
                            field_confidence.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_confidence.count = 1;

                            sensor_msgs::msg::PointField field_unamb_rangeratemask;
                            field_unamb_rangeratemask.name = "unamb_rangeratemask";
                            field_unamb_rangeratemask.offset = 48;
                            field_unamb_rangeratemask.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_unamb_rangeratemask.count = 1;

                            sensor_msgs::msg::PointField field_snr_azi;
                            field_snr_azi.name = "snr_azi";
                            field_snr_azi.offset = 52;
                            field_snr_azi.datatype = sensor_msgs::msg::PointField::FLOAT32;
                            field_snr_azi.count = 1;

                            // 清空并添加字段
                            cloud_msg.fields.clear();
                            cloud_msg.fields.push_back(field_x);
                            cloud_msg.fields.push_back(field_y);
                            cloud_msg.fields.push_back(field_z);
                            cloud_msg.fields.push_back(field_range);
                            cloud_msg.fields.push_back(field_amb_rangerate);
                            cloud_msg.fields.push_back(field_unamb_rangerate);
                            cloud_msg.fields.push_back(field_rangerate);
                            cloud_msg.fields.push_back(field_azimuth_deg);
                            cloud_msg.fields.push_back(field_elevation_deg);
                            cloud_msg.fields.push_back(field_snr);
                            cloud_msg.fields.push_back(field_rcs);
                            cloud_msg.fields.push_back(field_confidence);
                            cloud_msg.fields.push_back(field_unamb_rangeratemask);
                            cloud_msg.fields.push_back(field_snr_azi);

                            // 设置步长和数据内存
                            cloud_msg.point_step = 56;  // 14个FLOAT32 × 4字节
                            cloud_msg.row_step = cloud_msg.width * cloud_msg.point_step;
                            cloud_msg.data.resize(cloud_msg.row_step * cloud_msg.height);

                            // 创建迭代器（此时字段已确认存在）
                            sensor_msgs::PointCloud2Iterator<float> iter_x(cloud_msg, "x");
                            sensor_msgs::PointCloud2Iterator<float> iter_y(cloud_msg, "y");
                            sensor_msgs::PointCloud2Iterator<float> iter_z(cloud_msg, "z");
                            
                            sensor_msgs::PointCloud2Iterator<float> iter_range(cloud_msg, "range");
                            sensor_msgs::PointCloud2Iterator<float> iter_amb_rangerate(cloud_msg, "amb_rangerate");
                            sensor_msgs::PointCloud2Iterator<float> iter_unamb_rangerate(cloud_msg, "unamb_rangerate");
                            sensor_msgs::PointCloud2Iterator<float> iter_rangerate(cloud_msg, "rangerate");
                            sensor_msgs::PointCloud2Iterator<float> iter_azimuth_deg(cloud_msg, "azimuth_deg");
                            sensor_msgs::PointCloud2Iterator<float> iter_elevation_deg(cloud_msg, "elevation_deg");
                            sensor_msgs::PointCloud2Iterator<float> iter_snr(cloud_msg, "snr");
                            sensor_msgs::PointCloud2Iterator<float> iter_rcs(cloud_msg, "rcs");
                            sensor_msgs::PointCloud2Iterator<float> iter_confidence(cloud_msg, "confidence");
                            sensor_msgs::PointCloud2Iterator<float> iter_unamb_rangeratemask(cloud_msg, "unamb_rangeratemask");
                            sensor_msgs::PointCloud2Iterator<float> iter_snr_azi(cloud_msg, "snr_azi");

                            // 填充数据
                            for (size_t i = 0; i < cloud_msg.width; ++i) {  
                                t_PointCloud = points[i];
                                float azimuth_rad = M_PI * t_PointCloud.azimuth_deg / 180.0f;
                                float elevation_rad = M_PI * t_PointCloud.elevation_deg / 180.0f;
                                float range = t_PointCloud.range;

                                *iter_x = range * cos(elevation_rad) * cos(azimuth_rad);
                                *iter_y = range * cos(elevation_rad) * sin(azimuth_rad);
                                *iter_z = range * sin(elevation_rad);

                                *iter_range = t_PointCloud.range;
                                *iter_amb_rangerate = t_PointCloud.amb_rangerate;
                                *iter_unamb_rangerate = t_PointCloud.unamb_rangerate;
                                *iter_rangerate = t_PointCloud.unamb_rangerate;  // 兼容字段
                                *iter_azimuth_deg = t_PointCloud.azimuth_deg;
                                *iter_elevation_deg = t_PointCloud.elevation_deg;
                                *iter_snr = t_PointCloud.snr;
                                *iter_rcs = t_PointCloud.rcs;
                                *iter_confidence = t_PointCloud.confidence;
                                *iter_unamb_rangeratemask = static_cast<float>(t_PointCloud.unamb_rangeratemask);
                                *iter_snr_azi = t_PointCloud.snr_azi;

                                ++iter_x;
                                ++iter_y;
                                ++iter_z;
                                ++iter_range;
                                ++iter_amb_rangerate;
                                ++iter_unamb_rangerate;
                                ++iter_rangerate;
                                ++iter_azimuth_deg;
                                ++iter_elevation_deg;
                                ++iter_snr;
                                ++iter_rcs;
                                ++iter_confidence;
                                ++iter_unamb_rangeratemask;
                                ++iter_snr_azi;
                            }

                            // ====================== 发布PointCloud2消息 ======================
                            pub_pointPtr_PointCloud2_->publish(cloud_msg);
                        }
                    }
                break;

                //解析objectList报文
                case 0xAA90:
                    // 0xAA90 目标列表头：
                    objects.clear();
                    object_num = 0U;
                    object_frame_id = static_cast<uint16_t>((data_recvBuf[6] << 8) | (data_recvBuf[7])); //帧计数 0~65535 循环计数
                    object_num = data_recvBuf[8];   //获取得到object个数

                    RCLCPP_DEBUG(
                        this->get_logger(),
                        "Object header: frame_id=%u num=%u",
                        static_cast<unsigned>(object_frame_id),
                        static_cast<unsigned>(object_num)
                    );

                    //获取ptp时间
                    (void)ptp_s;
                    (void)ptp_ns;

                    saveObjectNum = 0;
                    findObjectHeader = 0x01;
                break;

                //解析object报文
                case 0xAA91:
                if(findObjectHeader == 0x01) {
                    // 0xAA91 目标数据：每目标 43 字节，从 data_recvBuf[9] 开始连续排布
                    numObjectInPackage  = (messageLen - 10) / 43;   //获取当前报文里面含有点云个数
                    if(saveObjectNum <  object_num ) {
                        p_ObjectAtt = &t_ObjectAtt ;
                        for(uint16_t idx = 0; idx < numObjectInPackage; idx++) {
                            //设置点云的i相应属性
                            p_data = &data_recvBuf[9 + idx * 43];

                            p_ObjectAtt->track_id = p_data[0];      //航迹的id号
                            p_ObjectAtt->xpos_vcs =  static_cast<int16_t>( p_data[1] << 8 | p_data[2]) * 0.01f;      //纵向距离 m
                            p_ObjectAtt->ypos_vcs =  static_cast<int16_t>( p_data[3] << 8 | p_data[4]) * 0.01f;      //横向距离 m
                            p_ObjectAtt->zpos_vcs =  static_cast<int16_t>( p_data[5] << 8 | p_data[6]) * 0.01f;      //垂直距离 m

                            p_ObjectAtt->xvel_abs =  static_cast<int16_t>( p_data[7] << 8 | p_data[8]) * 0.01f;      //纵向速度 m/s
                            p_ObjectAtt->yvel_abs =  static_cast<int16_t>( p_data[9] << 8 | p_data[10]) * 0.01f;     //横向速度 m/s

                            p_ObjectAtt->xacc_abs =  static_cast<int16_t>( p_data[11] << 8 | p_data[12]) * 0.01f;    //纵向加速度 m/s^2
                            p_ObjectAtt->yacc_abs =  static_cast<int16_t>( p_data[13] << 8 | p_data[14]) * 0.01f;    //横向加速度 m/s^2

                            p_ObjectAtt->heading_angle =  static_cast<int16_t>( p_data[15] << 8 | p_data[16]) * 0.01f; //航向角度 左正右负

                            p_ObjectAtt->box_width =  static_cast<uint16_t>( p_data[17] << 8 | p_data[18]) * 0.01f;    //航迹的包围框长宽高
                            p_ObjectAtt->box_length =  static_cast<uint16_t>( p_data[19] << 8 | p_data[20]) * 0.01f;
                            p_ObjectAtt->box_heigh =  static_cast<uint16_t>( p_data[21] << 8 | p_data[22]) * 0.01f;

                            p_ObjectAtt->classify_type = p_data[23];       //目标分类 0:未知 1：行人 2：自行车 3：小汽车 4：大卡车                             
                            p_ObjectAtt->classify_prob = p_data[24];       //目标分类对应的概率

                            p_ObjectAtt->objmotion_status =  static_cast<uint16_t>( p_data[25] << 8 | p_data[26]) ;  //航迹动静状态 0：静止 1：运动
                            p_ObjectAtt->obstacle_prob =  static_cast<uint16_t>( p_data[27] << 8 | p_data[28]) ;     //障碍物概率

                            objects.push_back(t_ObjectAtt);
                        }

                        saveObjectNum += numObjectInPackage;
                    }

                    //航迹接受到指定的个数
                    if(saveObjectNum == object_num ) {
                        findObjectHeader = 0x00;

                        // ====================== 发布航迹 PointCloud2（中心坐标+尺寸）======================
                        sensor_msgs::msg::PointCloud2 object_pc2;
                        object_pc2.header.stamp = radar_ptp_time;
                        object_pc2.header.frame_id = frame_id_;                  // 与点云坐标系一致
                        object_pc2.width = static_cast<uint32_t>(object_num);         // 航迹数量
                        object_pc2.height = 1;
                        object_pc2.is_dense = false;
                        object_pc2.is_bigendian = false;

                        // 创建 PointField 
                        std::vector<sensor_msgs::msg::PointField> object_fields;

                        // 1. x 字段（中心x坐标）
                        sensor_msgs::msg::PointField field_ox;
                        field_ox.name = "x";
                        field_ox.offset = 0;  // 偏移0字节
                        field_ox.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_ox.count = 1;
                        object_fields.push_back(field_ox);

                        // 2. y 字段（中心y坐标）
                        sensor_msgs::msg::PointField field_oy;
                        field_oy.name = "y";
                        field_oy.offset = 4;  // 偏移4字节
                        field_oy.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_oy.count = 1;
                        object_fields.push_back(field_oy);

                        // 3. z 字段（中心z坐标）
                        sensor_msgs::msg::PointField field_oz;
                        field_oz.name = "z";
                        field_oz.offset = 8;  // 偏移8字节
                        field_oz.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_oz.count = 1;
                        object_fields.push_back(field_oz);

                        // 4. width 字段（航迹宽度）
                        sensor_msgs::msg::PointField field_ow;
                        field_ow.name = "width";
                        field_ow.offset = 12;  // 偏移12字节
                        field_ow.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_ow.count = 1;
                        object_fields.push_back(field_ow);

                        // 5. length 字段（航迹长度）
                        sensor_msgs::msg::PointField field_ol;
                        field_ol.name = "length";
                        field_ol.offset = 16;  // 偏移16字节
                        field_ol.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_ol.count = 1;
                        object_fields.push_back(field_ol);

                        // 6. height 字段（航迹高度）
                        sensor_msgs::msg::PointField field_oh;
                        field_oh.name = "height";
                        field_oh.offset = 20;  // 偏移20字节
                        field_oh.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_oh.count = 1;
                        object_fields.push_back(field_oh);

                        // 7. xvel_abs（纵向速度）
                        sensor_msgs::msg::PointField field_xvel;
                        field_xvel.name = "xvel_abs";
                        field_xvel.offset = 24;  // 偏移24字节
                        field_xvel.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_xvel.count = 1;
                        object_fields.push_back(field_xvel);

                        // 8. yvel_abs（横向速度）
                        sensor_msgs::msg::PointField field_yvel;
                        field_yvel.name = "yvel_abs";
                        field_yvel.offset = 28;
                        field_yvel.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_yvel.count = 1;
                        object_fields.push_back(field_yvel);

                        // 9. xacc_abs（纵向加速度）
                        sensor_msgs::msg::PointField field_xacc;
                        field_xacc.name = "xacc_abs";
                        field_xacc.offset = 32;
                        field_xacc.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_xacc.count = 1;
                        object_fields.push_back(field_xacc);

                        // 10. yacc_abs（横向加速度）
                        sensor_msgs::msg::PointField field_yacc;
                        field_yacc.name = "yacc_abs";
                        field_yacc.offset = 36;
                        field_yacc.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_yacc.count = 1;
                        object_fields.push_back(field_yacc);

                        // 11. heading_angle（航向角）
                        sensor_msgs::msg::PointField field_heading;
                        field_heading.name = "heading_angle";
                        field_heading.offset = 40;
                        field_heading.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_heading.count = 1;
                        object_fields.push_back(field_heading);

                        // 12. classify_type（目标分类）
                        sensor_msgs::msg::PointField field_cls_type;
                        field_cls_type.name = "classify_type";
                        field_cls_type.offset = 44;
                        field_cls_type.datatype = sensor_msgs::msg::PointField::FLOAT32;  // 用FLOAT32存储uint8，兼容RViz显示
                        field_cls_type.count = 1;
                        object_fields.push_back(field_cls_type);

                        // 13. classify_prob（分类概率）
                        sensor_msgs::msg::PointField field_cls_prob;
                        field_cls_prob.name = "classify_prob";
                        field_cls_prob.offset = 48;
                        field_cls_prob.datatype = sensor_msgs::msg::PointField::FLOAT32;
                        field_cls_prob.count = 1;
                        object_fields.push_back(field_cls_prob);

                        // 14. objmotion_status（动静状态）
                        sensor_msgs::msg::PointField field_motion;
                        field_motion.name = "objmotion_status";
                        field_motion.offset = 52;
                        field_motion.datatype = sensor_msgs::msg::PointField::FLOAT32;  // 用FLOAT32存储uint16，兼容显示
                        field_motion.count = 1;
                        object_fields.push_back(field_motion);

                        // 15. obstacle_prob（障碍物概率）
                        sensor_msgs::msg::PointField field_obstacle_prob;
                        field_obstacle_prob.name = "obstacle_prob";
                        field_obstacle_prob.offset = 56;
                        field_obstacle_prob.datatype = sensor_msgs::msg::PointField::FLOAT32;  // 用FLOAT32存储uint16，兼容显示
                        field_obstacle_prob.count = 1;
                        object_fields.push_back(field_obstacle_prob);

                        // 16. track_id（航迹ID）
                        // 放在最后，避免改动既有字段 offset（下游如果只读旧字段仍可工作）
                        sensor_msgs::msg::PointField field_track_id;
                        field_track_id.name = "track_id";
                        field_track_id.offset = 60;
                        field_track_id.datatype = sensor_msgs::msg::PointField::FLOAT32;  // 用FLOAT32存储uint8，兼容显示
                        field_track_id.count = 1;
                        object_fields.push_back(field_track_id);

                        // 赋值字段到 PointCloud2
                        object_pc2.fields = object_fields;
                        object_pc2.point_step = 64;  // 16个FLOAT32 × 4字节 = 64字节
                        object_pc2.row_step = object_pc2.width * object_pc2.point_step;
                        object_pc2.data.resize(object_pc2.row_step * object_pc2.height);

                        // 创建迭代器填充数据
                        sensor_msgs::PointCloud2Iterator<float> iter_ox(object_pc2, "x");
                        sensor_msgs::PointCloud2Iterator<float> iter_oy(object_pc2, "y");
                        sensor_msgs::PointCloud2Iterator<float> iter_oz(object_pc2, "z");
                        sensor_msgs::PointCloud2Iterator<float> iter_ow(object_pc2, "width");
                        sensor_msgs::PointCloud2Iterator<float> iter_ol(object_pc2, "length");
                        sensor_msgs::PointCloud2Iterator<float> iter_oh(object_pc2, "height");

                        sensor_msgs::PointCloud2Iterator<float> iter_xvel(object_pc2, "xvel_abs");
                        sensor_msgs::PointCloud2Iterator<float> iter_yvel(object_pc2, "yvel_abs");
                        sensor_msgs::PointCloud2Iterator<float> iter_xacc(object_pc2, "xacc_abs");
                        sensor_msgs::PointCloud2Iterator<float> iter_yacc(object_pc2, "yacc_abs");
                        sensor_msgs::PointCloud2Iterator<float> iter_heading(object_pc2, "heading_angle");
                        sensor_msgs::PointCloud2Iterator<float> iter_cls_type(object_pc2, "classify_type");
                        sensor_msgs::PointCloud2Iterator<float> iter_cls_prob(object_pc2, "classify_prob");
                        sensor_msgs::PointCloud2Iterator<float> iter_motion(object_pc2, "objmotion_status");
                        sensor_msgs::PointCloud2Iterator<float> iter_obstacle_prob(object_pc2, "obstacle_prob");
                        sensor_msgs::PointCloud2Iterator<float> iter_track_id(object_pc2, "track_id");

                        // ====================== 生成航迹方框 MarkerArray（RViz 绘制用）======================
                        visualization_msgs::msg::MarkerArray marker_array;
                        int marker_id = 0;  // 每个航迹的唯一ID（避免RViz重复渲染）

                        for (const auto& obj : objects) {
                            // 填充 PointCloud2 数据
                            *iter_ox = obj.xpos_vcs;
                            *iter_oy = obj.ypos_vcs;
                            *iter_oz = obj.zpos_vcs;
                            *iter_ow = obj.box_width;
                            *iter_ol = obj.box_length;
                            *iter_oh = obj.box_heigh;

                            *iter_xvel = obj.xvel_abs;                                      // 纵向速度
                            *iter_yvel = obj.yvel_abs;                                      // 横向速度
                            *iter_xacc = obj.xacc_abs;                                      // 纵向加速度
                            *iter_yacc = obj.yacc_abs;                                      // 横向加速度
                            *iter_heading = obj.heading_angle;                              // 航向角
                            *iter_cls_type = static_cast<float>(obj.classify_type);         // uint8转float，兼容显示
                            *iter_cls_prob = obj.classify_prob;                             // 分类概率
                            *iter_motion = static_cast<float>(obj.objmotion_status);        // uint16转float，兼容显示
                            *iter_obstacle_prob = static_cast<float>(obj.obstacle_prob);    // uint16转float，兼容显示
                            *iter_track_id = static_cast<float>(obj.track_id);              // uint8转float，兼容显示

                            // 生成单个航迹的方框 Marker
                            visualization_msgs::msg::Marker marker;
                            marker.header = object_pc2.header;  
                            marker.id = marker_id++;  // 唯一ID
                            marker.type = visualization_msgs::msg::Marker::CUBE;  // 类型：立方体（方框）
                            marker.action = visualization_msgs::msg::Marker::ADD;

                            // 方框中心坐标（与航迹中心一致）
                            marker.pose.position.x = obj.xpos_vcs;  // 纵向距离 → x轴
                            marker.pose.position.y = obj.ypos_vcs;  // 横向距离 → y轴
                            marker.pose.position.z = obj.zpos_vcs;  // 垂直距离 → z轴

                            // 添加航向角旋转
                            float heading_rad = obj.heading_angle * M_PI / 180.0f;  // 度转弧度
                            // 关键：ROS 坐标系中，航向角左正右负，对应绕 Z 轴逆时针旋转
                            // 四元数计算（绕 Z 轴旋转 θ：w=cos(θ/2), z=sin(θ/2)）
                            marker.pose.orientation.w = cos(heading_rad / 2.0f);
                            marker.pose.orientation.z = sin(heading_rad / 2.0f);
                            marker.pose.orientation.x = 0.0f;
                            marker.pose.orientation.y = 0.0f;

                            // 方框尺寸（直接使用航迹的宽/长/高）
                            marker.scale.x = obj.box_length;  // 注意：RViz的scale.x对应航迹length（纵向）
                            marker.scale.y = obj.box_width;   // scale.y对应航迹width（横向）
                            marker.scale.z = obj.box_heigh;   // scale.z对应航迹height（垂直）

                            // 方框颜色（半透明蓝色，rgba：红,绿,蓝,透明度）
                            marker.color.r = 0.0f;
                            marker.color.g = 0.0f;
                            marker.color.b = 1.0f;
                            marker.color.a = 0.5f;  // 透明度0.5，避免遮挡其他数据

                            // 方框生命周期（1秒，避免航迹消失后残留）
                            marker.lifetime = rclcpp::Duration::from_seconds(1.0);

                            // 添加到 MarkerArray
                            marker_array.markers.push_back(marker);

                            // 迭代器自增
                            ++iter_ox; ++iter_oy; ++iter_oz; ++iter_ow; ++iter_ol; ++iter_oh;
                            ++iter_xvel; ++iter_yvel; ++iter_xacc; ++iter_yacc; ++iter_heading;
                            ++iter_cls_type; ++iter_cls_prob; ++iter_motion; ++iter_obstacle_prob; ++iter_track_id;
                        }

                        // 发布航迹 PointCloud2 和 MarkerArray
                        pub_object_pc2_->publish(object_pc2);
                        pub_object_marker_->publish(marker_array);
                    }
                } 
                break;
                
                //接受IP地址装订状态报文
                case 0xAA8B:
                if(messageLen == 8U) {
                    if(data_recvBuf[6] == 0x00) {
                        RCLCPP_INFO(this->get_logger(),"雷达IP操作失败!..........");
                    }
                    else if(data_recvBuf[6] == 0x01) {
                        RCLCPP_INFO(this->get_logger(),"雷达IP装订操作成功!..........");
                    }
                    else if(data_recvBuf[6] == 0x02) {
                        RCLCPP_INFO(this->get_logger(),"雷达IP复位操作成功!..........");
                    }
                    else {
                    }
                } 
                break;

                default:
                break;
            }
        }  
    }
};

// 解析运行模式：both(默认) / a / b
// 支持：
//   ros2 run ... --ros-args -p run_mode:=both|a|b
//   任意参数中含子串 run_mode:=both|a|b
//   --mmw-radar-run-mode=both|a|b  或  --mmw-radar-run-mode both|a|b
static std::string parse_run_mode(int argc, char** argv) {
    std::string mode = "both";
    for (int i = 1; i < argc; ++i) {
        const char* ai = argv[i];
        if (!ai) {
            continue;
        }
        std::string arg(ai);
        const std::string k = "run_mode:=";
        const auto pos = arg.find(k);
        if (pos != std::string::npos) {
            mode = arg.substr(pos + k.size());
            break;
        }
        if (arg == "-p" && i + 1 < argc) {
            std::string pv(argv[i + 1]);
            if (pv.compare(0, k.size(), k) == 0) {
                mode = pv.substr(k.size());
                break;
            }
        }
        const std::string k2 = "--mmw-radar-run-mode=";
        if (arg.compare(0, k2.size(), k2) == 0) {
            mode = arg.substr(k2.size());
            break;
        }
        if (arg == "--mmw-radar-run-mode" && i + 1 < argc) {
            mode = argv[i + 1];
            break;
        }
    }

    // 去空白并转小写
    size_t lo = 0;
    while (lo < mode.size() && std::isspace(static_cast<unsigned char>(mode[lo]))) {
        ++lo;
    }
    size_t hi = mode.size();
    while (hi > lo && std::isspace(static_cast<unsigned char>(mode[hi - 1U]))) {
        --hi;
    }
    mode = mode.substr(lo, hi - lo);
    for (char& c : mode) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }

    if (mode != "both" && mode != "a" && mode != "b") {
        std::cerr << "[mmw_radar_main] 无效 run_mode=\"" << mode << "\"，回退为 both\n";
        mode = "both";
    }
    return mode;
}

//主入口
int main(int argc, char **argv) {
    setlocale(LC_ALL, "en_US.UTF-8");
    rclcpp::init(argc, argv);

    auto bootstrap_node = std::make_shared<rclcpp::Node>("mmw_radar_bootstrap");
    const std::string run_mode_param = bootstrap_node->declare_parameter<std::string>("run_mode", "both");
    const std::string run_mode_cli = parse_run_mode(argc, argv);
    const std::string run_mode = (run_mode_param == "both" && run_mode_cli != "both") ? run_mode_cli : run_mode_param;

    const std::string multicast_ip = bootstrap_node->declare_parameter<std::string>("multicast_ip", "224.0.2.3");
    const int multicast_port = bootstrap_node->declare_parameter<int>("multicast_port", 42104);
    const std::string unicast_ip = bootstrap_node->declare_parameter<std::string>("unicast_ip", "10.13.2.115");
    const int unicast_port = bootstrap_node->declare_parameter<int>("unicast_port", 42404);
    const std::string multicast_interface_ip = bootstrap_node->declare_parameter<std::string>("multicast_interface_ip", "0.0.0.0");

    const int local_port_start = bootstrap_node->declare_parameter<int>("local_port_start", 50000);
    const int local_port_end = bootstrap_node->declare_parameter<int>("local_port_end", 65535);
    const std::string odom_topic = bootstrap_node->declare_parameter<std::string>("odom_topic", "/mavros/local_position/odom");
    const std::string vehicle_speed_topic = bootstrap_node->declare_parameter<std::string>("vehicle_speed_topic", "/VCU_status/vehicle_feedback");
    const bool vehicle_speed_is_signed_longitudinal = bootstrap_node->declare_parameter<bool>("vehicle_speed_is_signed_longitudinal", false);
    const std::string imu_topic = bootstrap_node->declare_parameter<std::string>("imu_topic", "/imu/data");
    const std::string pointcloud_topic = bootstrap_node->declare_parameter<std::string>("pointcloud_topic", "/mmw_radar/pointcloud_topic");
    const std::string object_topic = bootstrap_node->declare_parameter<std::string>("object_topic", "/mmw_radar/objectList_topic");
    const std::string object_marker_topic = bootstrap_node->declare_parameter<std::string>("object_marker_topic", "/mmw_radar/object_marker");
    const std::string frame_id = bootstrap_node->declare_parameter<std::string>("frame_id", "mmw_radar");

    /*************************同一局域网接入两个RA223F ROS2驱动示意demo,只有一个RA223F同样实用*********************************************/
    const bool enable_a = (run_mode == "both" || run_mode == "a");
    const bool enable_b = (run_mode == "both" || run_mode == "b");

    auto logger = rclcpp::get_logger("mmw_radar_main");
    RCLCPP_INFO(logger, "run_mode=%s (启用节点 a=%s, b=%s)",
                run_mode.c_str(),
                enable_a ? "是" : "否",
                enable_b ? "是" : "否");

    rclcpp::executors::MultiThreadedExecutor executor;
    std::shared_ptr<mmw_radar> mmw_radar_node_a;
    std::shared_ptr<mmw_radar> mmw_radar_node_b;

    /******************************************************************************************************
     * 节点A相关代码段（单节点模式：保留本段，整段注释“节点B相关代码段”即可）
     ******************************************************************************************************/
    if (enable_a) {
        // 雷达 a：组播收点云/目标，单播注入 odom
        const UdpEndpoint multicast_a{ multicast_ip, static_cast<uint16_t>(multicast_port) };
        const UdpEndpoint unicast_a{ unicast_ip, static_cast<uint16_t>(unicast_port) };

        //如需更改节点a所发布的话题名请在对应位置处输入对应的话题名字
        mmw_radar_node_a = std::make_shared<mmw_radar>(
            "mmw_radar_node",
            multicast_a,
            unicast_a,
            local_port_start,
            local_port_end,
            odom_topic,
            vehicle_speed_topic,
            imu_topic,
            pointcloud_topic,
            object_topic,
            object_marker_topic,
            frame_id,
            multicast_interface_ip,
            vehicle_speed_is_signed_longitudinal
        );
        executor.add_node(mmw_radar_node_a);
    }

    /******************************************************************************************************
     * 节点B相关代码段（双节点模式：保留本段 + 上方“节点A相关代码段”）
     ******************************************************************************************************/
    if (enable_b) {
        // 雷达 b：组播收点云/目标，单播注入 odom（单播地址统一使用 10.13.2.x 网段）
        // const UdpEndpoint multicast_b{ "224.0.2.3", 42106 };
        // const UdpEndpoint unicast_b{ "10.13.2.116", 42404 };

        // mmw_radar_node_b = std::make_shared<mmw_radar>(
        //     "mmw_radar_node_b",
        //     multicast_b,
        //     unicast_b,
        //     50000,
        //     65535,
        //     "/mavros/local_position/odom",
        //     "/mmw_radar_node_b/pointcloud_topic",
        //     "/mmw_radar_node_b/objectList_topic",
        //     "/mmw_radar_node_b/object_marker",
        //     default_networkCard_Ip
        // );
        // executor.add_node(mmw_radar_node_b);
    }

    executor.spin();

    rclcpp::shutdown();
    return 0;
}


