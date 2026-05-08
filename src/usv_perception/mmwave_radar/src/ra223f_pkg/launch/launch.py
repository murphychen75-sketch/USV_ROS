from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    default_params_file = os.path.join(
        get_package_share_directory("mmw_radar"),
        "config",
        "mmw_radar_params.yaml",
    )

    params_file_arg = DeclareLaunchArgument(
        "params_file",
        default_value=default_params_file,
        description="YAML parameter file for mmw_radar_node",
    )

    return LaunchDescription(
        [
            params_file_arg,
            Node(
                package="mmw_radar",
                executable="mmw_radar_node",
                name="mmw_radar_node",
                output="screen",
                parameters=[LaunchConfiguration("params_file")],
            ),
        ]
    )
