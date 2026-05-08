from launch import LaunchDescription
from launch_ros.actions import Node
#from launch.actions import RegisterEventHandler, ExecuteProcess
#from launch.event_handlers import OnProcessExit
#from launch.actions import IncludeLaunchDescription
#from launch.launch_description_sources import PythonLaunchDescriptionSource
#import os
#from ament_index_python import get_package_share_directory


def generate_launch_description():
    ais_src = Node(
            package="ais_nodes",
            executable="ais_parse_node",
    )

    nmea2gps = Node(
            package="nmea_navsat_driver",
            executable="nmea_topic_driver",
    )

    ais_db = Node(
            package="ais_nodes",
            executable="ais_db_node",
    )

    ais_tf = Node(
            package="ais_nodes",
            executable="ais_tf_node",
    )

    ais_map_pub = Node(
            package="ais_nodes",
            executable="ais_map_pub_node",
    )

    return LaunchDescription([
        ais_src, nmea2gps, ais_db, ais_tf, ais_map_pub,
    ])