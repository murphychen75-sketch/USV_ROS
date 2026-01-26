#!/usr/bin/env python3
"""
*****************************************************************************************
*  Copyright (C) 2026 MurphyChen, All Rights Reserved                                   *
*                                                                                       *
*  @brief    会话管理器，根据YAML配置生成传感器配置、桥接配置和机器人描述              *
*  @author   MurphyChen                                                               *
*  @version  1.0.0                                                                      *
*  @date     2026.1.14                                                                *
*****************************************************************************************
"""

import os
import yaml
import json
import shutil
from datetime import datetime
import subprocess
from ament_index_python.packages import get_package_share_directory
import math
import random


def create_session(config_path):
    """
    创建一个新的会话，包括日志目录和配置快照
    
    Args:
        config_path (str): 用户配置文件路径
        
    Returns:
        dict: 包含session_path、urdf_path、bridge_yaml_path和rviz_config_path的字典
    """
    # 获取当前时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 使用当前工作目录作为项目根目录
    project_root = os.getcwd()  # 获取当前工作目录（运行launch文件的目录）
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # 创建会话日志目录
    session_dir = os.path.join(logs_dir, f"session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)
    
    # 复制用户配置到会话目录
    source_config_path = os.path.join(session_dir, "source_config.yaml")
    shutil.copy2(config_path, source_config_path)
    
    # 读取配置文件
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # 生成传感器叠加层Xacro
    sensors_overlay_path = generate_sensors_overlay(config_data, session_dir)
    
    # 生成根Xacro文件
    root_xacro_path = generate_root_xacro(config_data, session_dir, sensors_overlay_path)
    
    # 生成参数化的Xacro文件（用于增强可追溯性）
    parametrized_xacro_path = generate_parametrized_xacro(config_data, session_dir, root_xacro_path, sensors_overlay_path)
    
    # 编译Xacro为URDF - 使用物理参数覆盖
    urdf_path = compile_xacro_to_urdf(parametrized_xacro_path, config_data, session_dir)
    
    # 生成桥接配置
    bridge_config = generate_bridge_config(config_data)
    
    # 保存桥接配置到会话目录
    bridge_yaml_path = os.path.join(session_dir, "bridge_config.yaml")
    with open(bridge_yaml_path, 'w') as f:
        yaml.dump(bridge_config, f)
    
    # 生成RViz配置
    rviz_config_path = generate_rviz_config(config_data, session_dir)
    
    # 生成障碍物布局
    obstacle_layout_path = generate_obstacles(config_data, session_dir)
    
    # 返回路径信息
    result = {
        "session_path": session_dir,
        "urdf_path": urdf_path,
        "bridge_yaml_path": bridge_yaml_path,
        "rviz_config_path": rviz_config_path,
        "obstacle_layout_path": obstacle_layout_path
    }
    
    return result


def generate_parametrized_xacro(config_data, session_dir, root_xacro_path, sensors_overlay_path):
    """
    生成参数化的Xacro文件，以增强可追溯性
    """
    # 获取要使用的xacro模板名称
    robot_config = config_data.get('robot', {})
    xacro_template = robot_config.get('xacro_template', 'wamv_gazebo.urdf.xacro')
    
    # 检查是否是本地模板（检查templates文件夹中是否存在该文件）
    local_template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'templates', 
        xacro_template
    )
    
    if os.path.exists(local_template_path):
        # 使用本地模板文件
        xacro_input = local_template_path
    else:
        # 检查本地模板不存在的情况
        if xacro_template.endswith(('.urdf.xacro', '.xacro')):
            # 如果是xacro类型的文件，说明用户可能期望使用本地模板
            if not os.path.exists(local_template_path):
                raise FileNotFoundError(f"Local template not found: '{local_template_path}'. "
                                      f"Please ensure the template file exists in the templates directory.")
        
        # 使用原始方式：通过ROS包查找
        package_name = robot_config.get('package_name', 'wamv_gazebo')
        xacro_relative_path = robot_config.get('xacro_relative_path', f'urdf/{xacro_template}')
        try:
            pkg_path = get_package_share_directory(package_name)
            xacro_input = os.path.join(pkg_path, xacro_relative_path)
        except Exception:
            xacro_input = f"/home/cczh/simulation/vrx_ws/install/{package_name}/share/{package_name}/{xacro_relative_path}"
            
        # 检查ROS包中的模板是否存在
        if not os.path.exists(xacro_input):
            raise FileNotFoundError(f"Template not found: neither local template at '{local_template_path}' nor package template at '{xacro_input}' exists.")

    # 读取原始Xacro文件内容
    with open(xacro_input, 'r') as f:
        xacro_content = f.read()

    # 从配置中提取参数并替换到Xacro内容中
    overrides = robot_config.get('overrides', {})
    
    # 替换物理参数
    for key, value in overrides.items():
        if key == 'inertia' and isinstance(value, list):
            # 替换惯性矩阵参数
            xacro_content = xacro_content.replace('$(arg ixx)', str(value[0]))
            xacro_content = xacro_content.replace('$(arg iyy)', str(value[1]))
            xacro_content = xacro_content.replace('$(arg izz)', str(value[2]))
        elif isinstance(value, (int, float)):
            # 替换数值参数
            xacro_content = xacro_content.replace(f'$(arg {key})', str(value))
        elif isinstance(value, str) and key != 'visual_mesh':  # 不替换visual_mesh，因为我们已经在顶部添加了
            # 替换字符串参数
            xacro_content = xacro_content.replace(f'$(arg {key})', str(value))

    # 特别处理visual_mesh参数 - 需要替换模板中的默认值
    if 'visual_mesh' in overrides:
        # 直接替换掉默认的visual_mesh参数值
        old_visual_mesh_def = 'default="package://wamv_description/models/WAM-V-Base/mesh/WAM-V-Base.dae"'
        new_visual_mesh_def = f'default="{overrides["visual_mesh"]}"'
        xacro_content = xacro_content.replace(old_visual_mesh_def, new_visual_mesh_def)

    # 替换浮力和水动力参数
    buoyancy_params = robot_config.get('buoyancy_params', {})
    for key, value in buoyancy_params.items():
        if isinstance(value, (int, float)):
            xacro_content = xacro_content.replace(f'$(arg {key})', str(value))
        elif isinstance(value, str):
            xacro_content = xacro_content.replace(f'$(arg {key})', str(value))

    # 替换推进器配置
    thruster_config = robot_config.get('thruster_config', 'H')
    xacro_content = xacro_content.replace('$(arg thruster_config)', str(thruster_config))

    # 替换传感器相关参数
    sensors_config = config_data.get('sensors', {})
    has_sensors = len(sensors_config.get('lidars', [])) > 0 or \
                  len(sensors_config.get('cameras', [])) > 0 or \
                  len(sensors_config.get('imus', [])) > 0 or \
                  len(sensors_config.get('gps_sensors', [])) > 0
                  
    xacro_content = xacro_content.replace('$(arg has_sensors)', str(has_sensors).lower())

    # 如果有传感器，替换extra_sensors参数
    if has_sensors and sensors_overlay_path and os.path.exists(sensors_overlay_path):
        # 读取传感器文件内容并插入到适当位置
        with open(sensors_overlay_path, 'r') as sensor_f:
            sensor_content = sensor_f.read()
        
        # 查找并替换extra_sensors引用部分
        # 这里使用更灵活的替换方法，因为传感器部分可能有不同的结构
        placeholder = 'filename="$(arg extra_sensors)"'
        if placeholder in xacro_content:
            # 将传感器内容直接嵌入到Xacro中
            xacro_content = xacro_content.replace(
                f'<xacro:include {placeholder} />',
                sensor_content
            )
        else:
            # 如果找不到placeholder，尝试在适当位置插入传感器内容
            # 通常在文件末尾，在结束标签之前插入
            closing_tag_idx = xacro_content.rfind('</robot>')
            if closing_tag_idx != -1:
                xacro_content = xacro_content[:closing_tag_idx] + sensor_content + xacro_content[closing_tag_idx:]

    # 保存参数化的Xacro文件
    parametrized_xacro_path = os.path.join(session_dir, "parametrized_robot.urdf.xacro")
    with open(parametrized_xacro_path, 'w') as f:
        f.write(xacro_content)
    
    print(f"Generated parametrized Xacro at: {parametrized_xacro_path}")
    return parametrized_xacro_path


