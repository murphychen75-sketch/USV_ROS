import os
import subprocess
import yaml

from ament_index_python.packages import get_package_share_directory
from usv_sim_full.launch_config_helpers import (
    default_radar_nav2_param_yaml,
    primary_robot_name,
    ship_config_blocks,
)
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, LogInfo, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    usv_sim_full_pkg = get_package_share_directory('usv_sim_full')

    main_launch_file = os.path.join(usv_sim_full_pkg, 'launch', 'main.launch.py')
    nav2_thruster_launch_file = os.path.join(usv_sim_full_pkg, 'launch', 'nav2_thruster_bringup.launch.py')

    launch_dir = os.path.dirname(os.path.abspath(__file__))
    default_nav2_params_file = default_radar_nav2_param_yaml(launch_dir)

    default_config_path = os.path.join(usv_sim_full_pkg, 'config', 'full_config.yaml')
    default_localization_params = os.path.join(usv_sim_full_pkg, 'config', 'robot_localization_gps.yaml')
    # 优先 install/share；若无（仅 colcon 未装 rviz 目录等），回退到与本 launch 同包的源码 rviz/
    _rviz_share = os.path.join(usv_sim_full_pkg, 'rviz', 'default.rviz')
    _rviz_src = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rviz', 'default.rviz')
    )
    default_rviz_config = _rviz_share if os.path.isfile(_rviz_share) else _rviz_src

    config_path = LaunchConfiguration('config_path')
    # 勿用通用名 `namespace`：main.launch 内含 gy_radar 的 IncludeLaunchDescription
    # 会对全局 launch 配置执行 SetLaunchConfiguration('namespace', robot_name)，
    # 多船时最后一艘（如 usv_2）会覆盖，导致此处误读到错误命名空间。
    nav2_namespace = LaunchConfiguration('nav2_namespace')
    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    nav2_start_delay = LaunchConfiguration('nav2_start_delay')
    auto_cleanup = LaunchConfiguration('auto_cleanup')
    cleanup_fastdds_shm = LaunchConfiguration('cleanup_fastdds_shm')
    enable_robot_localization = LaunchConfiguration('enable_robot_localization')
    localization_params_file = LaunchConfiguration('localization_params_file')
    use_static_map_odom_tf = LaunchConfiguration('use_static_map_odom_tf')

    def prelaunch_cleanup(context, *args, **kwargs):
        if auto_cleanup.perform(context).lower() != 'true':
            return []

        # Best-effort cleanup to avoid stale duplicate nodes from previous runs.
        kill_pattern = (
            'nav2_thruster_bringup.launch.py|'
            'navigation_launch.py|'
            'main.launch.py|'
            'gz sim|'
            'ros_gz_bridge/parameter_bridge|'
            'odom_tf_broadcaster|'
            'controller_server|planner_server|bt_navigator|behavior_server|'
            'waypoint_follower|velocity_smoother|smoother_server|'
            'lifecycle_manager_navigation|cmd_vel_to_thruster.py|'
            'ekf_node|navsat_transform_node|radar_gz_bridge|'
            'adaptive_radar_grid_map_node|usv_sim_wrapper|scenario_manager_node'
        )
        subprocess.run(
            ['bash', '-lc', f'pkill -9 -f "{kill_pattern}" || true; sleep 1'],
            check=False,
        )

        if cleanup_fastdds_shm.perform(context).lower() == 'true':
            subprocess.run(
                ['bash', '-lc', 'rm -rf /dev/shm/fastrtps* 2>/dev/null || true'],
                check=False,
            )

        return []

    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(main_launch_file),
        launch_arguments={
            'config_path': config_path,
            'enable_robot_localization': enable_robot_localization,
            'localization_params_file': localization_params_file,
            'use_static_map_odom_tf': use_static_map_odom_tf,
            # 使用包内 default.rviz 作为 RViz 底稿，不再打开 session_manager 生成的 session.rviz
            'rviz_config_path_override': default_rviz_config,
        }.items(),
    )

    def delayed_nav2_launch_with_resolved_ns(context, *args, **kwargs):
        requested_ns = nav2_namespace.perform(context).strip()
        resolved_ns = requested_ns
        cfg_path = config_path.perform(context)
        cfg = {}
        try:
            with open(cfg_path, 'r') as f:
                cfg = yaml.safe_load(f) or {}
        except Exception:
            pass

        if requested_ns in ('', 'auto'):
            resolved_ns = 'usv_1'
            try:
                resolved_ns = primary_robot_name(cfg)
            except Exception:
                resolved_ns = 'usv_1'

        known_names = []
        for block in ship_config_blocks(cfg):
            if isinstance(block, dict) and block.get('name'):
                known_names.append(str(block['name']).strip())

        prefix = []
        if known_names and resolved_ns not in known_names:
            prefix.append(
                LogInfo(
                    msg=(
                        '[WARN] nav2_namespace='
                        + resolved_ns
                        + ' 不在 full_config 的船名列表 '
                        + repr(known_names)
                        + ' 中；Nav2 TF/雷达话题可能与仿真不一致。'
                    )
                )
            )

        nav2_thruster_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav2_thruster_launch_file),
            launch_arguments={
                'namespace': resolved_ns,
                'params_file': params_file.perform(context),
                'use_sim_time': use_sim_time.perform(context),
            }.items(),
        )

        timer = TimerAction(
            period=float(nav2_start_delay.perform(context)),
            actions=[
                LogInfo(msg=[
                    'Starting Nav2 after delay: ',
                    nav2_start_delay.perform(context),
                    ' s (namespace=',
                    resolved_ns,
                    ')'
                ]),
                nav2_thruster_launch,
            ],
        )

        return [*prefix, timer]

    return LaunchDescription([
        DeclareLaunchArgument(
            'config_path',
            default_value=default_config_path,
            description='Path to usv_sim_full full_config.yaml'
        ),
        DeclareLaunchArgument(
            'nav2_namespace',
            default_value='auto',
            description=(
                'Nav2 与 cmd_vel→桨 所跟船的 ROS 命名空间，必须与 full_config 中该船 '
                'robot_*.name 完全一致（如 usv_1），以便 TF 帧 {name}/odom、{name}/base_link '
                '与 radar_nav2_param 中 __ROBOT_NS__ 替换一致。'
                'auto 或空：取 robot_1（按 slot 数字排序后的首船）。'
                '勿使用参数名 namespace，以免与 gy_radar IncludeLaunch 的全局 launch 键冲突。'
            ),
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=default_nav2_params_file,
            description='Nav2 parameters file path'
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation clock'
        ),
        DeclareLaunchArgument(
            'nav2_start_delay',
            default_value='10.0',
            description='Delay seconds before starting Nav2'
        ),
        DeclareLaunchArgument(
            'auto_cleanup',
            default_value='true',
            description='Kill stale sim/Nav2 related processes before launching'
        ),
        DeclareLaunchArgument(
            'cleanup_fastdds_shm',
            default_value='false',
            description='Additionally clean /dev/shm/fastrtps* before launching'
        ),
        DeclareLaunchArgument(
            'enable_robot_localization',
            default_value='false',
            description='Enable robot_localization in usv_sim_full main launch'
        ),
        DeclareLaunchArgument(
            'localization_params_file',
            default_value=default_localization_params,
            description='robot_localization parameter yaml path'
        ),
        DeclareLaunchArgument(
            'use_static_map_odom_tf',
            default_value='true',
            description='Publish static identity map->odom TF in main launch'
        ),
        LogInfo(msg=['Starting simulation bringup from: ', config_path]),
        OpaqueFunction(function=prelaunch_cleanup),
        sim_launch,
        OpaqueFunction(function=delayed_nav2_launch_with_resolved_ns),
    ])
