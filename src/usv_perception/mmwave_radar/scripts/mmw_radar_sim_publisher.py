#!/usr/bin/env python3
"""无雷达联调：以固定频率发布合成毫米波目标（与 mmw_radar_node 输出话题一致）。"""

import math
from typing import Any, Dict, List

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header
from visualization_msgs.msg import Marker, MarkerArray

from usv_interfaces.msg import MmwaveTarget, MmwaveTargetArray

OBJECT_FIELDS = [
    PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
    PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
    PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
    PointField(name='width', offset=12, datatype=PointField.FLOAT32, count=1),
    PointField(name='length', offset=16, datatype=PointField.FLOAT32, count=1),
    PointField(name='height', offset=20, datatype=PointField.FLOAT32, count=1),
    PointField(name='xvel_abs', offset=24, datatype=PointField.FLOAT32, count=1),
    PointField(name='yvel_abs', offset=28, datatype=PointField.FLOAT32, count=1),
    PointField(name='xacc_abs', offset=32, datatype=PointField.FLOAT32, count=1),
    PointField(name='yacc_abs', offset=36, datatype=PointField.FLOAT32, count=1),
    PointField(name='heading_angle', offset=40, datatype=PointField.FLOAT32, count=1),
    PointField(name='classify_type', offset=44, datatype=PointField.FLOAT32, count=1),
    PointField(name='classify_prob', offset=48, datatype=PointField.FLOAT32, count=1),
    PointField(name='objmotion_status', offset=52, datatype=PointField.FLOAT32, count=1),
    PointField(name='obstacle_prob', offset=56, datatype=PointField.FLOAT32, count=1),
    PointField(name='track_id', offset=60, datatype=PointField.FLOAT32, count=1),
]

POINTCLOUD_FIELDS = [
    PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
    PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
    PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
    PointField(name='range', offset=12, datatype=PointField.FLOAT32, count=1),
    PointField(name='amb_rangerate', offset=16, datatype=PointField.FLOAT32, count=1),
    PointField(name='unamb_rangerate', offset=20, datatype=PointField.FLOAT32, count=1),
    PointField(name='rangerate', offset=24, datatype=PointField.FLOAT32, count=1),
    PointField(name='azimuth_deg', offset=28, datatype=PointField.FLOAT32, count=1),
    PointField(name='elevation_deg', offset=32, datatype=PointField.FLOAT32, count=1),
    PointField(name='snr', offset=36, datatype=PointField.FLOAT32, count=1),
    PointField(name='rcs', offset=40, datatype=PointField.FLOAT32, count=1),
    PointField(name='confidence', offset=44, datatype=PointField.FLOAT32, count=1),
    PointField(name='unamb_rangeratemask', offset=48, datatype=PointField.FLOAT32, count=1),
    PointField(name='snr_azi', offset=52, datatype=PointField.FLOAT32, count=1),
]


def default_objects() -> List[Dict[str, Any]]:
    return [
        {
            'track_id': 1,
            'x': 12.0, 'y': -2.0, 'z': 0.5,
            'xvel': 3.0, 'yvel': 0.2, 'xacc': 0.0, 'yacc': 0.0,
            'width': 1.8, 'length': 4.5, 'height': 1.6,
            'heading': 5.0, 'classify_type': 3.0, 'classify_prob': 80.0,
            'motion': 1.0, 'obstacle_prob': 90.0,
        },
        {
            'track_id': 2,
            'x': 25.0, 'y': 3.0, 'z': 0.0,
            'xvel': -1.0, 'yvel': 0.0, 'xacc': 0.0, 'yacc': 0.0,
            'width': 2.0, 'length': 5.0, 'height': 1.8,
            'heading': -10.0, 'classify_type': 3.0, 'classify_prob': 75.0,
            'motion': 0.0, 'obstacle_prob': 85.0,
        },
    ]


