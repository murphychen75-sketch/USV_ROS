from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    default_sim_params = os.path.join(
        get_package_share_directory('mmw_radar'),
        'config',
        'mmw_radar_sim_params.yaml',
    )

    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_sim_params,
        description='仿真发布节点参数（默认 15Hz）',
    )

    return LaunchDescription([
        params_file_arg,
        Node(
            package='mmw_radar',
            executable='mmw_radar_sim_publisher.py',
            name='mmw_radar_sim_publisher',
            output='screen',
            parameters=[LaunchConfiguration('params_file')],
        ),
    ])
