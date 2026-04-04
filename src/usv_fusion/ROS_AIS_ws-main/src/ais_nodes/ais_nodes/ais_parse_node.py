import rclpy
import rclpy.logging
from rclpy.node import Node

import pyais.constants as pyaisc
from pyais.messages import MessageType1, MessageType5
from nmea_msgs.msg import Sentence

from .AIS_receiver.ais_client import AIS_Client
from ais_reports_interfaces.msg import AISLocationReport, AISStaticAndVoyageReport
from ais_interfaces.msg import EPFSTimeStamp, ManeuverIndicator, NavigationStatus, TurnRate


ais_parse_node_name = "ais_parse_node"


class AISParseNode(Node):
    def __init__(self):
        super().__init__(ais_parse_node_name)
        self.get_logger().info("AIS parse node started!")
        self.declare_parameter("ais_ip", "192.168.254.50")
        self.declare_parameter("ais_port", 22222)
        self.declare_parameter("gps_nmea_topic", "nmea_sentence")

        # Own Vessel
        self.frame_id = "OS"
        self.nmea_topic = self.get_parameter("gps_nmea_topic").get_parameter_value().string_value
        self.ais_ip = self.get_parameter("ais_ip").get_parameter_value().string_value
        self.ais_port = self.get_parameter("ais_port").get_parameter_value().integer_value
        self.ais_client = AIS_Client(
            host=self.ais_ip,
            port=self.ais_port,
        )

        self.location_report_publisher = self.create_publisher(
            msg_type=AISLocationReport,
            topic="ais_location_report",
            qos_profile=10,
        )
        self.static_and_voyage_publisher = self.create_publisher(
            msg_type=AISStaticAndVoyageReport,
            topic="ais_static_and_voyage_report",
            qos_profile=10,
        )
        self.nmea_publisher = self.create_publisher(
            msg_type=Sentence,
            topic=self.nmea_topic,
            qos_profile=10,
        )

        self.ais_client.update_encrypted_handlers(1, self.location_report_handler)
        self.ais_client.update_encrypted_handlers(2, self.location_report_handler)
        self.ais_client.update_encrypted_handlers(3, self.location_report_handler)
        self.ais_client.update_encrypted_handlers(5, self.static_report_handler)
        self.ais_client.update_unencrypted_handler(self.gps_msg_handler)

        self.get_logger().info("Connecting to AIS address: {}:{}".format(self.ais_ip, self.ais_port))
        self.ais_client.start()
        self.ais_client.listen()

    def gps_msg_handler(self, nmea_msg_dict):
        self.get_logger().info("Received nmea msg, head: {}".format(
            nmea_msg_dict["head"]))
        nmea_msg = Sentence()
        nmea_msg.header.stamp = self.get_clock().now().to_msg()
        nmea_msg.header.frame_id = self.frame_id
        nmea_msg.sentence = nmea_msg_dict["raw"]
        self.nmea_publisher.publish(nmea_msg)

    def location_report_handler(self, ais_report: MessageType1):
        report_msg = AISLocationReport()
        report_msg.timestamp = self.get_clock().now().to_msg()
        # copy data
        report_msg.msg_type = ais_report.msg_type
        report_msg.repeat = ais_report.repeat
        report_msg.mmsi = ais_report.mmsi
        # pyais status is type <Navigation Status>
        report_msg.navigation_status.navigation_status = int(ais_report.status)
        # pyais turn could be float if status normal, or status enum if abnormal
        raw_turn_rate = ais_report.turn
        if type(raw_turn_rate) is pyaisc.TurnRate.NO_TI_DEFAULT:
            report_msg.turn_rate.turn_status = TurnRate.NO_TURN_INFORMATION_AVAILABLE
        elif type(raw_turn_rate) is pyaisc.TurnRate.NO_TI_LEFT:
            report_msg.turn_rate.turn_status = TurnRate.TURNING_LEFT_RATE_EXCEEDING_RANGE_NO_TI_AVAILABLE
        elif type(raw_turn_rate) is pyaisc.TurnRate.NO_TI_RIGHT:
            report_msg.turn_rate.turn_status = TurnRate.TURNING_RIGHT_RATE_EXCEEDING_RANGE_NO_TI_AVAILABLE
        else:
            report_msg.turn_rate.turn_status = TurnRate.TURN_STATUS_OK
            report_msg.turn_rate.turn_rate = ais_report.turn
        # sog raw msg 1023 indicates unavailability, otherwise knots/10
        # pyais returns <raw_msg>/10, means 102.3 for unavailability
        report_msg.sog = ais_report.speed
        report_msg.is_valid_sog = False if report_msg.sog == 102.3 else True
    
        report_msg.location_accuracy = ais_report.accuracy
        # longitude 181 means unavailability
        report_msg.longitude = ais_report.lon
        report_msg.is_valid_longitude = False if report_msg.longitude == 181 else True
        # latitude 91 means unavailability
        report_msg.latitude = ais_report.lat
        report_msg.is_valid_latitude = False if report_msg.latitude == 91 else True
        # raw cog(course over ground/speed direction) 3600 means unavailability, else degerees/10, pyais already /10
        report_msg.cog = ais_report.course
        report_msg.is_valid_cog = False if report_msg.cog == 360 else True
        # hdg(true heading) should be [0, 359] int, 511 for unavailability
        report_msg.hdg = ais_report.heading
        report_msg.is_valid_hdg = False if report_msg.hdg == 511 else True
        # EPFS time stamp handling, normal value [0, 59]
        report_msg.epfs_time_stamp.seconds = ais_report.second
        if ais_report.second == 60:
            report_msg.epfs_time_stamp.timestamp_status = EPFSTimeStamp.TIME_STAMP_NOT_AVAILABLE
        elif ais_report.second == 61:
            report_msg.epfs_time_stamp.timestamp_status = EPFSTimeStamp.SYSTEM_MANUAL_INPUT_MODE
        elif ais_report.second == 62:
            report_msg.epfs_time_stamp.timestamp_status = EPFSTimeStamp.EPFS_DEAD_RECKONING_MODE
        elif ais_report.second == 63:
            report_msg.epfs_time_stamp.timestamp_status = EPFSTimeStamp.SYSTEM_INOPERATIVE
        else:
            report_msg.epfs_time_stamp.timestamp_status = EPFSTimeStamp.STATUS_NORMAL
    
        report_msg.maneuver_indicator.maneuver_indicator = int(ais_report.maneuver)
        report_msg.raim = ais_report.raim
        report_msg.radio = ais_report.radio

        self.get_logger().info("Publishing loc report for {}".format(report_msg.mmsi))
        self.location_report_publisher.publish(report_msg)

    def static_report_handler(self, ais_report: MessageType5):
        try:
            report_msg = AISStaticAndVoyageReport()
            report_msg.timestamp = self.get_clock().now().to_msg()
            # copy data
            report_msg.msg_type = ais_report.msg_type
            report_msg.repeat = ais_report.repeat
            report_msg.mmsi = ais_report.mmsi
            report_msg.ais_version = ais_report.ais_version
            report_msg.imo_number = ais_report.imo
            report_msg.call_sign = ais_report.callsign
            report_msg.vessel_name = ais_report.shipname
            report_msg.ship_type = int(ais_report.ship_type)
            report_msg.to_bow = ais_report.to_bow
            report_msg.to_stern = ais_report.to_stern
            report_msg.to_port = ais_report.to_port
            report_msg.to_starboard = ais_report.to_starboard
            report_msg.epfd_fix_type = int(ais_report.epfd)
            report_msg.eta_month = ais_report.month
            report_msg.eta_day = ais_report.day
            report_msg.eta_hour = ais_report.hour
            report_msg.eta_minute = ais_report.minute
            report_msg.draught = ais_report.draught
            report_msg.destination = ais_report.destination
            report_msg.dte = ais_report.dte

            self.get_logger().info("Publishing static and voyage report for {}".format(report_msg.mmsi))
            self.static_and_voyage_publisher.publish(report_msg)
        except Exception as e:
            self.get_logger().warning("Publishing static and voyage report for {} failed.".format(report_msg.mmsi))
            self.get_logger().warning("Exception: {}".format(e))


def main():
    rclpy.init()
    rclpy.spin(AISParseNode())
    rclpy.shutdown()
