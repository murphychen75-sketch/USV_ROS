#ifndef UDP_INTERFACE_H
#define UDP_INTERFACE_H

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/select.h>
#include <string>
#include <cstring>
#include <iostream>
#include <cerrno>

/*
 * UDP 抽象封装（Linux Socket）
 *
 * 设计目标：
 * - **组播接收**：为雷达数据接收提供稳定的 UDP 组播 server socket（可设置 SO_REUSEADDR、加入组播组）
 * - **单播发送**：为“雷达配置/状态注入”等场景提供 UDP 单播 client socket（可绑定本地端口）
 *
 * 约定说明：
 * - `socket_server_fd`：用于组播接收（recvfrom）
 * - `socket_client_fd`：用于单播发送（sendto）
 * - 本类允许同时打开 server/client 两类 socket；析构时统一释放。
 *
 * 返回值语义（通用）：
 * - 0：成功
 * - -1：失败（具体原因可从 errno/日志中查看）
 */
class UdpInterface {
private:
    int socket_server_fd = -1;
    int socket_client_fd = -1;
    struct sockaddr_in group_addr;
    struct sockaddr_in addr_serv;
    socklen_t addr_len = sizeof(group_addr);
    bool is_multicast_ = false;
    bool is_unicast_ = false;
    in_addr multicast_interface_addr_{};

public:
    UdpInterface() = default;
    ~UdpInterface();

    /**
     * @brief 初始化 UDP 组播接收端（server socket）
     * @param ip   组播地址（如 224.0.2.3）
     * @param port 监听端口（如 42104）
     *
     * 行为：
     * - 创建 UDP socket
     * - 设置 SO_REUSEADDR（便于重启/多进程场景）
     * - bind 到 INADDR_ANY:port
     * - 加入组播组（IP_ADD_MEMBERSHIP）
     */
    int initUdpMulticastServer(const std::string& ip, int port);

    /**
     * @brief 初始化 UDP 组播接收端（可指定加入组播的网卡 IP）
     * @param ip 组播地址
     * @param port 监听端口
     * @param interface_ip 本机网卡 IP（例如 10.13.2.123）；传空或 "0.0.0.0" 表示由系统选择默认网卡
     */
    int initUdpMulticastServer(const std::string& ip, int port, const std::string& interface_ip);

    /**
     * @brief 初始化 UDP 单播发送端（client socket）
     * @param dest_ip   目的 IP（雷达注入/配置接口 IP）
     * @param dest_port 目的端口
     * @param local_port 本机绑定端口（>0 时执行 bind；0 表示不显式 bind）
     *
     * 说明：
     * - 某些环境下需要固定/扫描本机端口，便于满足网络/设备侧策略。
     */
    int initUdpUnicastClient(const std::string& dest_ip, int dest_port, int local_port);

    /**
     * @brief 将指定 socket 设置为非阻塞
     * @param socket_type 0=server socket，1=client socket
     */
    void setNonBlocking(int socket_type);

    /**
     * @brief 带超时的接收（select + recvfrom）
     * @param src_addr   输出：来源地址
     * @param buffer     输出：接收缓冲区
     * @param recv_len   输出：接收长度（<=0 表示无数据或错误）
     * @param timeout_ms 超时时间（毫秒）
     *
     * 注意：
     * - 超时返回 0 且 recv_len=0（表示“本次没有数据”，不是错误）
     * - 仅当 select/recvfrom 发生不可恢复错误时返回 -1
     */
    int receiveWithTimeout(struct sockaddr_in* src_addr, char* buffer, int& recv_len, int timeout_ms = 100);

    /**
     * @brief 带超时的发送（select 可写 + sendto）
     * @param data       待发送数据
     * @param len        数据长度
     * @param timeout_ms 发送超时（毫秒）
     * @return sendto 返回值（发送字节数），或 -1（超时/错误）
     */
    int sendToRadar(const char* data, int len, int timeout_ms);

    /**
     * @brief 关闭并清理所有 socket
     *
     * - 若是组播接收端，会先执行 IP_DROP_MEMBERSHIP 退出组播组
     * - 关闭 server/client socket
     */
    void closeAllSockets();

    /**
     * @brief 发送心跳包（默认字符串 "HEARTBEAT"）
     *
     * 适用场景：调试网络连通性/链路可用性（雷达端是否处理由对端决定）
     */
    int sendHeartbeat(const std::string& heartbeat_data);

    // 状态检查
    bool isServerSocketOpen() const;
    bool isClientSocketOpen() const;
    bool isMulticast() const;
    bool isUnicast() const;

    // 获取信息
    std::string getServerAddress() const;
    uint16_t getServerPort() const;
    std::string getClientAddress() const;
    uint16_t getClientPort() const;
};

#endif // UDP_INTERFACE_H