def replace_visual_mesh_in_xacro(xacro_content, visual_mesh_path):
    """
    替换XACRO内容中的视觉网格文件路径
    """
    import re
    
    # 替换基础链接(base_link)中的视觉模型
    # 匹配 <visual>...</visual> 部分，特别是其中的 <mesh filename="..."> 部分
    visual_pattern = r'(<visual[^>]*>)(.*?)(</visual>)'
    
    def replace_mesh_in_visual(match):
        full_match = match.group(0)
        visual_start = match.group(1)
        visual_content = match.group(2)
        visual_end = match.group(3)
        
        # 检查是否是base_link的visual部分
        if 'base_link' in xacro_content.split('<link')[0] + full_match or '<link name=".*?base_link' in xacro_content:
            # 替换mesh文件路径
            mesh_pattern = r'<mesh\s+filename="[^"]*"[^>]*/?>'
            new_visual_content = re.sub(mesh_pattern, f'<mesh filename="{visual_mesh_path}" />', visual_content)
            return visual_start + new_visual_content + visual_end
        else:
            return full_match
            
    # 首先尝试更精确的匹配，查找base_link中的mesh部分
    # 更简单的方式：直接查找mesh标签并替换
    mesh_pattern = r'<mesh\s+filename="package://[^"]*/mesh/[^"]*\.dae"[^>]*/?>'
    xacro_content = re.sub(mesh_pattern, f'<mesh filename="{visual_mesh_path}" />', xacro_content)
    
    return xacro_content


