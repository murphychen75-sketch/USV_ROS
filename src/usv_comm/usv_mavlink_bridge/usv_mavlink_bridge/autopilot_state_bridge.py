import rclpy
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, SetMode
from rclpy.node import Node
from usv_interfaces import topics as usv_topics
from usv_interfaces.msg import HeartbeatStatus
from usv_interfaces.srv import AutopilotControl


class AutopilotStateBridge(Node):
    def __init__(self) -> None:
        super().__init__("autopilot_state_bridge")
        self.declare_parameter("mavros_state_input_topic", usv_topics.TOPIC_MAVROS_STATE_RAW)
        self.declare_parameter("autopilot_state_output_topic", usv_topics.TOPIC_AUTOPILOT_STATE)
        self.declare_parameter("autopilot_control_service", "/usv/mavlink/autopilot_control")
        self.declare_parameter("mavros_arming_service", "/mavros/cmd/arming")
        self.declare_parameter("mavros_set_mode_service", "/mavros/set_mode")
        self.declare_parameter("service_timeout_sec", 2.0)
        self.declare_parameter("mode_mapping_table", ["MANUAL:manual", "AUTO:auto"])

        self._service_timeout_sec = float(self.get_parameter("service_timeout_sec").value)
        self._mode_map = self._parse_mode_map(self.get_parameter("mode_mapping_table").value)

        self._state_pub = self.create_publisher(
            HeartbeatStatus, self.get_parameter("autopilot_state_output_topic").value, 10
        )
        self.create_subscription(
            State,
            self.get_parameter("mavros_state_input_topic").value,
            self._state_cb,
            10,
        )

        arming_service = self.get_parameter("mavros_arming_service").value
        set_mode_service = self.get_parameter("mavros_set_mode_service").value
        self._arming_client = self.create_client(CommandBool, arming_service)
        self._set_mode_client = self.create_client(SetMode, set_mode_service)

        service_name = self.get_parameter("autopilot_control_service").value
        self.create_service(AutopilotControl, service_name, self._control_cb)
        self.get_logger().info(f"autopilot_state_bridge started, service={service_name}")

    def _parse_mode_map(self, mapping_values) -> dict[str, str]:
        mapping = {}
        for item in mapping_values:
            if ":" not in item:
                continue
            source, target = item.split(":", 1)
            mapping[source.strip()] = target.strip()
        return mapping

    def _normalize_mode(self, mode: str) -> str:
        if mode in self._mode_map:
            return self._mode_map[mode]
        return mode.lower() if mode else "unknown"

    def _state_cb(self, msg: State) -> None:
        out = HeartbeatStatus()
        out.header.stamp = self.get_clock().now().to_msg()
        out.online = bool(msg.connected)
        out.unit = "mcu"
        out.armed_status = bool(msg.armed)
        out.control_mode = self._normalize_mode(msg.mode)
        self._state_pub.publish(out)

    def _control_cb(self, request, response):
        if not self._arming_client.wait_for_service(timeout_sec=self._service_timeout_sec):
            response.success = False
            response.message = "mavros arming service unavailable"
            return response
        if not self._set_mode_client.wait_for_service(timeout_sec=self._service_timeout_sec):
            response.success = False
            response.message = "mavros set_mode service unavailable"
            return response

        arm_req = CommandBool.Request()
        arm_req.value = bool(request.set_armed)
        arm_future = self._arming_client.call_async(arm_req)
        rclpy.spin_until_future_complete(self, arm_future, timeout_sec=self._service_timeout_sec)
        if not arm_future.done() or arm_future.result() is None:
            response.success = False
            response.message = "arming request timeout"
            return response
        arm_resp = arm_future.result()

        mode_sent = True
        if request.target_mode:
            mode_req = SetMode.Request()
            mode_req.base_mode = 0
            mode_req.custom_mode = request.target_mode
            mode_future = self._set_mode_client.call_async(mode_req)
            rclpy.spin_until_future_complete(
                self, mode_future, timeout_sec=self._service_timeout_sec
            )
            if not mode_future.done() or mode_future.result() is None:
                response.success = False
                response.message = "set_mode request timeout"
                return response
            mode_sent = bool(mode_future.result().mode_sent)

        response.success = bool(arm_resp.success) and mode_sent
        response.message = (
            f"armed={arm_resp.success}, mode_sent={mode_sent}, "
            f"target_mode={request.target_mode}"
        )
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AutopilotStateBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

