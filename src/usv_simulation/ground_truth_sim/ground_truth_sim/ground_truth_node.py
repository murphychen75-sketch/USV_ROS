#!/usr/bin/env python3
"""Ground truth generator node with RViz visualization."""

from __future__ import annotations

import math
from typing import List, Optional, Set, Tuple

import numpy as np
import rclpy
from geometry_msgs.msg import Point
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import QoSProfile
from rclpy.time import Time
import tf2_ros
from tf2_ros import TransformException
from visualization_msgs.msg import Marker, MarkerArray

from ground_truth_sim.ctrv import (
    TargetState,
    append_history,
    predict_future_path,
    propagate_target,
    sample_annulus_radius,
)

from usv_interfaces.msg import GlobalTrack, GlobalTrackArray


class GroundTruthNode(Node):
    """ROS 2 node that simulates ground-truth targets and RViz markers."""

    def __init__(self) -> None:
        super().__init__("ground_truth_node")
        self._declare_parameters()

        self._dt = self._get_float("update_dt")
        if self._dt <= 0.0:
            self.get_logger().warn("update_dt must be > 0, resetting to 0.02")
            self._dt = 0.02

        seed = self._get_int("rng_seed")
        self._rng = np.random.default_rng(seed if seed >= 0 else None)

        self._frame_id = self._get_string("frame_id")
        self._target_count = self._get_int("target_count")
        self._radius_min = self._get_float("annulus_radius_min")
        self._radius_max = self._get_float("annulus_radius_max")
        if self._radius_min >= self._radius_max:
            self.get_logger().warn("annulus_radius_min >= annulus_radius_max, fixing ordering")
            self._radius_min, self._radius_max = min(self._radius_min, self._radius_max), max(
                self._radius_min, self._radius_max
            )

        self._speed_min = self._get_float("speed_min")
        self._speed_max = self._get_float("speed_max")
        if self._speed_min >= self._speed_max:
            self.get_logger().warn("speed_min >= speed_max, fixing ordering")
            self._speed_min, self._speed_max = min(self._speed_min, self._speed_max), max(
                self._speed_min, self._speed_max
            )

        self._size_w_min = self._get_float("size_width_min")
        self._size_w_max = self._get_float("size_width_max")
        self._size_l_min = self._get_float("size_length_min")
        self._size_l_max = self._get_float("size_length_max")
        self._size_h_min = self._get_float("size_height_min")
        self._size_h_max = self._get_float("size_height_max")

        self._ais_match_probability = self._get_float("ais_match_probability")
        self._omega_noise_std = self._get_float("omega_noise_std")
        self._omega_decay = self._get_float("omega_decay")
        self._omega_limit = self._get_float("omega_limit")

        self._prediction_horizon = self._get_float("prediction_horizon")
        self._prediction_dt = self._get_float("prediction_dt")
        self._history_max_points = self._get_int("history_max_points")
        if self._history_max_points < 1:
            self._history_max_points = 1

        self._reference_robot = self._get_string("reference_robot").strip()
        self._reference_frame = self._get_string("reference_frame").strip() or "map"
        self._reference_child_frame = self._get_string("reference_child_frame").strip() or "base_link"
        self._reference_tf_timeout_sec = self._get_float("reference_tf_timeout_sec")

        self._fence_enabled = self._get_bool("fence_enabled")
        self._fence_x0 = self._get_float("fence_min_x")
        self._fence_x1 = self._get_float("fence_max_x")
        self._fence_y0 = self._get_float("fence_min_y")
        self._fence_y1 = self._get_float("fence_max_y")
        self._fence_maintain = self._get_bool("fence_maintain_target_count")
        if self._fence_x0 > self._fence_x1:
            self._fence_x0, self._fence_x1 = self._fence_x1, self._fence_x0
        if self._fence_y0 > self._fence_y1:
            self._fence_y0, self._fence_y1 = self._fence_y1, self._fence_y0
        if self._fence_enabled:
            if self._fence_x0 >= self._fence_x1 or self._fence_y0 >= self._fence_y1:
                self.get_logger().warn(
                    "fence_enabled 但 min>=max，已关闭围栏；请检查 fence_min_* / fence_max_*"
                )
                self._fence_enabled = False
            else:
                self.get_logger().info(
                    "围栏启用：%s 系 x∈[%.1f, %.1f], y∈[%.1f, %.1f]，越界移除；maintain_count=%s"
                    % (
                        self._frame_id,
                        self._fence_x0,
                        self._fence_x1,
                        self._fence_y0,
                        self._fence_y1,
                        str(self._fence_maintain),
                    )
                )

        self._next_track_id = 1
        self._last_published_track_ids: Set[int] = set()

        self._tf_buffer: Optional[tf2_ros.Buffer] = None
        self._tf_listener: Optional[tf2_ros.TransformListener] = None
        self._pending_reference_init = bool(self._reference_robot)
        self._last_tf_wait_log_ns = 0
        self._node_start_ns = self.get_clock().now().nanoseconds
        self._tf_fail_once_logged = False
        if self._reference_robot:
            self._tf_buffer = tf2_ros.Buffer()
            self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)
            self._targets: List[TargetState] = []
            self.get_logger().info(
                "reference_robot=%s: waiting for TF %s -> %s/%s before spawning targets"
                % (
                    self._reference_robot,
                    self._reference_frame,
                    self._reference_robot,
                    self._reference_child_frame,
                )
            )
            if self._reference_tf_timeout_sec > 0.0:
                self.get_logger().info(
                    "reference_tf_timeout_sec=%.1f: will fall back to map origin (0,0) if TF stays unavailable"
                    % self._reference_tf_timeout_sec
                )
        else:
            self._targets = self._initialize_targets(
                count=self._target_count, center_xy=None
            )

        tracks_topic = self._get_string("tracks_topic").strip() or "sim/ground_truth"
        markers_topic = self._get_string("markers_topic").strip() or "sim/ground_truth_markers"
        if tracks_topic.startswith("/"):
            tracks_topic = tracks_topic.lstrip("/")
        if markers_topic.startswith("/"):
            markers_topic = markers_topic.lstrip("/")

        qos = QoSProfile(depth=10)
        self._track_pub = self.create_publisher(GlobalTrackArray, tracks_topic, qos)
        self._marker_pub = self.create_publisher(MarkerArray, markers_topic, qos)
        self.create_timer(self._dt, self._timer_callback)
        if not self._pending_reference_init:
            self.get_logger().info(
                "GroundTruthNode initialized with %d targets" % len(self._targets)
            )

    # ---------------------------------------------------------------------
    # Target initialization
    # ---------------------------------------------------------------------
    def _declare_parameters(self) -> None:
        self.declare_parameter("update_dt", 0.02)
        self.declare_parameter("frame_id", "map")
        self.declare_parameter("target_count", 5)
        self.declare_parameter("annulus_radius_min", 50.0)
        self.declare_parameter("annulus_radius_max", 500.0)
        self.declare_parameter("speed_min", 2.0)
        self.declare_parameter("speed_max", 12.0)
        self.declare_parameter("size_width_min", 2.0)
        self.declare_parameter("size_width_max", 10.0)
        self.declare_parameter("size_length_min", 5.0)
        self.declare_parameter("size_length_max", 50.0)
        self.declare_parameter("size_height_min", 2.0)
        self.declare_parameter("size_height_max", 15.0)
        self.declare_parameter("ais_match_probability", 0.4)
        self.declare_parameter("omega_noise_std", 0.005)
        self.declare_parameter("omega_decay", 0.99)
        self.declare_parameter("omega_limit", 0.1)
        self.declare_parameter("prediction_horizon", 5.0)
        self.declare_parameter("prediction_dt", 0.25)
        self.declare_parameter("history_max_points", 500)
        self.declare_parameter("rng_seed", -1)
        self.declare_parameter("tracks_topic", "sim/ground_truth")
        self.declare_parameter("markers_topic", "sim/ground_truth_markers")
        self.declare_parameter("reference_robot", "")
        self.declare_parameter("reference_frame", "map")
        self.declare_parameter("reference_child_frame", "base_link")
        # 0 = 无限等待 TF；>0 超时后仍在 map 原点生成环带（避免永不发布 /sim/ground_truth）
        self.declare_parameter("reference_tf_timeout_sec", 25.0)
        # 地图系轴对齐围栏（与 frame_id 一致，通常为 map）；越界则从真值列表移除
        self.declare_parameter("fence_enabled", False)
        self.declare_parameter("fence_min_x", -500.0)
        self.declare_parameter("fence_max_x", 500.0)
        self.declare_parameter("fence_min_y", -500.0)
        self.declare_parameter("fence_max_y", 500.0)
        self.declare_parameter("fence_maintain_target_count", True)

    def _get_bool(self, name: str) -> bool:
        value = self.get_parameter(name).value
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).lower() in ("true", "1", "yes")

    def _get_float(self, name: str) -> float:
        value = self.get_parameter(name).value
        return float(value) if value is not None else 0.0

    def _get_int(self, name: str) -> int:
        value = self.get_parameter(name).value
        return int(value) if value is not None else 0

    def _get_string(self, name: str) -> str:
        value = self.get_parameter(name).value
        return str(value) if value is not None else ""

    # ---------------------------------------------------------------------
    # Target initialization
    # ---------------------------------------------------------------------
    def _lookup_reference_center(self) -> Optional[Tuple[float, float]]:
        if not self._tf_buffer or not self._reference_robot:
            return None
        child = f"{self._reference_robot}/{self._reference_child_frame}"
        try:
            tf_msg = self._tf_buffer.lookup_transform(
                self._reference_frame,
                child,
                Time(),
                timeout=Duration(seconds=0.2),
            )
            t = tf_msg.transform.translation
            return (float(t.x), float(t.y))
        except TransformException as ex:  # pragma: no cover
            if not self._tf_fail_once_logged:
                self.get_logger().debug(
                    "TF lookup %s -> %s failed: %s" % (self._reference_frame, child, ex)
                )
                self._tf_fail_once_logged = True
            return None

    def _inside_fence(self, x: float, y: float) -> bool:
        if not self._fence_enabled:
            return True
        return (
            self._fence_x0 <= x <= self._fence_x1
            and self._fence_y0 <= y <= self._fence_y1
        )

    def _sample_xy_initial(self, center_xy: Optional[Tuple[float, float]]) -> Tuple[float, float]:
        """初始位置：围栏内均匀采样，否则环带采样。"""
        if self._fence_enabled:
            x = self._rng.uniform(self._fence_x0, self._fence_x1)
            y = self._rng.uniform(self._fence_y0, self._fence_y1)
            return (float(x), float(y))
        ox, oy = (0.0, 0.0) if center_xy is None else center_xy
        radius = sample_annulus_radius(self._rng, self._radius_min, self._radius_max)
        bearing = self._rng.uniform(-math.pi, math.pi)
        return (ox + radius * math.cos(bearing), oy + radius * math.sin(bearing))

    def _make_target(self, track_id: int, x: float, y: float) -> TargetState:
        speed = self._rng.uniform(self._speed_min, self._speed_max)
        theta = self._rng.uniform(-math.pi, math.pi)
        omega = 0.0
        size_w = self._rng.uniform(self._size_w_min, self._size_w_max)
        size_l = self._rng.uniform(self._size_l_min, self._size_l_max)
        size_h = self._rng.uniform(self._size_h_min, self._size_h_max)
        is_ais_matched = bool(self._rng.random() < self._ais_match_probability)
        matched_mmsi = (
            int(self._rng.integers(100_000_000, 999_999_999)) if is_ais_matched else 0
        )
        target = TargetState(
            track_id=track_id,
            x=x,
            y=y,
            speed=speed,
            theta=theta,
            omega=omega,
            size_w=size_w,
            size_l=size_l,
            size_h=size_h,
            is_dark_target=not is_ais_matched,
            is_ais_matched=is_ais_matched,
            matched_mmsi=matched_mmsi,
        )
        target.history.append(Point(x=float(x), y=float(y), z=0.0))
        return target

    def _initialize_targets(
        self, count: int, center_xy: Optional[Tuple[float, float]]
    ) -> List[TargetState]:
        targets: List[TargetState] = []
        tid = self._next_track_id
        for _ in range(count):
            x, y = self._sample_xy_initial(center_xy)
            targets.append(self._make_target(tid, x, y))
            tid += 1
        self._next_track_id = tid
        return targets

    # ---------------------------------------------------------------------
    # Timer callback
    # ---------------------------------------------------------------------
    def _timer_callback(self) -> None:
        if self._pending_reference_init:
            center = self._lookup_reference_center()
            if center is not None:
                self._targets = self._initialize_targets(
                    count=self._target_count, center_xy=center
                )
                self._pending_reference_init = False
                self.get_logger().info(
                    "Spawned %d targets around reference (%.2f, %.2f) in frame %s"
                    % (len(self._targets), center[0], center[1], self._reference_frame)
                )
            else:
                now_ns = self.get_clock().now().nanoseconds
                elapsed_sec = (now_ns - self._node_start_ns) * 1e-9
                if (
                    self._reference_tf_timeout_sec > 0.0
                    and elapsed_sec >= self._reference_tf_timeout_sec
                ):
                    child = f"{self._reference_robot}/{self._reference_child_frame}"
                    self.get_logger().error(
                        "TF %s -> %s unavailable after %.1fs; spawning targets at map origin (0,0). "
                        "Check odom frame_id vs static map->.../odom, spawn delay, and reference_child_frame."
                        % (self._reference_frame, child, elapsed_sec)
                    )
                    self._targets = self._initialize_targets(
                        count=self._target_count, center_xy=(0.0, 0.0)
                    )
                    self._pending_reference_init = False
                else:
                    if now_ns - self._last_tf_wait_log_ns > 5_000_000_000:
                        tmo = self._reference_tf_timeout_sec
                        tmo_txt = (
                            "%.0fs timeout" % tmo if tmo > 0.0 else "no timeout (waiting indefinitely)"
                        )
                        self.get_logger().warn(
                            "Still waiting for TF %s -> %s/%s (no /sim/ground_truth yet, elapsed %.0fs, %s)"
                            % (
                                self._reference_frame,
                                self._reference_robot,
                                self._reference_child_frame,
                                elapsed_sec,
                                tmo_txt,
                            )
                        )
                        self._last_tf_wait_log_ns = now_ns
                    return

        for target in self._targets:
            propagate_target(
                target,
                self._dt,
                self._omega_noise_std,
                self._omega_decay,
                self._omega_limit,
                self._rng,
            )
            append_history(target, self._history_max_points)

        if self._fence_enabled:
            self._targets = [t for t in self._targets if self._inside_fence(t.x, t.y)]
            if self._fence_maintain:
                while len(self._targets) < self._target_count:
                    x = float(self._rng.uniform(self._fence_x0, self._fence_x1))
                    y = float(self._rng.uniform(self._fence_y0, self._fence_y1))
                    self._targets.append(self._make_target(self._next_track_id, x, y))
                    self._next_track_id += 1

        array_msg = self._build_track_array()
        self._track_pub.publish(array_msg)
        self._publish_markers(array_msg)

    def _build_track_array(self) -> GlobalTrackArray:
        msg = GlobalTrackArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id

        for target in self._targets:
            track = GlobalTrack()
            track.track_id = target.track_id
            track.x = target.x
            track.y = target.y
            track.v_x = target.v_x
            track.v_y = target.v_y
            track.size_w = target.size_w
            track.size_l = target.size_l
            track.size_h = target.size_h
            track.covariance = [0.0] * 16
            track.is_dark_target = target.is_dark_target
            track.is_ais_matched = target.is_ais_matched
            track.matched_mmsi = target.matched_mmsi
            track.source_model_name = ""
            msg.tracks.append(track)
        return msg

    # ---------------------------------------------------------------------
    # RViz markers
    # ---------------------------------------------------------------------
    def _publish_markers(self, track_array: GlobalTrackArray) -> None:
        stamp = track_array.header.stamp
        current_ids = {t.track_id for t in self._targets}
        removed = self._last_published_track_ids - current_ids

        marker_list: List[Marker] = []
        for tid in removed:
            marker_list.extend(self._make_delete_markers_for_track(tid, stamp))

        for target in self._targets:
            marker_list.append(self._make_position_marker(target, stamp))
            marker_list.append(self._make_path_marker(target, stamp))
            marker_list.append(self._make_history_marker(target, stamp))

        self._last_published_track_ids = current_ids
        markers = MarkerArray()
        markers.markers = marker_list
        self._marker_pub.publish(markers)

    def _make_delete_markers_for_track(self, track_id: int, stamp) -> List[Marker]:
        out: List[Marker] = []
        for ns, mid in (
            ("target_pose", track_id),
            ("target_path", track_id + 1000),
            ("target_history", track_id + 2000),
        ):
            m = Marker()
            m.header.frame_id = self._frame_id
            m.header.stamp = stamp
            m.ns = ns
            m.id = mid
            m.action = Marker.DELETE
            out.append(m)
        return out

    def _make_position_marker(self, target: TargetState, stamp) -> Marker:
        marker = Marker()
        marker.header.frame_id = self._frame_id
        marker.header.stamp = stamp
        marker.ns = "target_pose"
        marker.id = target.track_id
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD
        marker.pose.position.x = target.x
        marker.pose.position.y = target.y
        marker.pose.position.z = target.size_h * 0.5
        marker.pose.orientation.w = 1.0
        marker.scale.x = max(target.size_l, 2.0)
        marker.scale.y = max(target.size_w, 2.0)
        marker.scale.z = max(target.size_h, 1.5)
        if target.is_ais_matched:
            marker.color.r = 0.1
            marker.color.g = 0.8
            marker.color.b = 0.2
        else:
            marker.color.r = 1.0
            marker.color.g = 0.5
            marker.color.b = 0.0
        marker.color.a = 0.9
        marker.lifetime.sec = 0
        marker.lifetime.nanosec = 0
        return marker

    def _make_path_marker(self, target: TargetState, stamp) -> Marker:
        marker = Marker()
        marker.header.frame_id = self._frame_id
        marker.header.stamp = stamp
        marker.ns = "target_path"
        marker.id = target.track_id + 1000
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD
        marker.scale.x = 0.8
        marker.color.a = 0.85
        marker.color.r = 0.2
        marker.color.g = 0.6
        marker.color.b = 1.0 if target.is_ais_matched else 0.2
        marker.points = predict_future_path(
            target, self._prediction_horizon, self._prediction_dt
        )
        return marker

    def _make_history_marker(self, target: TargetState, stamp) -> Marker:
        marker = Marker()
        marker.header.frame_id = self._frame_id
        marker.header.stamp = stamp
        marker.ns = "target_history"
        marker.id = target.track_id + 2000
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD
        marker.scale.x = 0.4
        marker.color.a = 0.9
        marker.color.r = 0.7
        marker.color.g = 0.7
        marker.color.b = 0.7
        marker.points = list(target.history)
        return marker


def main(args=None) -> None:
    rclpy.init(args=args)
    node = GroundTruthNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("GroundTruthNode interrupted, shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