def generate_sensors_overlay(config_data, session_dir):
    """
    根据传感器配置生成传感器叠加层Xacro文件
    
    Args:
        config_data (dict): 配置数据
        session_dir (str): 会话目录
        
    Returns:
        str: 生成的传感器叠加层Xacro文件路径
    """
    sensors_overlay_path = os.path.join(session_dir, "generated_sensors.xacro")
    
    # 读取模板文件
    template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 "templates", "sensor_macros.xacro")
    
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # 只提取宏定义部分，不包括xml和robot标签
    lines = template_content.split('\n')
    inside_macro = False
    current_macro = []
    macros_content = []  # 添加缺失的变量定义
    
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith('<xacro:macro'):
            inside_macro = True
            current_macro = [line]
        elif inside_macro:
            current_macro.append(line)
            if stripped_line == '</xacro:macro>':
                # 结束宏定义
                macros_content.extend(current_macro)
                inside_macro = False
    
    # 生成传感器链接 - 注意不要重复XML声明
    sensors_content = '<robot xmlns:xacro="http://www.ros.org/wiki/xacro">\n'
    
    # 添加提取的宏定义
    for line in macros_content:
        sensors_content += line + '\n'
    
    sensors_content += "\n"
    
    # 添加传感器链接
    sensors_config = config_data.get('sensors', {})
    
    # 处理激光雷达
    lidars = sensors_config.get('lidars', [])
    for lidar in lidars:
        if not lidar.get('enabled', True):
            continue
            
        sensor_name = lidar['name']
        parent_link = lidar['parent_link']
        xyz = ' '.join(map(str, lidar['xyz']))
        rpy = ' '.join(map(str, lidar['rpy']))
        topic = lidar.get('topic', f'/sensors/lidar/{sensor_name}/points')
        
        sensors_content += f'''
  <xacro:vlp16_macro name="{sensor_name}" parent_link="wamv/{parent_link}" xyz="{xyz}" rpy="{rpy}" topic="{topic}"/>
'''

    # 处理摄像头
    cameras = sensors_config.get('cameras', [])
    for cam in cameras:
        if not cam.get('enabled', True):
            continue
            
        sensor_name = cam['name']
        parent_link = cam['parent_link']
        xyz = ' '.join(map(str, cam['xyz']))
        rpy = ' '.join(map(str, cam['rpy']))
        topic = cam.get('topic', f'/sensors/camera/{sensor_name}/image_raw')
        info_topic = cam.get('info_topic', f'/sensors/camera/{sensor_name}/camera_info')
        
        sensors_content += f'''
  <xacro:camera_macro name="{sensor_name}" parent_link="wamv/{parent_link}" xyz="{xyz}" rpy="{rpy}" topic="{topic}" info_topic="{info_topic}"/>
'''

    # 处理IMU
    imus = sensors_config.get('imus', [])
    for imu in imus:
        if not imu.get('enabled', True):
            continue
            
        sensor_name = imu['name']
        parent_link = imu['parent_link']
        xyz = ' '.join(map(str, imu['xyz']))
        rpy = ' '.join(map(str, imu['rpy']))
        topic = imu.get('topic', '/sensors/imu/data')
        update_rate = imu.get('update_rate', 100)
        
        sensors_content += f'''
  <xacro:imu_macro name="{sensor_name}" parent_link="wamv/{parent_link}" xyz="{xyz}" rpy="{rpy}" topic="{topic}" update_rate="{update_rate}"/>
'''

    # 处理GPS
    gps_sensors = sensors_config.get('gps_sensors', [])
    for gps in gps_sensors:
        if not gps.get('enabled', True):
            continue
            
        sensor_name = gps['name']
        parent_link = gps['parent_link']
        xyz = ' '.join(map(str, gps['xyz']))
        rpy = ' '.join(map(str, gps['rpy']))
        topic = gps.get('topic', '/sensors/gps/data')
        update_rate = gps.get('update_rate', 20)
        
        sensors_content += f'''
  <xacro:gps_macro name="{sensor_name}" parent_link="wamv/{parent_link}" xyz="{xyz}" rpy="{rpy}" topic="{topic}" update_rate="{update_rate}"/>
'''

    sensors_content += '</robot>\n'
    
    # 写入传感器叠加层文件
    with open(sensors_overlay_path, 'w') as f:
        f.write(sensors_content)
    
    return sensors_overlay_path


