import rclpy
import geopandas as gpd
import numpy as np
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup, MutuallyExclusiveCallbackGroup
from tf2_ros import StaticTransformBroadcaster
from geocube.api.core import make_geocube
from threading import Lock
from shapely.geometry import Polygon

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import Pose, TransformStamped

from ais_reports_interfaces.msg import AISLocationReport
from ais_interfaces.srv import VesselStaticInfoQuery 
from sensor_msgs.msg import NavSatFix

from .geo_utils import latlon_to_enu
from .geo_utils.combine import init_s57_config, combine_and_crop


class AISMapPubNode(Node):
    def __init__(self):
        super().__init__("ais_map_pub_node")
        self.get_logger().info("AIS map publisher node started!")

        # query srv will be called inside sub cb, thus should use independent cb group
        self.srv_group = ReentrantCallbackGroup()
        # timer cb should not be called at same time
        # since publish timer may flush (therefore del dict data)
        self.timer_group = MutuallyExclusiveCallbackGroup()

        # s57 ENCs dir path
        self.declare_parameter("s57_dir", "/home/cczh/00 Data S57/data")
        # coverage config path
        self.declare_parameter("s57_coverage", "/home/cczh/00 Data S57/coverage.json")
        # resolution for occupancy grid (m)
        self.declare_parameter("resolution", 10.0)
        # will return map in this range (m)
        self.declare_parameter("los_distance", 5000)
        # buffer size for point geoms (m)
        self.declare_parameter("buffer_size", 5.0)
        # default value for occupied grids: 100; ships' occupancy will decrease this value
        # in each publish period
        self.declare_parameter("decay_per_period", 20)
        # publish an occupancy map every this seconds (s)
        self.declare_parameter("pub_period", 10)

        self.declare_parameter("map_topic", "s57_data")
        self.declare_parameter("map_name", "map")
        self.declare_parameter("os_name", "OS")

        self.s57_dir = self.get_parameter("s57_dir").get_parameter_value().string_value
        self.s57_coverage = self.get_parameter("s57_coverage").get_parameter_value().string_value
        self.resolution = self.get_parameter("resolution").get_parameter_value().double_value
        self.los_distance = self.get_parameter("los_distance").get_parameter_value().integer_value
        self.buffer_size = self.get_parameter("buffer_size").get_parameter_value().double_value
        self.decay_per_period = self.get_parameter("decay_per_period").get_parameter_value().integer_value
        self.pub_period = self.get_parameter("pub_period").get_parameter_value().integer_value
        self.map_topic = self.get_parameter("map_topic").get_parameter_value().string_value
        self.map_name = self.get_parameter("map_name").get_parameter_value().string_value
        self.os_name = self.get_parameter("os_name").get_parameter_value().string_value
        self.os_enu = self.os_name + "_enu"


        init_s57_config(self.s57_dir, self.s57_coverage)
        # each element should be
        # mmsi: (lat, lon, hdg, to_bow, to_stern, to_port, to_starboard, occupancy_value)
        self.vessel_dict = {}
        self.vessel_dict_lock = Lock()

        # subscribe to os loc and locations reports
        self.gps_sub = self.create_subscription(
            msg_type=NavSatFix,
            topic="/fix",
            callback=self.gps_cb,
            qos_profile=10,
        )

        self.map_publisher = self.create_publisher(
            OccupancyGrid,
            self.map_topic,
            10,
        )

        self.ais_location_sub = self.create_subscription(
            msg_type=AISLocationReport,
            topic="/ais_location_report",
            callback=self.ais_location_cb,
            qos_profile=10,
        )

        self.static_query_cli = self.create_client(
            VesselStaticInfoQuery,
            "vessel_static_info_query",
            callback_group=self.srv_group,
        )
        
        while not self.static_query_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Vessel static and voyage info unavailable, try connecting...")

        self.create_timer(10, self.timer_cb, callback_group=self.timer_group)
        self.create_timer(29, self.refresh_vessel_static_cb, callback_group=self.timer_group)

        # publish relevant tf for map (compared to os ENU)
        self.map_tf_pub = StaticTransformBroadcaster(self)
        self.publish_map_tf()

    def publish_map_tf(self):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = self.os_enu
        t.child_frame_id = self.map_name

        self.map_tf_pub.sendTransform(t)
    
    def cube_to_msg(self, grid_cube):
        grid_msg = OccupancyGrid()
        grid_msg.header.frame_id = self.map_name
        grid_msg.header.stamp = self.get_clock().now().to_msg()
        grid_msg.info.map_load_time = self.get_clock().now().to_msg()
        # use default here as demo, should be replaced with coord of the left_lower cell
        #grid_msg.info.origin
        grid_origin = Pose()
        grid_origin.position.x = -float(self.los_distance)
        grid_origin.position.y = -float(self.los_distance)
        grid_msg.info.resolution = self.resolution
        grid_msg.info.width = len(grid_cube.x)
        grid_msg.info.height = len(grid_cube.y)
        grid_msg.info.origin = grid_origin

        grid_data = np.array(grid_cube.occupied)
        #grid_data = grid_data.T
        grid_data = np.where(np.isnan(grid_data), 0, grid_data)
        grid_data = grid_data.reshape([-1])
        grid_data = [int(d) for d in grid_data]
        grid_msg.data = grid_data
        #print(grid_msg)
        return grid_msg

    def is_valid_location_report(self, msg: AISLocationReport):
        return msg.is_valid_latitude and msg.is_valid_longitude and msg.is_valid_hdg

    def update_vessel_dynamic(
            self,
            mmsi: int,
            lon: float,
            lat: float,
            hdg: int,
    ):
        # mmsi: (lat, lon, hdg, to_bow, to_stern, to_port, to_starboard, occupancy_value)
        if not mmsi in self.vessel_dict.keys():
            with self.vessel_dict_lock:
                self.vessel_dict[mmsi] = (
                    lat, lon, hdg, None, None, None, None, 100,
                )
        else:
            _, _, _, to_bow, to_stern, to_port, to_starboard, _ = self.vessel_dict[mmsi]

            with self.vessel_dict_lock:
                self.vessel_dict[mmsi] = (
                    lat, lon, hdg, to_bow, to_stern, to_port, to_starboard, 100,
                )

    def vessel_has_static_info(self, mmsi):
        if not mmsi in self.vessel_dict.keys():
            return False
        else:
            _, _, _, to_bow, to_stern, to_port, to_starboard, _ = self.vessel_dict[mmsi]
            return to_bow is not None and to_stern is not None and to_port is not None and to_starboard is not None


    def update_vessel_static(
            self,
            mmsi: int,
            to_bow: int,
            to_stern: int,
            to_port: int,
            to_starboard: int,
            draught: float,
    ):
        if not mmsi in self.vessel_dict.keys():
            return
        else:
            lat, lon, hdg, _, _, _, _, occup_value = self.vessel_dict[mmsi]
            with self.vessel_dict_lock:
                self.vessel_dict[mmsi] = (
                    lat, lon, hdg, to_bow, to_stern, to_port, to_starboard, occup_value,
                )

    def flush_all_vessels(self):
        mmsis = list(self.vessel_dict.keys())
        for mmsi in mmsis:
            lat, lon, hdg, to_bow, to_stern, to_port, to_starboard, occup_value = self.vessel_dict[mmsi]

            if occup_value <= self.decay_per_period:
                with self.vessel_dict_lock:
                    del self.vessel_dict[mmsi]
                continue
            # else decay mmsi info
            else:
                occup_value -= self.decay_per_period

            with self.vessel_dict_lock:
                self.vessel_dict[mmsi] = (
                    lat, lon, hdg, to_bow, to_stern, to_port, to_starboard, occup_value,
                )
            

    def query_static_info(self, mmsi: int):
        req = VesselStaticInfoQuery.Request()
        req.mmsi = mmsi
        # returns a future
        return self.static_query_cli.call_async(req)
    
    def gps_cb(self, msg: NavSatFix):
        self.lon = msg.longitude
        self.lat = msg.latitude
        self.get_logger().info("Updated OS location: {},{}".format(self.lon, self.lat))

    def ais_location_cb(self, msg: AISLocationReport):
        # only handles msg with valid longi, lati and heading
        if not self.is_valid_location_report(msg):
            return

        mmsi = msg.mmsi
        lon = msg.longitude
        lat = msg.latitude
        hdg = msg.hdg
        self.get_logger().info(f"Received report, {mmsi}: ({lon}, {lat}), heading {hdg}.")
        # update vessel dict
        self.update_vessel_dynamic(
            mmsi,
            lon,
            lat,
            hdg,
        )
        # query if necessay
        if not self.vessel_has_static_info(mmsi):
            query_future = self.query_static_info(mmsi)
            query_future.add_done_callback(self.query_done_cb)

    def query_done_cb(self, future):
        try:
            response: VesselStaticInfoQuery.Response = future.result()
            if not response.available:
                self.get_logger().warning(f"Query {response.mmsi} failed, data unavailable for now.")
            else:
                self.update_vessel_static(
                    response.mmsi,
                    response.to_bow,
                    response.to_stern,
                    response.to_port,
                    response.to_starboard,
                    response.draught,
                )
        except:
            self.get_logger().warning("Query static info failed.")
        
    def valid_vessel_within_los(
            self,
            x, y, to_bow, to_stern, to_port, to_starboard,
    ):
        if to_bow is None or to_stern is None or to_port is None or to_starboard is None:
            return False
        if to_bow == 0 or to_stern == 0 or to_port == 0 or to_starboard == 0:
            return False
        if np.linalg.norm([x, y]) >= self.los_distance:
            return False
        return True
        
        
    def gen_vessel_geom(self, x, y, hdg, to_bow, to_stern, to_port, to_starboard):
        # assume vessel is rectangle
        # convert hdg to angle in xoy
        psi = np.deg2rad(90.0 - hdg)
        psi_bow = psi
        psi_port = psi + np.pi/2
        psi_starboard = psi - np.pi/2
        psi_stern = psi + np.pi
        # calc vec to each edge
        vec_bow = to_bow * np.array([np.cos(psi_bow), np.sin(psi_bow)])
        vec_stern = to_stern * np.array([np.cos(psi_stern), np.sin(psi_stern)])
        vec_port = to_port * np.array([np.cos(psi_port), np.sin(psi_port)])
        vec_starboard = to_starboard * np.array([np.cos(psi_starboard), np.sin(psi_starboard)])
        # calc each point
        corner1 = vec_bow + vec_port
        corner2 = vec_port + vec_stern
        corner3 = vec_stern + vec_starboard
        corner4 = vec_starboard + vec_bow
        # shift each point
        shift = np.array([x, y])
        corner1 += shift
        corner2 += shift
        corner3  += shift
        corner4  += shift
        # create polygon
        return Polygon([corner1, corner2, corner3, corner4])

    def timer_cb(self):
        self.get_logger().info("Publishing map.")
        #self.get_logger().info(f"{self.vessel_dict}")
        # generate map
        # case gdf empty case should be checked
        vec_obs_gdf, m_covr = combine_and_crop(longi=self.lon, lati=self.lat, size=self.los_distance, buffer_size=self.buffer_size)
        vessel_keys = list(self.vessel_dict.keys())
        # convert vessels inf to geom
        for vessel in vessel_keys:
            lat, lon, hdg, to_bow, to_stern, to_port, to_starboard, occup_value = self.vessel_dict[vessel]
            x, y = latlon_to_enu(self.lon, self.lat, lon, lat)
            if not self.valid_vessel_within_los(x, y, to_bow, to_stern, to_port, to_starboard):
                continue
            ship_geom = self.gen_vessel_geom(x, y, hdg, to_bow, to_stern, to_port, to_starboard)
            vec_obs_gdf.loc[len(vec_obs_gdf)] = [ship_geom, occup_value]

        # publish map
        # fake crs for flat rasterization
        vec_obs_gdf = vec_obs_gdf.set_crs(epsg=4674, inplace=True)
        print(vec_obs_gdf)
        cube = make_geocube(vector_data=vec_obs_gdf, resolution=(self.resolution, self.resolution), geom=m_covr, fill=0)
        map_msg = self.cube_to_msg(cube)
        self.map_publisher.publish(map_msg)
        # refresh vessel dict
        self.flush_all_vessels()

    def refresh_vessel_static_cb(self):
        self.get_logger().info("Try querying vessel statics.")
        # try query each vessel without static info
        for vessel in self.vessel_dict.keys():
            if not self.vessel_has_static_info(vessel):
                query_future = self.query_static_info(vessel)
                query_future.add_done_callback(self.query_done_cb)


def main():
    rclpy.init()

    node = AISMapPubNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    try:
        executor.spin()
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()