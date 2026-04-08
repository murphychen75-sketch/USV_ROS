#!/usr/bin/env python3

import math
import os
import subprocess
import tempfile
import time
import yaml

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from ros_gz_interfaces.srv import SpawnEntity

class DynamicObstacle:
    def __init__(self, config, node):
        self.requested_name = str(config.get('name', 'obstacle'))
        # Use a stable, searchable runtime name in Gazebo Entity Tree.
        self.name = self.requested_name if self.requested_name.startswith('dyn_') else f'dyn_{self.requested_name}'
        self.shape = config.get('shape', 'cylinder')
        self.color = config.get('color', 'Red')
        self.speed = config.get('speed', 1.0)
        self.loop = config.get('loop', True)
        self.waypoints = config.get('waypoints', [])
        
        self.current_wp_idx = 1 if len(self.waypoints) > 1 else 0
        self.direction = 1 # 1 for forward, -1 for backward
        if len(self.waypoints) > 0:
            self.x = float(self.waypoints[0][0])
            self.y = float(self.waypoints[0][1])
        else:
            self.x = 0.0
            self.y = 0.0
            
        self.active = len(self.waypoints) > 1
        
        # ROS 2 Publisher
        self.cmd_vel_pub = node.create_publisher(Twist, f'/model/{self.name}/cmd_vel', 10)
        
        # Start bridge for this obstacle's cmd_vel
        # ros_gz_bridge parameter_bridge /model/{name}/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist
        cmd = [
            'ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
            f'/model/{self.name}/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist'
        ]
        self.bridge_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def cleanup(self):
        if hasattr(self, 'bridge_process') and self.bridge_process:
            self.bridge_process.terminate()