def generate_root_xacro(config_data, session_dir, sensors_overlay_path):
    """
    不再生成独立的root xacro，仅返回基础模板路径和参数信息。
    现在由 compile_xacro_to_urdf 直接处理模板选择。
    """
    return None  # 后续由 compile_xacro_to_urdf 处理


def compile_xacro_to_urdf(parametrized_xacro_path, config_data, session_dir):
    """
    使用 ros2 run xacro xacro 编译最终URDF，现在接收参数化的Xacro文件路径
    
    Args:
        parametrized_xacro_path (str): 参数化的Xacro文件路径
        config_data (dict): 配置数据
        session_dir (str): 会话目录
        
    Returns:
        str: 生成的URDF文件路径
    """
    urdf_path = os.path.join(session_dir, "final_robot.urdf")

    # 从配置中获取overrides参数
    robot_config = config_data.get('robot', {})
    overrides = robot_config.get('overrides', {})
    
    # 构建xacro命令 - 添加参数
    cmd = [
        'ros2', 'run', 'xacro', 'xacro',
        parametrized_xacro_path,
        '-o', urdf_path
    ]
    
    # 添加overrides参数到命令
    for key, value in overrides.items():
        if key == 'inertia' and isinstance(value, list):
            # 特殊处理惯性参数
            cmd.append(f"ixx:={value[0]}")
            cmd.append(f"iyy:={value[1]}")
            cmd.append(f"izz:={value[2]}")
        elif isinstance(value, (str, int, float)):
            # 统一处理字符串、整数和浮点数参数
            cmd.append(f"{key}:={value}")
            
    # 特别处理visual_mesh参数（如果存在）
    if 'visual_mesh' in overrides:
        cmd.append(f"visual_mesh:={overrides['visual_mesh']}")

    # 执行命令
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to compile Xacro to URDF:\nCommand: {' '.join(cmd)}\nError: {result.stderr}")

    print(f"Generated URDF at: {urdf_path}")
    return urdf_path


