import rclpy
import rclpy.logging
from rclpy.node import Node

import pymysql
from ais_interfaces.srv import VesselStaticInfoQuery
from ais_reports_interfaces.msg import AISStaticAndVoyageReport


ais_db_node_name = "ais_db_node"
db_setup = {
    "host": "localhost",
    "port": 3306,
    "user": "cczh",
    "passwd": "cczh2024",
    "db": "ais_data",
}

class AISDBNode(Node):
    def __init__(self):
        super().__init__(ais_db_node_name)
        self.get_logger().info("AIS DB node started!")

        self.static_and_voyage_sub = self.create_subscription(
            msg_type=AISStaticAndVoyageReport,
            topic="ais_static_and_voyage_report",
            callback=self.static_and_voyage_subscriber_cb,
            qos_profile=10,
        )

        self.vessel_static_info_query_serv = self.create_service(
            VesselStaticInfoQuery,
            "vessel_static_info_query",
            self.static_info_service_cb,
        )
        self.init_db()

    def static_and_voyage_subscriber_cb(self, msg: AISStaticAndVoyageReport):
        self.get_logger().info("Received static info of {}".format(msg.mmsi))
        self.store_or_udpate_static(msg)

    def static_info_service_cb(self, request, response):
        self.get_logger().info("Received static info query request for {}".format(request.mmsi))
        mmsi = request.mmsi
        query_result = self.query_static(mmsi)
        if query_result:
            response.mmsi = mmsi
            response.available = True
            response.vessel_name = query_result["vessel_name"]
            response.to_bow = query_result["to_bow"]
            response.to_stern = query_result["to_stern"]
            response.to_port = query_result["to_port"]
            response.to_starboard = query_result["to_starboard"]
            response.draught = query_result["draught"]
            return response
        else:
            response.mmsi = mmsi
            response.available = False
            return response

    def init_db(self):
        self.get_logger().info("Try connecting to db, use config: {}".format(
            db_setup
        ))
        self.connect = pymysql.Connect(**db_setup)
        self.cursor = self.connect.cursor()
        self.get_logger().info("DB connected")

    def store_or_udpate_static(self, msg: AISStaticAndVoyageReport):
        mmsi = msg.mmsi
        vessel_name = msg.vessel_name
        to_bow = msg.to_bow
        to_stern = msg.to_stern
        to_port = msg.to_port
        to_starboard = msg.to_starboard
        draught = msg.draught

        self.get_logger().info(f"INFO: {vessel_name} {to_bow} {to_stern} {to_port} {to_starboard} {draught}")
        # if already in db, update, else insert
        if self.query_static(mmsi) is not None:
            self.get_logger().info("MMSI exists in db, updating info...")
            sql = "UPDATE static_info SET vessel_name = '{}', to_bow = {}, to_stern = {}, to_port = {}, to_starboard = {}, draught = {} WHERE mmsi = {}".format(
                vessel_name, to_bow, to_stern, to_port, to_starboard, draught, mmsi
            )
        else:
            sql = "INSERT INTO static_info ( mmsi, vessel_name, to_bow, to_stern, to_port, to_starboard, draught ) VALUES( {}, '{}', {}, {}, {}, {}, {} )".format(
                mmsi, vessel_name, to_bow, to_stern, to_port, to_starboard, draught,
            )
        self.cursor.execute(sql)
        self.connect.commit()

    def query_static(self, mmsi):
        sql = f"SELECT vessel_name, to_bow, to_stern, to_port, to_starboard, draught FROM static_info WHERE mmsi = {mmsi}"
        self.cursor.execute(sql)
        self.connect.commit()

        db_select_result = self.cursor.fetchall()
        if len(db_select_result) == 0:
            return

        # else query success
        query_result = {
            "vessel_name": db_select_result[0][0],
            "to_bow": db_select_result[0][1],
            "to_stern": db_select_result[0][2],
            "to_port": db_select_result[0][3],
            "to_starboard": db_select_result[0][4],
            "draught":  db_select_result[0][5],
        }
        return query_result


def main():
    rclpy.init()
    rclpy.spin(AISDBNode())
    rclpy.shutdown()
