import os
os.environ['MAVLINK20'] = '1'  # 开启 MAVLink 2

import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Imu
from pymavlink import mavutil
from usv_mavlink_bridge.topic_contract import (
    LEGACY_TOPICS,
    MAVLINK_ENDPOINT,
    MAVLINK_SOURCE_COMPONENT,
    MAVLINK_SOURCE_SYSTEM,
    PRIMARY_TOPICS,
)


class MavImuBridge(Node):
    def __init__(self):
        super().__init__('mav_imu_bridge')
        self.declare_parameter('use_legacy_imu_topic', False)
        use_legacy = self.get_parameter(
            'use_legacy_imu_topic').get_parameter_value().bool_value
        self.connection = mavutil.mavlink_connection(
            MAVLINK_ENDPOINT,
            source_system=MAVLINK_SOURCE_SYSTEM,
            source_component=MAVLINK_SOURCE_COMPONENT,
        )

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.primary_sub = self.create_subscription(
            Imu,
            PRIMARY_TOPICS['imu_in'],
            self.imu_callback,
            qos,
        )

        self.legacy_sub = None
        if use_legacy and LEGACY_TOPICS['imu_in'] != PRIMARY_TOPICS['imu_in']:
            self.legacy_sub = self.create_subscription(
                Imu,
                LEGACY_TOPICS['imu_in'],
                self.imu_callback,
                qos,
            )

        self.get_logger().info(
            f"IMU primary topic: {PRIMARY_TOPICS['imu_in']}, "
            f"legacy: {LEGACY_TOPICS['imu_in'] if use_legacy else 'disabled'}"
        )

    @staticmethod
    def enu_to_ned_acc(ax, ay, az):
        ax_ned = ay
        ay_ned = ax
        az_ned = -az
        return ax_ned, ay_ned, az_ned

    @staticmethod
    def enu_to_ned_gyro(gx, gy, gz):
        gx_ned = gy
        gy_ned = gx
        gz_ned = -gz
        return gx_ned, gy_ned, gz_ned

    def imu_callback(self, msg: Imu):
        time_usec = int(time.time() * 1e6)

        ax_enu = msg.linear_acceleration.x
        ay_enu = msg.linear_acceleration.y
        az_enu = msg.linear_acceleration.z

        gx_enu = msg.angular_velocity.x
        gy_enu = msg.angular_velocity.y
        gz_enu = msg.angular_velocity.z

        # 坐标系转换 ENU → NED
        ax, ay, az = self.enu_to_ned_acc(ax_enu, ay_enu, az_enu)
        gx, gy, gz = self.enu_to_ned_gyro(gx_enu, gy_enu, gz_enu)

        try:
            self.connection.mav.highres_imu_send(
                time_usec,
                ax, ay, az,
                gx, gy, gz,
                0, 0, 0,
                0, 0, 0, 0,
                0
            )

        except Exception as e:
            self.get_logger().warn(f"发送 IMU 失败: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = MavImuBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
