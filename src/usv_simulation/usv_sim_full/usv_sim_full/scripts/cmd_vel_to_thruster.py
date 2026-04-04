#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64

class CmdVelToThruster(Node):
    def __init__(self):
        super().__init__('cmd_vel_to_thruster')

        # Read namespace at startup so one script can be reused by multiple vessels.
        self.declare_parameter('namespace', 'usv_1')
        ns = self.get_parameter('namespace').get_parameter_value().string_value.strip('/')
        self.namespace = ns if ns else 'usv_1'

        cmd_vel_topic = f'/{self.namespace}/cmd_vel'
        cmd_vel_fallback_topic = '/cmd_vel'
        left_thrust_topic = f'/{self.namespace}/thrusters/left/thrust'
        right_thrust_topic = f'/{self.namespace}/thrusters/right/thrust'
        left_pos_topic = f'/{self.namespace}/thrusters/left/pos'
        right_pos_topic = f'/{self.namespace}/thrusters/right/pos'

        self.subscription = self.create_subscription(
            Twist,
            cmd_vel_topic,
            self.listener_callback,
            10)

        # Compatibility path: some Nav2 launch variants publish /cmd_vel directly.
        self.subscription_fallback = self.create_subscription(
            Twist,
            cmd_vel_fallback_topic,
            self.listener_callback,
            10)

        self.left_pub = self.create_publisher(Float64, left_thrust_topic, 10)
        self.right_pub = self.create_publisher(Float64, right_thrust_topic, 10)

        self.left_pos_pub = self.create_publisher(Float64, left_pos_topic, 10)
        self.right_pos_pub = self.create_publisher(Float64, right_pos_topic, 10)

        # Basic differential drive kinematics approximation
        self.linear_scale = 1000.0 # thrust per m/s
        self.angular_scale = 500.0 # thrust diff per rad/s

        self.get_logger().info(
            f"Started cmd_vel -> thruster converter for namespace '{self.namespace}' "
            f"(listening on {cmd_vel_topic} and {cmd_vel_fallback_topic})"
        )

    def listener_callback(self, msg):
        v = msg.linear.x
        w = msg.angular.z

        left_thrust = (v * self.linear_scale) - (w * self.angular_scale)
        right_thrust = (v * self.linear_scale) + (w * self.angular_scale)

        # Publish thrusts
        lt_msg = Float64()
        lt_msg.data = max(min(left_thrust, 1000.0), -1000.0)
        self.left_pub.publish(lt_msg)

        rt_msg = Float64()
        rt_msg.data = max(min(right_thrust, 1000.0), -1000.0)
        self.right_pub.publish(rt_msg)

        # Publish 0 pos for fixed azimuth
        pos_msg = Float64()
        pos_msg.data = 0.0
        self.left_pos_pub.publish(pos_msg)
        self.right_pos_pub.publish(pos_msg)

def main(args=None):
    rclpy.init(args=args)
    node = CmdVelToThruster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        # shutdown may already be triggered by launch on Ctrl+C
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
