#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped
import math

class TFBroadcasterNode(Node):
    def __init__(self):
        super().__init__('tf_broadcaster')
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # 存储所有的TF变换关系
        self.transforms = []
        
        # 定时器，定期广播所有TF变换
        self.timer = self.create_timer(0.1, self.timer_callback)  # 每0.1秒广播一次
        
        self.get_logger().info('TF Broadcaster Node has been started.')
        self.add_transforms_interactively()
        
    def add_transforms_interactively(self):
        """交互式添加TF变换"""
        try:
            while True:
                print("\n请输入坐标系变换参数:")
                
                parent_frame = input("母坐标系名称 (例如: map): ") or "map"
                child_frame = input("子坐标系名称 (例如: base_link): ") or "base_link"
                
                print("\n请输入平移分量 (单位: 米):")
                x = float(input("X: ") or 0.0)
                y = float(input("Y: ") or 0.0)
                z = float(input("Z: ") or 0.0)
                
                print("\n请输入旋转分量 (单位: 度):")
                roll = math.radians(float(input("Roll: ") or 0.0))
                pitch = math.radians(float(input("Pitch: ") or 0.0))
                yaw = math.radians(float(input("Yaw: ") or 0.0))
                
                # 添加到变换列表
                transform_data = {
                    'parent_frame': parent_frame,
                    'child_frame': child_frame,
                    'x': x,
                    'y': y,
                    'z': z,
                    'roll': roll,
                    'pitch': pitch,
                    'yaw': yaw
                }
                
                self.transforms.append(transform_data)
                self.get_logger().info(f'Added TF: {parent_frame} -> {child_frame}')
                
                # 显示刚刚添加的变换详情
                print(f"\n已添加变换详情:")
                print(f"  坐标系关系: {parent_frame} -> {child_frame}")
                print(f"  平移: X={x:.3f}, Y={y:.3f}, Z={z:.3f}")
                print(f"  旋转: Roll={math.degrees(roll):.1f}°, Pitch={math.degrees(pitch):.1f}°, Yaw={math.degrees(yaw):.1f}°")
                
                cont = input("\n是否继续添加新的变换? (y/n): ")
                if cont.lower() != 'y':
                    break
                    
        except ValueError as e:
            self.get_logger().error(f"输入格式错误: {e}")
        except KeyboardInterrupt:
            print("\n输入被用户中断")
        
        if self.transforms:
            print(f"\n开始广播 {len(self.transforms)} 个坐标变换关系...")
            self.list_all_transforms()  # 列出所有已添加的变换
            print("按 Ctrl+C 停止节点")
        else:
            print("\n没有添加任何变换关系，节点将退出")
            
    def list_all_transforms(self):
        """列出所有已添加的坐标变换"""
        print("\n=== 所有已添加的坐标变换 ===")
        for i, transform_data in enumerate(self.transforms, 1):
            print(f"{i}. {transform_data['parent_frame']} -> {transform_data['child_frame']}")
            print(f"   平移: X={transform_data['x']:.3f}, Y={transform_data['y']:.3f}, Z={transform_data['z']:.3f}")
            print(f"   旋转: Roll={math.degrees(transform_data['roll']):.1f}°, "
                  f"Pitch={math.degrees(transform_data['pitch']):.1f}°, "
                  f"Yaw={math.degrees(transform_data['yaw']):.1f}°")
            print()
            
    def timer_callback(self):
        """定时器回调函数，定期广播所有TF变换"""
        for transform_data in self.transforms:
            self.broadcast_transform(
                transform_data['parent_frame'],
                transform_data['child_frame'],
                transform_data['x'],
                transform_data['y'],
                transform_data['z'],
                transform_data['roll'],
                transform_data['pitch'],
                transform_data['yaw']
            )
    
    def broadcast_transform(self, parent_frame, child_frame, x, y, z, roll, pitch, yaw):
        """
        广播单个坐标系变换
        """
        t = TransformStamped()
        
        # 设置时间戳和坐标系
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = parent_frame
        t.child_frame_id = child_frame
        
        # 设置平移
        t.transform.translation.x = float(x)
        t.transform.translation.y = float(y)
        t.transform.translation.z = float(z)
        
        # 将欧拉角转换为四元数
        quat = self.euler_to_quaternion(float(roll), float(pitch), float(yaw))
        
        # 设置旋转(四元数)
        t.transform.rotation.x = quat[0]
        t.transform.rotation.y = quat[1]
        t.transform.rotation.z = quat[2]
        t.transform.rotation.w = quat[3]
        
        # 发布TF变换
        self.tf_broadcaster.sendTransform(t)
    
    def euler_to_quaternion(self, roll, pitch, yaw):
        """
        将欧拉角转换为四元数
        """
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)

        qx = sr * cp * cy - cr * sp * sy
        qy = cr * sp * cy + sr * cp * sy
        qz = cr * cp * sy - sr * sp * cy
        qw = cr * cp * cy + sr * sp * sy

        return [qx, qy, qz, qw]

def main(args=None):
    # 初始化ROS 2
    rclpy.init(args=args)
    
    # 创建节点
    node = TFBroadcasterNode()
    
    try:
        # 进入ROS 2事件循环
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        # 销毁节点并关闭ROS 2
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()