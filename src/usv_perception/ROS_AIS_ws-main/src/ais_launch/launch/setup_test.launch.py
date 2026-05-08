from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
#from launch.event_handlers import OnProcessExit
#from launch.actions import IncludeLaunchDescription
#from launch.launch_description_sources import PythonLaunchDescriptionSource
#import os
#from ament_index_python import get_package_share_directory


def generate_launch_description():
    bag_path_arg = DeclareLaunchArgument(
        'bag_path',
        description="Path to the ROS2 bag file or directory to be played."
    )

    bag_path = LaunchConfiguration("bag_path")
    use_db_arg = DeclareLaunchArgument(
        "use_db",
        default_value="false",
        description="Whether to start ais_db_node (requires pymysql and DB).",
    )

    bag = ExecuteProcess(
        cmd=['ros2', 'bag', 'play', bag_path],
        output='screen',
    )

    nmea2gps = Node(
            package="nmea_navsat_driver",
            executable="nmea_topic_driver",
    )

    # typical develope environment may not have ais db
    ais_db = Node(
            package="ais_nodes",
            executable="ais_db_node",
            condition=IfCondition(LaunchConfiguration("use_db")),
    )

    ais_tf = Node(
            package="ais_nodes",
            executable="ais_tf_node",
    )

    return LaunchDescription([
        use_db_arg,
        nmea2gps,
        ais_db,
        bag,
        ais_tf,
    ])