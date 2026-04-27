import math
import random
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from rclpy.qos import QoSProfile, ReliabilityPolicy
from ros2_mav_demo.topic_contract import LEGACY_TOPICS, PRIMARY_TOPICS

class ImuSimNode(Node):
    def __init__(self):
        super().__init__("imu_sim_node")
        self.declare_parameter('publish_legacy_imu_topic', False)
        publish_legacy = self.get_parameter(
            'publish_legacy_imu_topic').get_parameter_value().bool_value

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.pub = self.create_publisher(Imu, PRIMARY_TOPICS["imu_in"], qos)
        self.legacy_pub = None
        if publish_legacy and LEGACY_TOPICS["imu_in"] != PRIMARY_TOPICS["imu_in"]:
            self.legacy_pub = self.create_publisher(Imu, LEGACY_TOPICS["imu_in"], qos)

        # 发送 IMU，默认 10Hz
        self.timer = self.create_timer(0.1, self.timer_callback)

        # 模拟状态
        self.t = 0.0

        self.get_logger().info(
            f"IMU Simulator Started -> primary={PRIMARY_TOPICS['imu_in']}, "
            f"legacy={LEGACY_TOPICS['imu_in'] if publish_legacy else 'disabled'}"
        )

    def timer_callback(self):
        msg = Imu()

        # ---------------------------
        # 时间模拟
        # ---------------------------
        self.t += 0.01

        # ---------------------------
        # 模拟线加速度（ENU）
        #
        #   x: 轻微震动 + 简谐运动
        #   y: 偏移 + 随机扰动
        #   z: 加上重力 9.8（一般 IMU 包含重力）
        # ---------------------------
        ax = 0.5 * math.sin(1.2 * self.t) + random.uniform(-0.05, 0.05)
        ay = 0.3 * math.sin(0.9 * self.t + 1.0) + random.uniform(-0.05, 0.05)
        az = 9.8 + 0.1 * math.sin(0.5 * self.t) + random.uniform(-0.02, 0.02)

        # ---------------------------
        # 模拟角速度（ENU）
        #
        # 假设有轻微 yaw 旋转、上下抖动
        # ---------------------------
        gx = 0.02 * math.sin(0.8 * self.t) + random.uniform(-0.005, 0.005)
        gy = 0.015 * math.cos(0.5 * self.t) + random.uniform(-0.005, 0.005)
        gz = 0.1 * math.sin(0.3 * self.t) + random.uniform(-0.002, 0.002)

        # 填写 IMU 消息
        msg.linear_acceleration.x = ax
        msg.linear_acceleration.y = ay
        msg.linear_acceleration.z = az

        msg.angular_velocity.x = gx
        msg.angular_velocity.y = gy
        msg.angular_velocity.z = gz

        # 发布
        self.pub.publish(msg)
        if self.legacy_pub is not None:
            self.legacy_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ImuSimNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
