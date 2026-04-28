import rclpy
from rclpy.node import Node
from usv_interfaces import topics as usv_topics
from usv_interfaces.srv import AutopilotControl


class AutopilotControlServiceNode(Node):
    def __init__(self) -> None:
        super().__init__("autopilot_control_service_node")
        self.declare_parameter("frontend_service_name", usv_topics.SERVICE_AUTOPILOT_CONTROL)
        self.declare_parameter("backend_service_name", "/usv/mavlink/autopilot_control")
        self.declare_parameter("backend_wait_timeout_sec", 1.0)

        frontend_name = self.get_parameter("frontend_service_name").value
        backend_name = self.get_parameter("backend_service_name").value
        self._backend_wait_timeout_sec = float(
            self.get_parameter("backend_wait_timeout_sec").value
        )

        self._backend_client = self.create_client(AutopilotControl, backend_name)
        self.create_service(AutopilotControl, frontend_name, self._handle_request)
        self.get_logger().info(
            f"autopilot control proxy ready: {frontend_name} -> {backend_name}"
        )

    def _handle_request(self, request, response):
        if not self._backend_client.wait_for_service(
            timeout_sec=self._backend_wait_timeout_sec
        ):
            response.success = False
            response.message = "backend autopilot service unavailable"
            return response

        backend_req = AutopilotControl.Request()
        backend_req.set_armed = bool(request.set_armed)
        backend_req.target_mode = request.target_mode
        future = self._backend_client.call_async(backend_req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
        if not future.done() or future.result() is None:
            response.success = False
            response.message = "backend autopilot service timeout"
            return response

        backend_resp = future.result()
        response.success = bool(backend_resp.success)
        response.message = backend_resp.message
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AutopilotControlServiceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

