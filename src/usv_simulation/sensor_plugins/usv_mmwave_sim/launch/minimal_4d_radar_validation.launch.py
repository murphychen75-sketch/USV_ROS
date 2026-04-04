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
        "minimal_4d_radar_validation.sdf",
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

    validation_markers = Node(
        package="usv_mmwave_sim",
        executable="validation_world_markers",
        name="validation_world_markers",
        output="screen",
    )

    # 插件点云 frame_id 为 world；无 TF 时 RViz 无法变换，显示异常或看似全黑。
    static_map_world = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_map_to_world",
        arguments=[
            "--x",
            "0",
            "--y",
            "0",
            "--z",
            "0",
            "--qx",
            "0",
            "--qy",
            "0",
            "--qz",
            "0",
            "--qw",
            "1",
            "--frame-id",
            "map",
            "--child-frame-id",
            "world",
        ],
    )

    return LaunchDescription([
        set_plugin_path,
        static_map_world,
        validation_markers,
        start_gz,
        start_rviz,
    ])