class ScenarioManager(Node):
    def __init__(self):
        super().__init__('scenario_manager')
        
        self.declare_parameter('config_path', '')
        config_path = self.get_parameter('config_path').get_parameter_value().string_value
        
        if not config_path or not os.path.exists(config_path):
            self.get_logger().error(f"Config file not found: {config_path}")
            return
            
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        self.world_name = self.config.get('environment', {}).get('world_name', 'sydney_regatta')
        scenario_cfg = self.config.get('scenario', {})
        self.obs_configs = scenario_cfg.get('dynamic_obstacles', [])
        
        self.obstacles = []
        
        # 等待 /world/<name>/create 就绪后再生成；超时则走 ros_gz_sim create CLI（仍会做 success 检查）。
        # 默认等待 10s；机器或世界较慢时可自行调大 _wait_for_world_spawn_service 的 timeout_sec。
        self.spawn_client = self.create_client(SpawnEntity, f'/world/{self.world_name}/create')
        self.use_spawn_service = self._wait_for_world_spawn_service(timeout_sec=10.0)
        if not self.use_spawn_service:
            self.get_logger().warn(
                f"在时限内未等到 /world/{self.world_name}/create，将仅用 ros_gz_sim create CLI 尝试生成动态障碍。"
            )

        self.spawn_obstacles()
        
        # Timer for kinematic control (10 Hz)
        self.dt = 0.1
        self.timer = self.create_timer(self.dt, self.control_loop)

    def _wait_for_world_spawn_service(self, timeout_sec=10.0) -> bool:
        srv = f'/world/{self.world_name}/create'
        deadline = time.monotonic() + timeout_sec
        attempt = 0
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            wait = min(5.0, max(0.1, remaining))
            if self.spawn_client.wait_for_service(timeout_sec=wait):
                self.get_logger().info(f'Gazebo 生成服务已就绪: {srv}')
                return True
            attempt += 1
            if attempt % 2 == 0:
                self.get_logger().warn(
                    f'仍在等待 {srv}（Gazebo 世界加载中），剩余约 {remaining:.0f}s …'
                )
        return False

    def _spawn_dynamic_obstacle_via_service(self, obs, obstacle_sdf) -> bool:
        req = SpawnEntity.Request()
        req.entity_factory.name = obs.name
        req.entity_factory.sdf = obstacle_sdf
        req.entity_factory.allow_renaming = True
        if len(obs.waypoints) > 0:
            req.entity_factory.pose.position.x = float(obs.waypoints[0][0])
            req.entity_factory.pose.position.y = float(obs.waypoints[0][1])
            req.entity_factory.pose.position.z = 0.5

        future = self.spawn_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=60.0)
        if not future.done():
            self.get_logger().error(
                f'动态障碍 {obs.name}：调用 {self.world_name}/create 超时，未收到响应。'
            )
            return False
        try:
            resp = future.result()
        except Exception as exc:
            self.get_logger().error(f'动态障碍 {obs.name}：spawn 服务异常: {exc}')
            return False
        if not resp.success:
            self.get_logger().error(
                f'动态障碍 {obs.name}：Gazebo 拒绝生成（success=false）。'
                '请检查终端 Gazebo 报错、world_name 是否与 environment.world_name 一致、SDF 是否合法。'
            )
            return False
        self.get_logger().info(
            f"动态障碍已插入仿真：配置名='{obs.requested_name}'，实体名='{obs.name}'（服务返回 success）。"
        )
        return True

    def get_color_rgba(self, color_name):
        colors = {
            'Red': '1 0 0 1',
            'Green': '0 1 0 1',
            'Blue': '0 0 1 1',
            'Yellow': '1 1 0 1',
            'Black': '0 0 0 1',
            'White': '1 1 1 1'
        }
        return colors.get(color_name, '1 1 1 1')

    def generate_sdf(self, obs_cfg):
        name = obs_cfg.name
        shape = obs_cfg.shape
        color = self.get_color_rgba(obs_cfg.color)
        
        if shape == 'box':
            # Slightly larger default to improve visibility in Gazebo scene.
            geom = "<box><size>1.2 1.2 1.2</size></box>"
        else: # default cylinder
            geom = "<cylinder><radius>0.8</radius><length>1.2</length></cylinder>"
            
        sdf = f"""<?xml version="1.0" ?>
        <sdf version="1.6">
            <model name="{name}">
                <static>false</static>
                <link name="base_link">
                    <gravity>false</gravity>
                    <visual name="visual">
                        <geometry>{geom}</geometry>
                        <material>
                            <ambient>{color}</ambient>
                            <diffuse>{color}</diffuse>
                            <emissive>{color}</emissive>
                        </material>
                    </visual>
                    <collision name="collision">
                        <geometry>{geom}</geometry>
                    </collision>
                    <inertial>
                        <mass>50.0</mass>
                        <inertia>
                            <ixx>4.0</ixx>
                            <iyy>4.0</iyy>
                            <izz>6.0</izz>
                        </inertia>
                    </inertial>
                </link>
                <plugin filename="gz-sim-velocity-control-system" name="gz::sim::systems::VelocityControl">
                    <topic>/model/{name}/cmd_vel</topic>
                </plugin>
            </model>
        </sdf>
        """
        return sdf

    def spawn_obstacles(self):
        for cfg in self.obs_configs:
            obs = DynamicObstacle(cfg, self)
            self.obstacles.append(obs)

            obstacle_sdf = self.generate_sdf(obs)
            self.get_logger().info(
                f"Preparing dynamic obstacle: requested='{obs.requested_name}', runtime='{obs.name}', "
                f"waypoints={obs.waypoints}, speed={obs.speed}"
            )

            spawned = False
            if self.use_spawn_service:
                spawned = self._spawn_dynamic_obstacle_via_service(obs, obstacle_sdf)
            if not spawned:
                self.get_logger().warn(
                    f"动态障碍 {obs.name}：服务路径未成功，改用 ros_gz_sim create CLI。"
                )
                self._spawn_with_create_cli(obs, obstacle_sdf)

    def _spawn_with_create_cli(self, obs, obstacle_sdf):
        """Spawn an obstacle with ros_gz_sim create as a fallback path."""
        x = float(obs.waypoints[0][0]) if len(obs.waypoints) > 0 else 0.0
        y = float(obs.waypoints[0][1]) if len(obs.waypoints) > 0 else 0.0
        z = 0.5

        tmp_sdf_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sdf', delete=False) as tmpf:
                tmpf.write(obstacle_sdf)
                tmp_sdf_path = tmpf.name

            cmd = [
                'ros2', 'run', 'ros_gz_sim', 'create',
                '-world', self.world_name,
                '-file', tmp_sdf_path,
                '-name', obs.name,
                '-x', str(x),
                '-y', str(y),
                '-z', str(z)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.get_logger().info(
                    f"动态障碍已通过 CLI 插入：'{obs.name}'（ros_gz_sim create）。"
                )
            else:
                detail = (result.stderr or result.stdout or '').strip()
                self.get_logger().error(
                    f"CLI 生成 {obs.name} 失败（code={result.returncode}）：{detail}"
                )
        except Exception as exc:
            self.get_logger().error(f"Exception while spawning {obs.name} via CLI: {exc}")
        finally:
            if tmp_sdf_path and os.path.exists(tmp_sdf_path):
                try:
                    os.remove(tmp_sdf_path)
                except Exception:
                    pass

    def control_loop(self):
        for obs in self.obstacles:
            if not obs.active:
                continue
                
            target_wp = obs.waypoints[obs.current_wp_idx]
            tx, ty = float(target_wp[0]), float(target_wp[1])
            
            dx = tx - obs.x
            dy = ty - obs.y
            dist = math.hypot(dx, dy)
            
            # Check waypoint arrival
            if dist < 0.5:
                if len(obs.waypoints) > 1:
                    if obs.loop:
                        # 往复巡逻逻辑 (Ping-pong)
                        obs.current_wp_idx += obs.direction
                        if obs.current_wp_idx >= len(obs.waypoints):
                            obs.direction = -1
                            obs.current_wp_idx = len(obs.waypoints) - 2
                            if obs.current_wp_idx < 0:
                                obs.current_wp_idx = 0
                        elif obs.current_wp_idx < 0:
                            obs.direction = 1
                            obs.current_wp_idx = 1
                            if obs.current_wp_idx >= len(obs.waypoints):
                                obs.current_wp_idx = 0
                    else:
                        obs.current_wp_idx += 1
                        if obs.current_wp_idx >= len(obs.waypoints):
                            obs.active = False
                            # Stop the obstacle
                            twist = Twist()
                            obs.cmd_vel_pub.publish(twist)
                            continue
                target_wp = obs.waypoints[obs.current_wp_idx]
                tx, ty = float(target_wp[0]), float(target_wp[1])
                dx = tx - obs.x
                dy = ty - obs.y
                dist = math.hypot(dx, dy)
            
            # Kinematic estimation
            if dist > 0:
                vx = (dx / dist) * obs.speed
                vy = (dy / dist) * obs.speed
            else:
                vx = 0.0
                vy = 0.0
                
            obs.x += vx * self.dt
            obs.y += vy * self.dt
            
            # Publish twist
            twist = Twist()
            twist.linear.x = vx
            twist.linear.y = vy
            twist.angular.z = 0.0 # pure holonomic translation
            obs.cmd_vel_pub.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = ScenarioManager()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        for obs in node.obstacles:
            obs.cleanup()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