class MmwRadarSimPublisher(Node):
    def __init__(self) -> None:
        super().__init__('mmw_radar_sim_publisher')

        self.declare_parameter('publish_rate_hz', 15.0)
        self.declare_parameter('raw_pointcloud_topic', '/mmw_radar/raw_pointcloud_topic')
        self.declare_parameter('raw_object_topic', '/mmw_radar/raw_objectList_topic')
        self.declare_parameter('target_array_topic', '/perception/radar/mmw/objects')
        self.declare_parameter('object_marker_topic', '/mmw_radar/object_marker')
        self.declare_parameter('frame_id', 'mmw_radar')

        rate_hz = self.get_parameter('publish_rate_hz').get_parameter_value().double_value
        raw_pc_topic = self.get_parameter('raw_pointcloud_topic').get_parameter_value().string_value
        raw_obj_topic = self.get_parameter('raw_object_topic').get_parameter_value().string_value
        target_topic = self.get_parameter('target_array_topic').get_parameter_value().string_value
        marker_topic = self.get_parameter('object_marker_topic').get_parameter_value().string_value
        self._frame_id = self.get_parameter('frame_id').get_parameter_value().string_value

        self._pub_raw_pc = self.create_publisher(PointCloud2, raw_pc_topic, 10)
        self._pub_raw_obj = self.create_publisher(PointCloud2, raw_obj_topic, 10)
        self._pub_targets = self.create_publisher(MmwaveTargetArray, target_topic, 10)
        self._pub_markers = self.create_publisher(MarkerArray, marker_topic, 10)

        period = 1.0 / rate_hz if rate_hz > 0.0 else 1.0 / 15.0
        self._timer = self.create_timer(period, self._publish_frame)
        self.get_logger().info(
            f'无雷达仿真发布已启动: {rate_hz:.1f} Hz -> raw_object + target_array + marker'
        )

    def _make_header(self) -> Header:
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = self._frame_id
        return header

    def _build_raw_object_cloud(self, header: Header, objects: List[Dict[str, Any]]) -> PointCloud2:
        points = [
            (
                o['x'], o['y'], o['z'],
                o['width'], o['length'], o['height'],
                o['xvel'], o['yvel'], o['xacc'], o['yacc'],
                o['heading'], o['classify_type'], o['classify_prob'],
                o['motion'], o['obstacle_prob'], float(o['track_id']),
            )
            for o in objects
        ]
        return point_cloud2.create_cloud(header, OBJECT_FIELDS, points)

    def _build_raw_pointcloud(self, header: Header) -> PointCloud2:
        points = [(10.0, 1.0, 0.2, 10.05, 0.0, 0.5, 0.5, 5.0, 0.0, 12.0, 0.5, 8.0, 0.9, 0.0)]
        return point_cloud2.create_cloud(header, POINTCLOUD_FIELDS, points)

    def _build_target_array(self, header: Header, objects: List[Dict[str, Any]]) -> MmwaveTargetArray:
        msg = MmwaveTargetArray()
        msg.header = header
        for o in objects:
            t = MmwaveTarget()
            t.x = float(o['x'])
            t.y = float(o['y'])
            t.v_x = float(o['xvel'])
            t.v_y = float(o['yvel'])
            t.size_w = float(o['width'])
            t.size_l = float(o['length'])
            t.size_h = float(o['height'])
            t.objmotion_status = 1 if int(o['motion']) != 0 else 0
            t.track_id = int(o['track_id'])
            msg.targets.append(t)
        return msg

    def _build_markers(self, header: Header, objects: List[Dict[str, Any]]) -> MarkerArray:
        arr = MarkerArray()
        for idx, o in enumerate(objects):
            m = Marker()
            m.header = header
            m.id = idx
            m.type = Marker.CUBE
            m.action = Marker.ADD
            m.pose.position.x = float(o['x'])
            m.pose.position.y = float(o['y'])
            m.pose.position.z = float(o['z'])
            heading_rad = math.radians(float(o['heading']))
            m.pose.orientation.w = math.cos(heading_rad / 2.0)
            m.pose.orientation.z = math.sin(heading_rad / 2.0)
            m.scale.x = float(o['length'])
            m.scale.y = float(o['width'])
            m.scale.z = float(o['height'])
            m.color.r = 0.0
            m.color.g = 0.0
            m.color.b = 1.0
            m.color.a = 0.5
            m.lifetime.sec = 1
            arr.markers.append(m)
        return arr

    def _publish_frame(self) -> None:
        header = self._make_header()
        objects = default_objects()
        self._pub_raw_pc.publish(self._build_raw_pointcloud(header))
        self._pub_raw_obj.publish(self._build_raw_object_cloud(header, objects))
        self._pub_targets.publish(self._build_target_array(header, objects))
        self._pub_markers.publish(self._build_markers(header, objects))


def main() -> None:
    rclpy.init()
    node = MmwRadarSimPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
