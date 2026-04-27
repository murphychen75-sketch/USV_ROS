import os
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Int16MultiArray
from pymavlink import mavutil
import threading
import time
from ros2_mav_demo.topic_contract import (
    LEGACY_TOPICS,
    MAVLINK_ENDPOINT,
    MAVLINK_SOURCE_COMPONENT,
    MAVLINK_SOURCE_SYSTEM,
    PRIMARY_TOPICS,
)

# 强制使用 MAVLink 2
os.environ['MAVLINK20'] = '1'
"""
节点作用：
        1.模拟飞控发送heart_beat心跳包，让QGC以为有飞控连接
        2.接收MavLink的MANUAL_CONTROL消息，并转换成ros消息
"""
class VirtualPilotNode(Node):
    def __init__(self):
        super().__init__('mav_rc_bridge_node')
        self.declare_parameter('publish_legacy_manual_topic', False)
        publish_legacy = self.get_parameter(
            'publish_legacy_manual_topic').get_parameter_value().bool_value
        self.control_pub = self.create_publisher(Twist, PRIMARY_TOPICS['manual_out'], 10)
        self.legacy_pub = None
        if publish_legacy:
            self.legacy_pub = self.create_publisher(
                Int16MultiArray,
                LEGACY_TOPICS['manual_out'],
                10
            )
        
        self.connection = mavutil.mavlink_connection(
            MAVLINK_ENDPOINT,
            source_system=MAVLINK_SOURCE_SYSTEM,
            source_component=MAVLINK_SOURCE_COMPONENT
        )
        self.get_logger().info(">>> 虚拟飞控已启动，正在连接 QGC...")

        # --- 虚拟参数 (用于通过 QGC 的握手检查) ---
        self.mock_params = [
            (b"SYSID_THISMAV", 1.0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32),
            (b"PILOT_THR_BHV", 0.0, mavutil.mavlink.MAV_PARAM_TYPE_INT32),
            (b"ARMING_CHECK",  0.0, mavutil.mavlink.MAV_PARAM_TYPE_INT32),
        ]

        # 启动接收线程
        self.listen_thread = threading.Thread(target=self.mavlink_loop, daemon=True)
        self.listen_thread.start()

        # 启动心跳定时器 (1Hz)
        self.timer = self.create_timer(1.0, self.send_heartbeat)

    def send_heartbeat(self):
        # 伪装成 ArduPilot 飞控
        self.connection.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_SURFACE_BOAT,
            mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
            mavutil.mavlink.MAV_MODE_MANUAL_ARMED, 
            0,
            mavutil.mavlink.MAV_STATE_ACTIVE
        )

    def send_mock_param(self):
        #发送虚拟参数列表，不然QGC会一直卡在连接界面
        param_count = len(self.mock_params)
        for i, (name, value, p_type) in enumerate(self.mock_params):
            self.connection.mav.param_value_send(
                name, value, p_type, param_count, i
            )
            time.sleep(0.01) # 防止丢包

    def mavlink_loop(self):
        while rclpy.ok():
            try:
                msg = self.connection.recv_match(blocking=True, timeout=1.0)
                if not msg:
                    continue

                msg_type = msg.get_type()

                # 处理摇杆控制
                if msg_type == 'MANUAL_CONTROL':
                    self.process_manual_control(msg)

                # 处理参数握手
                elif msg_type == 'PARAM_REQUEST_LIST':
                    self.get_logger().info('收到参数列表请求，正在同步...')
                    self.send_mock_param()
                
                elif msg_type == 'PARAM_REQUEST_READ':
                    req_idx = msg.param_index
                    if 0 <= req_idx < len(self.mock_params):
                        name, value, p_type = self.mock_params[req_idx]
                        self.connection.mav.param_value_send(name, value, p_type, len(self.mock_params), req_idx)

            except Exception as e:
                self.get_logger().error(f"MAVLink Error: {e}")

    def process_manual_control(self, msg):
        """
        处理摇杆数据
        """
        val_x = int(msg.x)
        val_y = int(msg.y)
        val_r = int(msg.r)
        val_z = int(msg.z) 

        cmd_msg = Twist()
        cmd_msg.linear.x = max(-1.0, min(1.0, val_x / 1000.0))
        cmd_msg.linear.y = max(-1.0, min(1.0, val_y / 1000.0))
        cmd_msg.linear.z = max(-1.0, min(1.0, (val_z - 500.0) / 500.0))
        cmd_msg.angular.z = max(-1.0, min(1.0, val_r / 1000.0))
        self.control_pub.publish(cmd_msg)

        if self.legacy_pub is not None:
            array_msg = Int16MultiArray()
            array_msg.data = [val_x, val_y, val_z, val_r]
            self.legacy_pub.publish(array_msg)

        print(
            f"\r[Control] x={val_x:5d} | y={val_y:5d} | z={val_z:5d} | r={val_r:5d}", 
            end="", flush=True
        )

def main(args=None):
    rclpy.init(args=args)
    node = VirtualPilotNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()