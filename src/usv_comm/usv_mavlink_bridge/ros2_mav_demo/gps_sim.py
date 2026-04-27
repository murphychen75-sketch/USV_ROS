import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import Float64MultiArray
import math
import time
from ros2_mav_demo.topic_contract import LEGACY_TOPICS, PRIMARY_TOPICS


class GpsSimNode(Node):
    def __init__(self):
        super().__init__('fake_gps_publisher')
        self.declare_parameter('publish_legacy_gps_topics', False)
        publish_legacy = self.get_parameter(
            'publish_legacy_gps_topics').get_parameter_value().bool_value
        self.publish_legacy = publish_legacy

        self.pub_fix = self.create_publisher(NavSatFix, PRIMARY_TOPICS['gps_fix_in'], 10)
        self.pub_vel = self.create_publisher(TwistStamped, PRIMARY_TOPICS['velocity_in'], 10)
        self.pub_gps = None
        self.pub_gpsr = None
        if publish_legacy:
            self.pub_gps = self.create_publisher(Float64MultiArray, LEGACY_TOPICS['gps_in'], 10)
            self.pub_gpsr = self.create_publisher(Float64MultiArray, LEGACY_TOPICS['gpsr_in'], 10)

        self.timer = self.create_timer(0.1, self.timer_callback)

        # 初始状态
        self.lat, self.lon, self.alt = 31.2304, 121.4737, 5.0
        self.speed = 2.0  # m/s
        self.yaw = 0.0    # 0=北, 90=东
        self.last_time = time.time()

        self.get_logger().info(
            f"Fake GPS Publisher Started -> fix={PRIMARY_TOPICS['gps_fix_in']}, "
            f"velocity={PRIMARY_TOPICS['velocity_in']}, legacy={publish_legacy}"
        )

    def timer_callback(self):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        # 1. 模拟转弯（每秒转10度）
        self.yaw = (self.yaw + 10.0 * dt) % 360.0
        yaw_rad = math.radians(self.yaw)

        # 2. 计算速度分量 (NED坐标系: 北, 东, 地)
        vel_n = self.speed * math.cos(yaw_rad)
        vel_e = self.speed * math.sin(yaw_rad)
        vel_d = 0.0

        # 3. 更新经纬度
        self.lat += (vel_n * dt) / 111111.0
        self.lon += (vel_e * dt) / (111111.0 * math.cos(math.radians(self.lat)))

        fix_msg = NavSatFix()
        fix_msg.header.stamp = self.get_clock().now().to_msg()
        fix_msg.header.frame_id = "gps_link"
        fix_msg.latitude = float(self.lat)
        fix_msg.longitude = float(self.lon)
        fix_msg.altitude = float(self.alt)
        self.pub_fix.publish(fix_msg)

        vel_msg = TwistStamped()
        vel_msg.header.stamp = fix_msg.header.stamp
        vel_msg.header.frame_id = "map"
        vel_msg.twist.linear.x = float(vel_n)
        vel_msg.twist.linear.y = float(vel_e)
        vel_msg.twist.linear.z = float(vel_d)
        self.pub_vel.publish(vel_msg)

        if self.publish_legacy:
            gps_msg = Float64MultiArray()
            gps_msg.data = [
                float(self.lat),
                float(self.lon),
                float(self.alt),
                float(self.speed),
                float(self.yaw),
                float(vel_n),
                float(vel_e),
                float(vel_d),
                float(now),
                float(15),
                float(0.8),
                float(3),
            ]
            self.pub_gps.publish(gps_msg)

            gpsr_msg = Float64MultiArray()
            gpsr_msg.data = [1.0, float(self.yaw), 0.1, 4.0]
            self.pub_gpsr.publish(gpsr_msg)

def main(args=None):
    rclpy.init(args=args)
    node = GpsSimNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()