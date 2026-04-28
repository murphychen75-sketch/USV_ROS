import json
import time

import psutil
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from usv_interfaces.msg import JetsonStatus
from usv_interfaces import topics as usv_topics


class SystemStatusNode(Node):
    def __init__(self) -> None:
        super().__init__("system_status_node")
        self.declare_parameter("publish_hz", 5.0)
        self.declare_parameter("disk_path", "/")
        self.declare_parameter("jetson_status_topic", usv_topics.TOPIC_JETSON_STATUS)
        self.declare_parameter("status_jetson_json_topic", "/usv/monitor/status_jetson/json")
        self.declare_parameter("use_jtop", True)

        self._disk_path = self.get_parameter("disk_path").value
        self._status_pub = self.create_publisher(
            JetsonStatus, self.get_parameter("jetson_status_topic").value, 10
        )
        self._status_json_pub = self.create_publisher(
            String, self.get_parameter("status_jetson_json_topic").value, 10
        )

        self._boot_time_sec = psutil.boot_time()
        self._jtop = None
        self._use_jtop = self.get_parameter("use_jtop").value
        self._init_jtop()

        publish_hz = max(0.5, float(self.get_parameter("publish_hz").value))
        self.create_timer(1.0 / publish_hz, self._timer_cb)
        self.get_logger().info(f"system_status_node started: {publish_hz:.2f}Hz")

    def _init_jtop(self) -> None:
        if not self._use_jtop:
            return
        try:
            from jtop import jtop  # pylint: disable=import-outside-toplevel

            self._jtop = jtop()
            self._jtop.start()
            self.get_logger().info("jtop connected.")
        except Exception as exc:  # noqa: BLE001
            self._jtop = None
            self.get_logger().warn(f"jtop unavailable, fallback to psutil only: {exc}")

    def _read_gpu_and_temp(self) -> tuple[float, float]:
        gpu_usage = 0.0
        temperature = 0.0
        if self._jtop is not None:
            try:
                stats = self._jtop.stats
                gpu_usage = float(stats.get("GPU", 0.0))
                temperature = float(stats.get("Temp AO", stats.get("Temp CPU", 0.0)))
                return gpu_usage, temperature
            except Exception:  # noqa: BLE001
                pass

        temps = psutil.sensors_temperatures(fahrenheit=False)
        for entries in temps.values():
            if entries:
                temperature = float(entries[0].current)
                break
        return gpu_usage, temperature

    def _timer_cb(self) -> None:
        cpu_usage = float(psutil.cpu_percent(interval=None))
        mem_usage = float(psutil.virtual_memory().percent)
        disk_usage = float(psutil.disk_usage(self._disk_path).percent)
        uptime_ms = int((time.time() - self._boot_time_sec) * 1000.0)
        gpu_usage, temperature = self._read_gpu_and_temp()

        msg = JetsonStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.cpu_usage_percent = cpu_usage
        msg.memory_usage_percent = mem_usage
        msg.gpu_usage_percent = gpu_usage
        msg.temperature_c = temperature
        msg.uptime_ms = uptime_ms
        msg.disk_usage_percent = disk_usage
        self._status_pub.publish(msg)

        payload = {
            "cpu_usage_percent": cpu_usage,
            "memory_usage_percent": mem_usage,
            "gpu_usage_percent": gpu_usage,
            "temperature_c": temperature,
            "uptime_ms": uptime_ms,
            "disk_usage_percent": disk_usage,
        }
        json_msg = String()
        json_msg.data = json.dumps(payload, ensure_ascii=True)
        self._status_json_pub.publish(json_msg)

    def destroy_node(self) -> bool:
        if self._jtop is not None:
            try:
                self._jtop.close()
            except Exception:  # noqa: BLE001
                pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SystemStatusNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

