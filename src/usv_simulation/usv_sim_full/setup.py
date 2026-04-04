from setuptools import setup, find_packages
from glob import glob
import os

package_name = 'usv_sim_full'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/usv_sim_full']),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py') + ['launch/notes.md']),
        (os.path.join('share', package_name, 'test_env'), glob('test_env/*')),
        (os.path.join('share', package_name, 'launch/components'), glob('launch/components/*.py')),
    ] + [
        (os.path.join('share', package_name, root), [os.path.join(root, f) for f in files])
        for root, dirs, files in os.walk('description')
    ] + [
        (os.path.join('share', package_name, root), [os.path.join(root, f) for f in files])
        for root, dirs, files in os.walk('worlds')
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='MurphyChen',
    maintainer_email='murphy.chen@xxx.com',
    description='A YAML-driven USV simulation package with dynamic sensor configuration',
    license='MIT',
    
    entry_points={
        'console_scripts': [
            'odom_tf_broadcaster = usv_sim_full.scripts.odom_tf_broadcaster:main',
            'obstacle_spawner = usv_sim_full.scripts.obstacle_spawner:main',
            'dual_thruster_teleop_incre = usv_sim_full.scripts.dual_thruster_teleop_incre:main',
            'cmd_vel_to_thruster = usv_sim_full.scripts.cmd_vel_to_thruster:main',
            'session_manager = usv_sim_full.scripts.session_manager:main',
            'usv_env_dynamics = usv_sim_full.scripts.usv_env_dynamics:main',
            'monitor_left_thruster = usv_sim_full.scripts.monitor_left_thruster:main',
            'simple_thruster_monitor = usv_sim_full.scripts.simple_thruster_monitor:main',
            'dual_namespace_teleop = usv_sim_full.scripts.dual_namespace_teleop:main',
            'test_thruster_response = usv_sim_full.scripts.test_thruster_response:main',
            'thruster_diagnostics = usv_sim_full.scripts.thruster_diagnostics:main',
            'usv_sim_wrapper = usv_sim_full.scripts.usv_sim_wrapper:main',
            'scenario_manager_node = usv_sim_full.scripts.scenario_manager_node:main',
            'tf_namespace_relay = usv_sim_full.scripts.tf_namespace_relay:main',
        ],
    },
)
