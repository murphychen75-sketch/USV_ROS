"""
******************************************************************************************
*  Copyright (C) 2026 MurphyChen, All Rights Reserved                                  *
*                                                                                        *
*  @brief    主启动文件 - 组装各个模块                                                 *
*  @author   MurphyChen                                                                *
*  @version  1.0.0                                                                       *
*  @date     2026.1.21                                                                 *
******************************************************************************************
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, SetEnvironmentVariable, OpaqueFunction, IncludeLaunchDescription, DeclareLaunchArgument, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node
import yaml
import subprocess
import json


def launch_setup(context, *args, **kwargs):
    # 获取包路径
    pkg_share = get_package_share_directory('usv_sim_full')
    
    # 获取用户配置路径 (通过LaunchConfiguration)
    config_path = LaunchConfiguration('config_path').perform(context)
    enable_robot_localization = LaunchConfiguration('enable_robot_localization').perform(context)
    localization_params_file = LaunchConfiguration('localization_params_file').perform(context)
    localization_start_delay = LaunchConfiguration('localization_start_delay').perform(context)
    use_static_map_odom_tf = LaunchConfiguration('use_static_map_odom_tf').perform(context)
    
    # 读取用户配置获取世界名称
    with open(config_path, 'r') as f:
        user_config = yaml.safe_load(f)
    
    world_name = user_config.get('environment', {}).get('world_name', 'sydney_regatta')
    
    # 检查是否启用RViz
    launch_rviz = user_config.get('visualization', {}).get('launch_rviz', True)

    # 从 full_config 现有 sensors 配置中判断是否启用导航雷达处理链路
    # 约定: 仅当 maritime_radar/radar 类型传感器 enabled=true 时启动 gy_radar_driver
    radar_processing_enabled = False
    radar_sensor_name = 'radar'
    radar_output_topic = '/sensors/radar/nav/sector'
    for sensor in user_config.get('sensors', []):
        sensor_type = str(sensor.get('type', '')).lower()
        if sensor_type in ('maritime_radar', 'radar') and sensor.get('enabled', True):
            radar_processing_enabled = True
            radar_sensor_name = str(sensor.get('name', 'radar'))
            if sensor.get('override_topic'):
                radar_output_topic = str(sensor.get('override_topic'))
            break

    # 执行会话管理器脚本，获取URDF、桥接配置、RViz配置和障碍物布局路径
    try:
        result = subprocess.run([
            'ros2',
            'run',
            'usv_sim_full',
            'session_manager',
            '--config-path', config_path
        ], capture_output=True, text=True, check=True)
        
        session_output = result.stdout.strip()
        print(f"Full session manager output: '{session_output}'")
        
        # 提取JSON部分 - 从 { 开始到最后
        lines = session_output.split('\n')
        json_line = None
        for line in lines:
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                json_line = line
                break
                
        if not json_line:
            raise ValueError(f"No JSON found in output: {session_output}")
        
        # 解析返回的JSON
        session_info = json.loads(json_line)
        urdf_path = session_info['urdf_path']
        bridge_yaml_path = session_info['bridge_yaml_path']
        rviz_config_path = session_info['rviz_config_path']
        obstacle_layout_path = session_info['obstacle_layout_path']
    except subprocess.CalledProcessError as e:
        print(f"Session manager failed with error: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise e
    except Exception as e:
        print(f"Error running session manager: {e}")
        raise e

    # 获取机器人配置
    robot_config = user_config.get('robot', {})
    robot_name = robot_config.get('name', 'usv')  # 默认使用'usv'作为机器人名
    spawn_pose = robot_config.get('spawn_pose', [0.0, 0.0, 0.5, 0.0, 0.0, 0.0])

    # gy_radar_driver 建图节点默认订阅全局话题，这里显式传入机器人命名空间话题。
    mapping_input_topic = radar_output_topic
    if not mapping_input_topic.startswith('/'):
        mapping_input_topic = '/' + mapping_input_topic
    if not mapping_input_topic.startswith(f'/{robot_name}/'):
        mapping_input_topic = f'/{robot_name}{mapping_input_topic}'
    converter_output_topic = f'/{robot_name}/sensors/radar/nav/points'
    mapping_output_gridmap_topic = f'/{robot_name}/map/navradar/gridmap'
    mapping_output_occupancy_topic = f'/{robot_name}/map/navradar/occupancy_grid'
    
    # 包含基础设施仿真
    infra_sim_include = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            get_package_share_directory('usv_sim_full'),
            '/launch/components/infra_sim.launch.py'
        ]),
        launch_arguments={
            'world_name': world_name
        }.items()
    )
    
    # 启动机器人系统（状态发布、实体创建、传感器桥接）
    robot_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            get_package_share_directory('usv_sim_full'),
            '/launch/components/robot_bringup.launch.py'
        ]),
        launch_arguments={
            'robot_name': robot_name,
            'urdf_path': urdf_path,
            'bridge_config_path': bridge_yaml_path,
            'obstacle_layout_path': obstacle_layout_path,
            'radar_sensor_name': radar_sensor_name,
            'radar_ros_topic': radar_output_topic,
            'enable_robot_localization': enable_robot_localization,
            'localization_params_file': localization_params_file,
            'localization_start_delay': localization_start_delay,
            'x': str(spawn_pose[0]),
            'y': str(spawn_pose[1]),
            'z': str(spawn_pose[2]),
            'R': str(spawn_pose[3]),
            'P': str(spawn_pose[4]),
            'Y': str(spawn_pose[5]),
            'use_sim_time': 'true'
        }.items()
    )
    
    # 启动可视化（RViz）
    viz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            get_package_share_directory('usv_sim_full'),
            '/launch/components/visualization.launch.py'
        ]),
        launch_arguments={
            'rviz_config_path': rviz_config_path
        }.items()
    )

    # 启动导航雷达解算和建图节点（按 full_config 传感器开关启用）
    radar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            get_package_share_directory('gy_radar_driver'),
            '/launch/radar_controller.launch.py'
        ]),
        launch_arguments={
            'namespace': robot_name,
            'enable_control': 'false',
            'enable_data': 'false',
            'enable_arpa': 'false',
            'enable_tf': 'false',
            'enable_mapping': 'true',
            'enable_converter': 'true',
            'mapping_input_topic': mapping_input_topic,
            'converter_input_topic': mapping_input_topic,
            'converter_output_topic': converter_output_topic,
            'mapping_output_gridmap_topic': mapping_output_gridmap_topic,
            'mapping_output_occupancy_topic': mapping_output_occupancy_topic,
            'use_sim_time': 'true'
        }.items()
    )
    

    import re
    sanitized_robot_name = re.sub(r"[^A-Za-z0-9_\-]", '_', str(robot_name))
    
    
    scenario_manager_node = Node(
        package="usv_sim_full",
        executable="scenario_manager_node",
        name="scenario_manager_node",
        output="screen",
        parameters=[{
            "config_path": config_path
        }]
    )

    wrapper_node = Node(
        package='usv_sim_full',
        executable='usv_sim_wrapper',
        name='usv_sim_wrapper',
        namespace=robot_name,
        output='screen',
        parameters=[{
            'odom_topic': f'/model/{sanitized_robot_name}/odometry',
            'gps_topic': f'/{sanitized_robot_name}/sensors/gps/gps_sensor/data'
        }],
        remappings=[
            ('/usv/state/vessel', f'/{sanitized_robot_name}/state/vessel'),
        ],
        
    )

    # 创建全局 map 坐标系，当前约定 map 与 odom 重合（零位姿静态变换）
    map_to_odom_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='map_to_odom_tf',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom'],
        condition=IfCondition(LaunchConfiguration('use_static_map_odom_tf')),
        output='screen'
    )
    
    # === 环境动力学节点 ===
    env_dynamics_node = Node(
        package='usv_sim_full',
        executable='usv_env_dynamics',
        name='usv_env_dynamics_node',
        output='screen',
        parameters=[{
            'model_name': robot_name, # 使用从配置读取的robot_name作为目标模型名
            'k_wind': 1.5,
            'k_current': 250.0
        }]
    )
    
    # 返回所有启动项
    launch_items = [
        infra_sim_include,
        map_to_odom_tf_node,
        robot_launch,
        wrapper_node,
        scenario_manager_node,
        env_dynamics_node
    ]

    if launch_rviz:
        launch_items.insert(2, viz_launch)

    if radar_processing_enabled:
        launch_items.append(radar_launch)

    return launch_items



def generate_launch_description():
    pkg_share = get_package_share_directory('usv_sim_full')
    default_config_path = os.path.join(pkg_share, 'config', 'full_config.yaml')
    default_localization_params = os.path.join(pkg_share, 'config', 'robot_localization_gps.yaml')
    
    return LaunchDescription([
        DeclareLaunchArgument(
            'config_path',
            default_value=default_config_path,
            description='Path to the full_config.yaml file'
        ),
        DeclareLaunchArgument(
            'enable_robot_localization',
            default_value='false',
            description='Enable robot_localization (EKF + navsat_transform) for dynamic map->odom'
        ),
        DeclareLaunchArgument(
            'localization_params_file',
            default_value=default_localization_params,
            description='Path to robot_localization parameter yaml'
        ),
        DeclareLaunchArgument(
            'localization_start_delay',
            default_value='5.0',
            description='Delay seconds before starting robot_localization nodes'
        ),
        DeclareLaunchArgument(
            'use_static_map_odom_tf',
            default_value='true',
            description='Publish static identity map->odom transform (disable when robot_localization is enabled)'
        ),
        OpaqueFunction(function=launch_setup)
    ])