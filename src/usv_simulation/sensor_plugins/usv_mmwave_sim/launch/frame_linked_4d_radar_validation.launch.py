import os

from ament_index_python.packages import get_package_prefix
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch.actions import SetEnvironmentVariable
from launch_ros.actions import Node


def generate_launch_description():
    pkg_name = "usv_mmwave_sim"
    pkg_share = get_package_share_directory(pkg_name)
    pkg_prefix = get_package_prefix(pkg_name)

    world_file = os.path.join(
        pkg_share,
        "worlds",
        "frame_linked_4d_radar_validation.sdf",
    )
    rviz_config = os.path.join(
        pkg_share,
        "rviz",
        "4d_radar_minimal.rviz",
    )

    plugin_lib_dir = os.path.join(pkg_prefix, "lib")
    old_plugin_path = os.environ.get("GZ_SIM_SYSTEM_PLUGIN_PATH", "")
    if old_plugin_path:
        new_plugin_path = plugin_lib_dir + os.pathsep + old_plugin_path
    else:
        new_plugin_path = plugin_lib_dir

    set_plugin_path = SetEnvironmentVariable(
        name="GZ_SIM_SYSTEM_PLUGIN_PATH",
        value=new_plugin_path,
    )

    start_gz = ExecuteProcess(
        cmd=["gz", "sim", "-r", world_file],
        output="screen",
    )

    start_rviz = ExecuteProcess(
        cmd=["rviz2", "-d", rviz_config],
        output="screen",
    )

    # RViz配置默认使用 map 作为 Fixed Frame；补充 map->world 静态变换。
    static_map_world = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_map_to_world",
        arguments=[
            "--x", "0",
            "--y", "0",
            "--z", "0",
            "--qx", "0",
            "--qy", "0",
            "--qz", "0",
            "--qw", "1",
            "--frame-id", "map",
            "--child-frame-id", "world",
        ],
    )

    # frame_linked_4d_radar_validation.sdf 中 radar_link 在 world 下是固定位置。
    static_world_radar = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_world_to_radar_link",
        arguments=[
            "--x", "0.8",
            "--y", "0",
            "--z", "1.8",
            "--qx", "0",
            "--qy", "0",
            "--qz", "0",
            "--qw", "1",
            "--frame-id", "world",
            "--child-frame-id", "radar_link",
        ],
    )

    return LaunchDescription([
        set_plugin_path,
        static_map_world,
        static_world_radar,
        start_gz,
        start_rviz,
    ])