def generate_bridge_config(config_data):
    """
    根据传感器配置生成桥接配置
    
    Args:
        config_data (dict): 配置数据
        
    Returns:
        list: 桥接配置（YAML序列格式）
    """
    # 桥接配置必须是列表格式
    bridges = [
        {
            "ros_topic_name": "/clock",
            "gz_topic_name": "/clock",
            "ros_type_name": "rosgraph_msgs/msg/Clock",
            "gz_type_name": "gz.msgs.Clock",
            "direction": "GZ_TO_ROS"
        }
    ]
    
    # 添加遥测配置
    if config_data.get('visualization', {}).get('enable_telemetry', True):
        # 添加里程计桥接
        bridges.append({
            "ros_topic_name": "/model/wamv/odometry",
            "gz_topic_name": "/model/wamv/odometry",
            "ros_type_name": "nav_msgs/msg/Odometry",
            "gz_type_name": "gz.msgs.Odometry",
            "direction": "GZ_TO_ROS"
        })
        
        # 添加关节状态桥接
        bridges.append({
            "ros_topic_name": "/model/wamv/joint_state",
            "gz_topic_name": "/model/wamv/joint_state",
            "ros_type_name": "sensor_msgs/msg/JointState",
            "gz_type_name": "gz.msgs.Model",
            "direction": "GZ_TO_ROS"
        })
        
        # 添加位姿桥接（用于TF）
        bridges.append({
            "ros_topic_name": "/model/wamv/pose",
            "gz_topic_name": "/model/wamv/pose",
            "ros_type_name": "tf2_msgs/msg/TFMessage",
            "gz_type_name": "gz.msgs.Pose_V",
            "direction": "GZ_TO_ROS"
        })

    # 遍历传感器配置，生成桥接配置
    sensors_config = config_data.get('sensors', {})
    
    # 处理激光雷达
    lidars = sensors_config.get('lidars', [])
    for lidar in lidars:
        if not lidar.get('enabled', True):
            continue
            
        topic = lidar.get('topic', f'/sensors/lidar/{lidar["name"]}/points')
        gz_topic = topic.replace('/sensors/', '/world/sydney_regatta/model/wamv/sensor/')
        bridges.append({
            "ros_topic_name": topic,
            "gz_topic_name": gz_topic,
            "ros_type_name": "sensor_msgs/msg/PointCloud2",
            "gz_type_name": "gz.msgs.PointCloudPacked",
            "direction": "GZ_TO_ROS"
        })
    
    # 处理摄像头
    cameras = sensors_config.get('cameras', [])
    for cam in cameras:
        if not cam.get('enabled', True):
            continue
            
        topic = cam.get('topic', f'/sensors/camera/{cam["name"]}/image_raw')
        info_topic = cam.get('info_topic', f'/sensors/camera/{cam["name"]}/camera_info')
        
        # 图像数据
        bridges.append({
            "ros_topic_name": topic,
            "gz_topic_name": topic.replace('/sensors/', '/world/sydney_regatta/model/wamv/sensor/'),
            "ros_type_name": "sensor_msgs/msg/Image",
            "gz_type_name": "gz.msgs.Image",
            "direction": "GZ_TO_ROS"
        })
        
        # 相机信息
        bridges.append({
            "ros_topic_name": info_topic,
            "gz_topic_name": info_topic.replace('/sensors/', '/world/sydney_regatta/model/wamv/sensor/'),
            "ros_type_name": "sensor_msgs/msg/CameraInfo",
            "gz_type_name": "gz.msgs.CameraInfo",
            "direction": "GZ_TO_ROS"
        })
    
    # 处理IMU
    imus = sensors_config.get('imus', [])
    for imu in imus:
        if not imu.get('enabled', True):
            continue
            
        topic = imu.get('topic', '/sensors/imu/data')
        bridges.append({
            "ros_topic_name": topic,
            "gz_topic_name": topic.replace('/sensors/', '/world/sydney_regatta/model/wamv/sensor/'),
            "ros_type_name": "sensor_msgs/msg/Imu",
            "gz_type_name": "gz.msgs.IMU",
            "direction": "GZ_TO_ROS"
        })
    
    # 处理GPS
    gps_sensors = sensors_config.get('gps_sensors', [])
    for gps in gps_sensors:
        if not gps.get('enabled', True):
            continue
            
        topic = gps.get('topic', '/sensors/gps/data')
        bridges.append({
            "ros_topic_name": topic,
            "gz_topic_name": topic.replace('/sensors/', '/world/sydney_regatta/model/wamv/sensor/'),
            "ros_type_name": "sensor_msgs/msg/NavSatFix",
            "gz_type_name": "gz.msgs.NavSat",
            "direction": "GZ_TO_ROS"
        })
    
    return bridges


