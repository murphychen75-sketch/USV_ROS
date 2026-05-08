import rclpy
from rclpy.node import Node
from tf2_ros import TransformBroadcaster

from geometry_msgs.msg import TransformStamped
from ais_reports_interfaces.msg import AISLocationReport
from sensor_msgs.msg import NavSatFix

from .geo_utils import haversin_distance, latlon_to_enu, heading_to_enu_quaternion


class AISTfNode(Node):
    def __init__(self):
        super().__init__("ais_tf_node")
        self.get_logger().info("AIS tf node started!")

        self.declare_parameter("os_name", "OS")
        self.declare_parameter("filter_threshold_km", 10.0)

        self.os_name = self.get_parameter("os_name").get_parameter_value().string_value
        self.os_enu = self.os_name + "_enu"
        self.threshold_km = self.get_parameter("filter_threshold_km").get_parameter_value().double_value
        self.lon = None
        self.lat = None

        self.self_gps_sub = self.create_subscription(
            msg_type=NavSatFix,
            topic="/fix",
            callback=self.self_gps_cb,
            qos_profile=10,
        )

        self.ais_location_sub = self.create_subscription(
            msg_type=AISLocationReport,
            topic="/ais_location_report",
            callback=self.ais_location_cb,
            qos_profile=10,
        )

        self.tf_broadcaster = TransformBroadcaster(self)

    def self_gps_cb(self, msg: NavSatFix):
        self.lon = msg.longitude
        self.lat = msg.latitude
        self.get_logger().info("Updated OS location: {},{}".format(self.lon, self.lat))

    def ais_location_cb(self, msg: AISLocationReport):
        if self.lon is None or self.lat is None:
            self.get_logger().warning("AIS location report received, but OS location unknown.")
            return
        mmsi = msg.mmsi
        lon = msg.longitude
        lat = msg.latitude
        distance = haversin_distance((self.lon, self.lat), (lon, lat))

        self.get_logger().info("Received AIS location report, vessel: {}, distance: {}.".format(mmsi, distance))
        if distance <= self.threshold_km:
            self.publish_transform(msg)

    def publish_transform(
            self,
            msg: AISLocationReport,
    ):
        """
        if invalid heading (511), heading set to 0 on default
        """
        mmsi = msg.mmsi
        lon = msg.longitude
        lat = msg.latitude
        heading = msg.hdg

        x, y = latlon_to_enu(
            ref_lon=self.lon,
            ref_lat=self.lat,
            lon=lon,
            lat=lat,
        )
        self.get_logger().info("Tf vessel: {}, xy: {}, {}, heading: {}.".format(mmsi, x, y, heading))

        t = TransformStamped()

        t.header.stamp = msg.timestamp
        t.header.frame_id = self.os_enu
        t.child_frame_id = f"{mmsi}"

        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = 0.0

        if heading != 511:
            x, y, z, w = heading_to_enu_quaternion(heading)
            t.transform.rotation.x = x
            t.transform.rotation.y = y
            t.transform.rotation.z = z
            t.transform.rotation.w = w

        self.tf_broadcaster.sendTransform(t)


def main():
    rclpy.init()
    rclpy.spin(AISTfNode())
    rclpy.shutdown()