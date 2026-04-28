from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import os


def generate_launch_description():
    params = os.path.join(
        get_package_share_directory("usv_monitor"),
        "config",
        "monitor_params.yaml",
    )
    return LaunchDescription(
        [
            Node(
                package="usv_monitor",
                executable="system_status_node",
                name="system_status_node",
                output="screen",
                parameters=[params],
            ),
            Node(
                package="usv_monitor",
                executable="heartbeat_node",
                name="heartbeat_node",
                output="screen",
                parameters=[params],
            ),
            Node(
                package="usv_monitor",
                executable="autopilot_control_service_node",
                name="autopilot_control_service_node",
                output="screen",
                parameters=[params],
            ),
            Node(
                package="usv_monitor",
                executable="alarm_watchdog_node",
                name="alarm_watchdog_node",
                output="screen",
                parameters=[params],
            ),
        ]
    )