def generate_rviz_config(config_data, session_dir):
    """
    根据传感器配置生成RViz配置
    
    Args:
        config_data (dict): 配置数据
        session_dir (str): 会话目录
        
    Returns:
        str: 生成的RViz配置文件路径
    """
    # 读取RViz模板
    template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 "templates", "default.rviz")
    
    with open(template_path, 'r') as f:
        rviz_config = yaml.safe_load(f)
    
    # 获取Display列表
    displays = rviz_config['Visualization Manager']['Displays']
    
    # 添加传感器显示项
    sensors_config = config_data.get('sensors', {})
    
    # 处理激光雷达
    lidars = sensors_config.get('lidars', [])
    for lidar in lidars:
        if not lidar.get('enabled', True):
            continue
            
        topic = lidar['topic']
        display_config = {
            'Class': 'rviz_default_plugins/PointCloud2',
            'Name': f"Lidar: {lidar['name']}",
            'Enabled': True,
            'Topic': {
                'Value': topic,
                'Depth': 5,
                'Durability Policy': 'Volatile',
                'History Policy': 'Keep Last',
                'Reliability Policy': 'Best Effort'  # Changed to Best Effort for point clouds
            },
            'Position Transformer': 'XYZ',
            'Shape': {'Value': 'Points'},
            'Size (m)': 0.009999999776482582,
            'Style': 'Points'
        }
        displays.append(display_config)
    
    # 处理摄像头
    cameras = sensors_config.get('cameras', [])
    for cam in cameras:
        if not cam.get('enabled', True):
            continue
            
        topic = cam['topic']
        display_config = {
            'Class': 'rviz_default_plugins/Image',
            'Name': f"Camera: {cam['name']}",
            'Enabled': True,
            'Topic': {
                'Value': topic,
                'Depth': 5,
                'Durability Policy': 'Volatile',
                'History Policy': 'Keep Last',
                'Reliability Policy': 'Best Effort'  # Changed to Best Effort for images
            }
        }
        displays.append(display_config)
    
    # 处理IMU
    imus = sensors_config.get('imus', [])
    for imu in imus:
        if not imu.get('enabled', True):
            continue
            
        topic = imu['topic']
        display_config = {
            'Class': 'rviz_default_plugins/Imu',
            'Name': f"IMU: {imu['name']}",
            'Enabled': True,
            'Topic': {
                'Value': topic,
                'Depth': 5,
                'Durability Policy': 'Volatile',
                'History Policy': 'Keep Last',
                'Reliability Policy': 'Best Effort'
            },
            'Box Color': '255; 0; 0',
            'Box Size': 0.30000001192092896,
            'Queue Size': 10,
            'Style': 'Axes'
        }
        displays.append(display_config)
    
    # 处理GPS
    gps_sensors = sensors_config.get('gps_sensors', [])
    for gps in gps_sensors:
        if not gps.get('enabled', True):
            continue
            
        # GPS数据显示配置
        display_config = {
            'Class': 'rviz_default_plugins/Axes',
            'Name': f"GPS: {gps['name']}",
            'Enabled': True,
            'Shaft Length': 1.0,
            'Head Radius': 0.5,
            'Head Length': 0.5,
            'Shaft Radius': 0.25
        }
        displays.append(display_config)
    
    # 保存RViz配置到会话目录
    rviz_config_path = os.path.join(session_dir, "session.rviz")
    with open(rviz_config_path, 'w') as f:
        yaml.dump(rviz_config, f, default_flow_style=False, indent=2)
    
    return rviz_config_path


