"""Launch file for the USV MQTT bridge node."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    params_file = LaunchConfiguration("params_file")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("usv_mqtt_bridge"), "config", "params.yaml"]
                ),
                description="Path to the ROS 2 parameter file.",
            ),
            Node(
                package="usv_mqtt_bridge",
                executable="usv_mqtt_bridge_node",
                name="usv_mqtt_bridge_node",
                output="screen",
                parameters=[params_file],
            ),
        ]
    )
