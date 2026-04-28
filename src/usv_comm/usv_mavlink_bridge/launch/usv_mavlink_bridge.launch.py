from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    params = os.path.join(
        get_package_share_directory('usv_mavlink_bridge'),
        'config',
        'bridge_topics.yaml'
    )
    return LaunchDescription([
        Node(
            package='usv_mavlink_bridge',
            executable='imu_sim',
            name='imu_sim',
            output='screen',
            parameters=[params]
        ),
        Node(
            package='usv_mavlink_bridge',
            executable='heartbeat',
            name='mav_heartbeat',
            output='screen'
        ),
        Node(
            package='usv_mavlink_bridge',
            executable='imu_bridge',
            name='mav_imu_bridge',
            output='screen',
            parameters=[params]
        ),
        Node(
            package='usv_mavlink_bridge',
            executable='gps_sim',
            name='gps_sim',
            output='screen',
            parameters=[params]
        ),
        Node(
            package='usv_mavlink_bridge',
            executable='gps_bridge',
            name='mav_gps_bridge',
            output='screen',
            parameters=[params]
        ),
        Node(
            package='usv_mavlink_bridge',
            executable='rc_bridge',
            name='mav_rc_bridge',
            output='screen',
            parameters=[params]
        ),
        Node(
            package='usv_mavlink_bridge',
            executable='autopilot_state_bridge',
            name='autopilot_state_bridge',
            output='screen',
            parameters=[params]
        ),
    ])