def generate_obstacles(config_data, session_dir):
    """
    根据配置生成障碍物布局
    
    Args:
        config_data (dict): 配置数据
        session_dir (str): 会话目录
        
    Returns:
        str: 生成的障碍物布局文件路径
    """
    obstacles_config = config_data.get('obstacles', {})
    random_areas = obstacles_config.get('random_areas', [])
    fixed_list = obstacles_config.get('fixed_list', [])
    
    all_obstacles = []
    
    # 处理固定障碍物
    for obs in fixed_list:
        all_obstacles.append({
            'name': obs['name'],
            'type': obs['type'],
            'pose': obs['pose'],  # [x, y, z, roll, pitch, yaw]
            'size': obs['size'],
            'color': obs['color']
        })
    
    # 处理随机区域
    for area in random_areas:
        center_x, center_y = area['center'][0], area['center'][1]
        radius = area['radius']
        count = area['count']
        obs_type = area['type']
        size_range = area['size_range']
        color = area['color']
        
        for i in range(count):
            # 使用极坐标随机生成算法确保均匀分布
            r = radius * math.sqrt(random.random())
            theta = random.random() * 2 * math.pi
            x = center_x + r * math.cos(theta)
            y = center_y + r * math.sin(theta)
            
            # 避免生成在原点附近（保护区，防止生成在船身上）
            if abs(x) < 2.0 and abs(y) < 2.0:
                # 如果生成在保护区内，重新生成
                continue_attempts = 0
                while abs(x) < 2.0 and abs(y) < 2.0 and continue_attempts < 10:
                    r = radius * math.sqrt(random.random())
                    theta = random.random() * 2 * math.pi
                    x = center_x + r * math.cos(theta)
                    y = center_y + r * math.sin(theta)
                    continue_attempts += 1
                    
            # 如果还是在保护区内，跳过这次生成
            if abs(x) < 2.0 and abs(y) < 2.0:
                continue
            
            # 随机选择大小
            size_val = random.uniform(size_range[0], size_range[1])
            height = random.uniform(size_range[0]*2, size_range[1]*2)  # 高度稍大一点
            
            obstacle = {
                'name': f"{area['name']}_{obs_type}_{i}",
                'type': obs_type,
                'pose': [x, y, 0.0, 0.0, 0.0, 0.0],  # z设为0保证在水面上
                'size': [size_val, height],
                'color': color
            }
            all_obstacles.append(obstacle)
    
    # 保存障碍物布局到会话目录
    obstacle_layout_path = os.path.join(session_dir, "obstacle_layout.json")
    with open(obstacle_layout_path, 'w') as f:
        json.dump(all_obstacles, f, indent=2)
    
    return obstacle_layout_path


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Session Manager for USV Simulation')
    parser.add_argument('--config-path', type=str, required=True, help='Path to user config file')
    
    args = parser.parse_args()
    
    result = create_session(args.config_path)
    
    # 输出JSON格式的结果，供launch文件读取
    print(json.dumps(result))


if __name__ == "__main__":
    main()