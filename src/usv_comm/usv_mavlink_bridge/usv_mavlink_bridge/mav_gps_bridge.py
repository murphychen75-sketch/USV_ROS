import os
os.environ['MAVLINK20'] = '1'

import math
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import TwistStamped
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import Float64MultiArray
from pymavlink import mavutil

from usv_mavlink_bridge.topic_contract import (
    LEGACY_TOPICS,
    MAVLINK_ENDPOINT,
    MAVLINK_SOURCE_COMPONENT,
    MAVLINK_SOURCE_SYSTEM,
    PRIMARY_TOPICS,
)


class MavGpsBridge(Node):
    def __init__(self):
        super().__init__('mav_gps_bridge')
        self.declare_parameter('use_legacy_gps_topics', False)
        use_legacy = self.get_parameter(
            'use_legacy_gps_topics').get_parameter_value().bool_value

        self.conn = mavutil.mavlink_connection(
            MAVLINK_ENDPOINT,
            source_system=MAVLINK_SOURCE_SYSTEM,
            source_component=MAVLINK_SOURCE_COMPONENT
        )
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)

        self.sub_gps_fix = self.create_subscription(
            NavSatFix,
            PRIMARY_TOPICS['gps_fix_in'],
            self.navsat_callback,
            qos
        )
        self.sub_vel = self.create_subscription(
            TwistStamped,
            PRIMARY_TOPICS['velocity_in'],
            self.velocity_callback,
            qos
        )

        self.sub_legacy_gps = None
        self.sub_legacy_gpsr = None
        if use_legacy:
            self.sub_legacy_gps = self.create_subscription(
                Float64MultiArray,
                LEGACY_TOPICS['gps_in'],
                self.legacy_gps_callback,
                qos
            )
            self.sub_legacy_gpsr = self.create_subscription(
                Float64MultiArray,
                LEGACY_TOPICS['gpsr_in'],
                self.legacy_gpsr_callback,
                qos
            )

        self.latest_fix = None
        self.latest_velocity = None
        self.latest_legacy_yaw = None
        self.latest_satellites = 12
        self.latest_hdop = 1.0
        self.boot_time = time.time()

        self.get_logger().info(
            f"MAVLink GPS Bridge Started. gps={PRIMARY_TOPICS['gps_fix_in']}, "
            f"velocity={PRIMARY_TOPICS['velocity_in']}, legacy={use_legacy}"
        )

    def navsat_callback(self, msg: NavSatFix):
        self.latest_fix = msg
        self.publish_mavlink_from_standard()

    def velocity_callback(self, msg: TwistStamped):
        self.latest_velocity = msg
        self.publish_mavlink_from_standard()

    def legacy_gpsr_callback(self, msg: Float64MultiArray):
        if len(msg.data) > 1:
            self.latest_legacy_yaw = float(msg.data[1])

    def legacy_gps_callback(self, msg: Float64MultiArray):
        data = msg.data
        if len(data) < 11:
            return
        try:
            lat = data[0]
            lon = data[1]
            alt = data[2]
            speed = data[3]
            yaw = data[4]
            vel_n = data[5]
            vel_e = data[6]
            vel_d = data[7]
            stars = int(data[9])
            hdop = data[10]
            current_yaw = self.latest_legacy_yaw if self.latest_legacy_yaw is not None else yaw
            self.send_mavlink(lat, lon, alt, speed, vel_n, vel_e, vel_d, current_yaw, stars, hdop)
        except Exception as e:
            self.get_logger().error(f'Legacy GPS 数据处理失败: {e}')

    def publish_mavlink_from_standard(self):
        if self.latest_fix is None or self.latest_velocity is None:
            return

        vel = self.latest_velocity.twist.linear
        vel_n = float(vel.x)
        vel_e = float(vel.y)
        vel_d = float(vel.z)
        speed = math.sqrt(vel_n ** 2 + vel_e ** 2 + vel_d ** 2)
        yaw_deg = math.degrees(math.atan2(vel_e, vel_n)) if speed > 1e-6 else 0.0

        self.send_mavlink(
            lat=self.latest_fix.latitude,
            lon=self.latest_fix.longitude,
            alt=self.latest_fix.altitude,
            speed=speed,
            vel_n=vel_n,
            vel_e=vel_e,
            vel_d=vel_d,
            yaw_deg=yaw_deg,
            stars=self.latest_satellites,
            hdop=self.latest_hdop,
        )

    def send_mavlink(self, lat, lon, alt, speed, vel_n, vel_e, vel_d, yaw_deg, stars, hdop):
        mav_hdg = int((yaw_deg % 360.0) * 100)
        lat_i = int(lat * 1e7)
        lon_i = int(lon * 1e7)
        alt_i = int(alt * 1000)
        vel_cm = int(speed * 100)
        vn_cm = int(vel_n * 100)
        ve_cm = int(vel_e * 100)
        vd_cm = int(vel_d * 100)
        hdop_i = int(max(0.0, hdop) * 100)
        t_ms = int((time.time() - self.boot_time) * 1000)
        t_us = t_ms * 1000

        self.conn.mav.gps_raw_int_send(
            t_us, 3, lat_i, lon_i, alt_i,
            hdop_i, 65535, vel_cm, mav_hdg, int(stars)
        )
        self.conn.mav.global_position_int_send(
            t_ms, lat_i, lon_i, alt_i, alt_i,
            vn_cm, ve_cm, vd_cm, mav_hdg
        )

def main(args=None):
    rclpy.init(args=args)
    node = MavGpsBridge()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
