import os
import tempfile
import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, LogInfo, GroupAction, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import PushRosNamespace, Node
from ament_index_python.packages import get_package_share_directory
from usv_sim_full.launch_config_helpers import default_radar_nav2_param_yaml


def _nav2_params_subst_robot_ns(obj, ns: str):
    """将 radar_nav2_param.yaml 中的 __ROBOT_NS__ 替换为实际船名（无首尾 /）。"""
    if isinstance(obj, dict):
        return {k: _nav2_params_subst_robot_ns(v, ns) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_nav2_params_subst_robot_ns(x, ns) for x in obj]
    if isinstance(obj, str):
        return obj.replace('__ROBOT_NS__', ns)
    return obj


def generate_launch_description():
    # 获取 nav2_bringup 引擎的启动文件路径
    nav2_bringup_pkg = get_package_share_directory('nav2_bringup')
    nav2_launch_file = os.path.join(nav2_bringup_pkg, 'launch', 'navigation_launch.py')

    launch_dir = os.path.dirname(os.path.abspath(__file__))
    default_nav2_params_file = default_radar_nav2_param_yaml(launch_dir)

    namespace = LaunchConfiguration('namespace')
    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')

    # 0. 将全局 /tf 转发到 /<namespace>/tf，确保命名空间化 Nav2 可以接收 TF。
    tf_relay_node = Node(
        package='usv_sim_full',
        executable='tf_namespace_relay',
        name='tf_namespace_relay',
        namespace=namespace,
        parameters=[{
            'namespace': namespace,
            'use_sim_time': use_sim_time,
        }],
        output='screen'
    )

    def _launch_nav2_with_namespaced_map(context, *args, **kwargs):
        raw_ns = namespace.perform(context).strip().strip('/')
        resolved_params_file = params_file.perform(context)
        resolved_use_sim_time = use_sim_time.perform(context)

        prefix_logs = []
        if not raw_ns:
            resolved_ns = 'usv_1'
            prefix_logs.append(
                LogInfo(
                    msg=(
                        '[WARN] Nav2 namespace 为空，参数与 map_topic 回退为 usv_1；'
                        '请显式传入 namespace:=<船名> 与 full_config 中 robot_*.name 一致。'
                    )
                )
            )
        else:
            resolved_ns = raw_ns

        map_topic = f'/{resolved_ns}/map/navradar/occupancy_grid'

        with open(resolved_params_file, 'r') as f:
            nav2_params = yaml.safe_load(f) or {}

        nav2_params = _nav2_params_subst_robot_ns(nav2_params, resolved_ns)

        try:
            nav2_params['global_costmap']['global_costmap']['ros__parameters']['static_layer']['map_topic'] = map_topic
            nav2_params['local_costmap']['local_costmap']['ros__parameters']['static_layer']['map_topic'] = map_topic
        except KeyError:
            pass

        gcp = nav2_params.get('global_costmap', {}).get('global_costmap', {}).get('ros__parameters', {})
        lcp = nav2_params.get('local_costmap', {}).get('local_costmap', {}).get('ros__parameters', {})
        robot_bf = str(gcp.get('robot_base_frame', '?'))
        local_gf = str(lcp.get('global_frame', '?'))

        tmp_file = tempfile.NamedTemporaryFile(
            mode='w',
            prefix=f'nav2_{resolved_ns}_',
            suffix='.yaml',
            delete=False,
        )
        with tmp_file:
            yaml.safe_dump(nav2_params, tmp_file, sort_keys=False)

        info = LogInfo(
            msg=(
                'Nav2 参数已按船名注入: namespace='
                + resolved_ns
                + ' robot_base_frame='
                + robot_bf
                + ' local_costmap.global_frame='
                + local_gf
                + ' static_layer.map_topic='
                + map_topic
            )
        )

        stack = GroupAction([
            PushRosNamespace(namespace=namespace),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(nav2_launch_file),
                launch_arguments={
                    'namespace': namespace,
                    'params_file': tmp_file.name,
                    'use_sim_time': resolved_use_sim_time,
                }.items()
            )
        ])

        return [*prefix_logs, info, stack]

    # 2. 启动手写的 "cmd_vel 转底层双桨" 桥接脚本
    thruster_bridge_node = ExecuteProcess(
        cmd=[
            'ros2',
            'run',
            'usv_sim_full',
            'cmd_vel_to_thruster',
            '--ros-args',
            '-r',
            ['__ns:=/', namespace],
            '-p',
            ['namespace:=', namespace],
        ],
        name='cmd_vel_to_thruster',
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'namespace',
            default_value='usv_1',
            description=(
                '本船 ROS 命名空间，须与 full_config 中该船 name 及 TF 前缀一致 '
                '（与 nav2_sim_full_bringup 的 nav2_namespace 解析结果相同）。'
            ),
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=default_nav2_params_file,
            description='Nav2 parameters file path for this vessel instance'
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation clock'
        ),
        tf_relay_node,
        LogInfo(msg=['Starting Nav2 navigation stack for ', namespace, '...']),
        OpaqueFunction(function=_launch_nav2_with_namespaced_map),
        LogInfo(msg=['Starting cmd_vel to thruster bridge for ', namespace, '...']),
        thruster_bridge_node
    ])
