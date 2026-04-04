#!/usr/bin/env python3
"""
******************************************************************************************
*  Copyright (C) 2026 MurphyChen, All Rights Reserved                                  *
*                                                                                        *
*  @brief    障碍物生成器 - 从JSON布局文件加载并创建Gazebo障碍物                        *
*  @author   MurphyChen                                                                *
*  @version  1.0.0                                                                       *
*  @date     2026.1.21                                                                 *
******************************************************************************************
"""

import sys
import json
import subprocess
import math
import argparse


def spawn_obstacle(name, model_type, pose, size, color):
    """生成SDF字符串并使用create服务创建障碍物"""
    
    # 简单的颜色映射
    color_map = {
        "Red": "1 0 0 1",
        "Green": "0 1 0 1",
        "Blue": "0 0 1 1",
        "Yellow": "1 1 0 1",
        "Black": "0 0 0 1",
        "White": "1 1 1 1"
    }
    rgba = color_map.get(color, "1 0 0 1")

    # 根据类型创建SDF
    if model_type == "cylinder":
        radius, height = size
        sdf_xml = f"""<?xml version="1.0"?>
<sdf version="1.7">
  <model name="{name}">
    <pose>{pose[0]} {pose[1]} {pose[2]} 0 0 0</pose>
    <link name="link">
      <visual name="visual">
        <geometry>
          <cylinder>
            <radius>{radius}</radius>
            <length>{height}</length>
          </cylinder>
        </geometry>
        <material>
          <ambient>{rgba}</ambient>
          <diffuse>{rgba}</diffuse>
        </material>
      </visual>
      <collision name="collision">
        <geometry>
          <cylinder>
            <radius>{radius}</radius>
            <length>{height}</length>
          </cylinder>
        </geometry>
      </collision>
      <inertial>
        <mass>1.0</mass>
        <inertia>
          <ixx>0.1</ixx>
          <iyy>0.1</iyy>
          <izz>0.1</izz>
        </inertia>
      </inertial>
    </link>
    <static>true</static>
  </model>
</sdf>"""
    elif model_type == "box":
        width, height, depth = size
        sdf_xml = f"""<?xml version="1.0"?>
<sdf version="1.7">
  <model name="{name}">
    <pose>{pose[0]} {pose[1]} {pose[2]} 0 0 0</pose>
    <link name="link">
      <visual name="visual">
        <geometry>
          <box>
            <size>{width} {height} {depth}</size>
          </box>
        </geometry>
        <material>
          <ambient>{rgba}</ambient>
          <diffuse>{rgba}</diffuse>
        </material>
      </visual>
      <collision name="collision">
        <geometry>
          <box>
            <size>{width} {height} {depth}</size>
          </box>
        </geometry>
      </collision>
      <inertial>
        <mass>1.0</mass>
        <inertia>
          <ixx>0.1</ixx>
          <iyy>0.1</iyy>
          <izz>0.1</izz>
        </inertia>
      </inertial>
    </link>
    <static>true</static>
  </model>
</sdf>"""
    else:
        print(f"Unsupported model type: {model_type}")
        return False

    try:
        # 使用create服务创建障碍物，同时在命令行参数中显式指定位置，防止依赖SDF内部<pose>失效
        result = subprocess.run([
            'ros2', 'run', 'ros_gz_sim', 'create',
            '-string', sdf_xml,
            '-name', name,
            '-x', str(pose[0]),
            '-y', str(pose[1]),
            '-z', str(pose[2])
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Failed to spawn obstacle {name}: {result.stderr}")
            return False
        else:
            print(f"Successfully spawned obstacle {name}")
            return True
    except Exception as e:
        print(f"Failed to spawn obstacle {name}: {str(e)}")
        return False
def main():
    if len(sys.argv) < 2:
        print("Usage: ros2 run usv_sim_full obstacle_spawner.py <obstacle_layout.json>")
        return

    layout_file_path = sys.argv[1]
    
    try:
        with open(layout_file_path, 'r') as f:
            obstacles_data = json.load(f)
    except FileNotFoundError:
        print(f"Layout file not found: {layout_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Invalid JSON in layout file: {layout_file_path}")
        return

    # 遍历所有障碍物并创建
    for idx, obstacle in enumerate(obstacles_data):
        name = obstacle.get('name', f'obstacle_{idx}')
        model_type = obstacle.get('type', 'cylinder')
        pose = obstacle.get('pose', [0, 0, 0])
        size = obstacle.get('size', [0.5, 1.0] if model_type == 'cylinder' else [1.0, 1.0, 1.0])
        color = obstacle.get('color', 'Red')
        
        success = spawn_obstacle(name, model_type, pose, size, color)
        if not success:
            print(f"Failed to spawn obstacle: {name}")
        
        # 等待一小段时间，避免同时创建冲突
        import time
        time.sleep(0.1)


if __name__ == '__main__':
    main()