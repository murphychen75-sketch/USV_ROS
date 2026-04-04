#!/usr/bin/env python3
"""Publish RViz markers matching minimal_4d_radar_validation.sdf obstacle geometry (frame: world)."""

import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray


def quat_yaw(yaw: float):
    """Roll/pitch=0, yaw about Z. Returns geometry_msgs Quaternion."""
    from geometry_msgs.msg import Quaternion

    q = Quaternion()
    q.x = 0.0
    q.y = 0.0
    q.z = math.sin(yaw * 0.5)
    q.w = math.cos(yaw * 0.5)
    return q


def cube_marker(stamp, ns: str, m_id: int, x, y, z, yaw, sx, sy, sz, rgba):
    m = Marker()
    m.header.stamp = stamp
    m.header.frame_id = "world"
    m.ns = ns
    m.id = m_id
    m.type = Marker.CUBE
    m.action = Marker.ADD
    m.pose.position.x = float(x)
    m.pose.position.y = float(y)
    m.pose.position.z = float(z)
    m.pose.orientation = quat_yaw(yaw)
    m.scale.x = float(sx)
    m.scale.y = float(sy)
    m.scale.z = float(sz)
    c = ColorRGBA()
    c.r, c.g, c.b, c.a = rgba
    m.color = c
    m.lifetime.sec = 0
    m.lifetime.nanosec = 0
    return m


class ValidationWorldMarkers(Node):
    def __init__(self):
        super().__init__("validation_world_markers")
        self.pub = self.create_publisher(MarkerArray, "/radar/validation_models", 10)
        self.timer = self.create_timer(0.5, self.cb)

    def cb(self):
        arr = MarkerArray()
        stamp = self.get_clock().now().to_msg()

        # ego_usv hull_collision: model (0,0,1), box center in link (-0.7,0,-0.4), size 2x1x0.4
        arr.markers.append(
            cube_marker(
                stamp,
                "validation",
                0,
                -0.7,
                0.0,
                0.6,
                0.0,
                2.0,
                1.0,
                0.4,
                (0.2, 0.9, 0.3, 0.35),
            )
        )

        # target_ship_metal
        arr.markers.append(
            cube_marker(
                stamp, "validation", 1, 35.0, 0.0, 1.0, 0.0, 6.0, 3.0, 2.0, (1.0, 0.4, 0.1, 0.45)
            )
        )
        # target_ship_metal_port
        arr.markers.append(
            cube_marker(
                stamp, "validation", 2, 42.0, 14.0, 1.0, 0.25, 5.0, 2.5, 2.0, (0.2, 0.6, 1.0, 0.45)
            )
        )
        # target_ship_metal_starboard
        arr.markers.append(
            cube_marker(
                stamp, "validation", 3, 48.0, -18.0, 1.2, -0.2, 4.0, 2.0, 1.8, (0.9, 0.2, 0.9, 0.45)
            )
        )

        self.pub.publish(arr)


def main():
    rclpy.init()
    node = ValidationWorldMarkers()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
