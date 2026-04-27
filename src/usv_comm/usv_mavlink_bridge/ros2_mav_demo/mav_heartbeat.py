import os
# 强制使用 MAVLink 2 协议
os.environ['MAVLINK20'] = '1'

import rclpy
from rclpy.node import Node
from pymavlink import mavutil
import threading
from ros2_mav_demo.topic_contract import (
    MAVLINK_ENDPOINT,
    MAVLINK_SOURCE_COMPONENT,
    MAVLINK_SOURCE_SYSTEM,
)
"""
节点作用：模拟飞控发送heart_beat心跳包，让QGC以为有飞控连接
"""
class MavHeartbeatNode(Node):
    def __init__(self):
        super().__init__('mav_heartbeat_node')
        
        # QGC 默认监听 UDP 14550
        # source_system=1: 无人船ID为1，若有多个无人船，则ID顺延，最大支持255个同时连接
        # source_component=1: 组件ID为1 (飞控)
        self.connection = mavutil.mavlink_connection(
            MAVLINK_ENDPOINT,
            source_system=MAVLINK_SOURCE_SYSTEM,
            source_component=MAVLINK_SOURCE_COMPONENT
        )
        self.listener_thread = threading.Thread(target=self.mavlink_listener, daemon=True)
        self.listener_thread.start()

        # 创建定时器，1Hz (1.0秒)
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.get_logger().info("MAVLink 2 Heartbeat Sender Started -> UDP 14550")

    def timer_callback(self):
        # 发送心跳包
        # MAV_TYPE_SURFACE_BOAT: 船
        # MAV_AUTOPILOT_GENERIC: 通用飞控
        # MAV_MODE_MANUAL_ARMED：模拟已解锁状态
        self.connection.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_SURFACE_BOAT,
            mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
            mavutil.mavlink.MAV_MODE_MANUAL_ARMED,
            0, 
            mavutil.mavlink.MAV_STATE_ACTIVE)
        self.get_logger().info("Sent Heartbeat")

    def mavlink_listener(self):
        """
        监听来自QGC的下行指令，特别是握手请求。
        """
        while rclpy.ok():
            try:
                # 阻塞式读取，超时1秒
                msg = self.connection.recv_match(blocking=True, timeout=1.0)
                if not msg:
                    continue

                # 处理参数列表请求：这是QGC连接成功的关键握手步骤
                if msg.get_type() == 'PARAM_REQUEST_LIST':
                    self.get_logger().info(f'收到参数请求 PARAM_REQUEST_LIST 来自 SysID:{msg.get_srcSystem()}')
                    self.send_mock_parameters()
                    
            except Exception as e:
                self.get_logger().error(f'MAVLink监听异常: {e}')

    def send_mock_parameters(self):
        """
        发送虚拟参数以欺骗QGC完成连接流程。(若不发送参数，QGC会一直在尝试连接。)
        """
        # 定义一个虚拟参数 "BRIDGE_VER"
        param_id = b'BRIDGE_VER'
        param_value = 1.0
        param_type = mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        param_count = 1
        param_index = 0

        self.connection.mav.param_value_send(
            param_id,
            param_value,
            param_type,
            param_count,
            param_index
        )
        self.get_logger().info('已发送虚拟参数响应，完成握手。')


def main(args=None):
    rclpy.init(args=args)
    node = MavHeartbeatNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()