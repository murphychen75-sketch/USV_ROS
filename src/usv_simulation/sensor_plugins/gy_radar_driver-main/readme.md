# 适用于x86_64架构的电脑
 消息包接口定义在usv_interfaces里

## 节点说明：
###        radar_control_node 
    打开雷达，让雷达开始扫描

###        radar_data_node 
    通过sdk读取雷达回波，转换成marine_sensor_msg/msg/radarsector消息
            
        输出topic: 

###         arpa_receiver_node
    通过sdk读取雷达追踪的arpa目标，并封装成自定义ros消息

        输出topic:

###         radar_converter_node 
    接收marine_sensor_msg/msg/radarsector消息转换成sensor_msgs/msg/point_cloud2消息

        输入topic: 
        输出topic: 
    
###        adaptive_radar_grid_map_node 
    接收marine_sensor_msg/msg/radarsector消息然后发布栅格地图

        输入topic: 
        输出topic: 
###         radar_tf_node
    接收arpa消息并转换tf

##          其他节点均为测试代码或者版本迭代代码，不必理会


