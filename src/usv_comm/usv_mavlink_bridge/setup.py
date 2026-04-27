from setuptools import setup

package_name = 'ros2_mav_demo'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
        ('share/' + package_name + '/launch', ['launch/demo_launch.py']),
        ('share/' + package_name + '/config', ['config/bridge_topics.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='your_name',
    maintainer_email='your@email.com',
    description='ROS 2 to MAVLink Demo',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'heartbeat = ros2_mav_demo.mav_heartbeat:main',
            'imu_bridge = ros2_mav_demo.mav_imu_bridge:main',
            'imu_sim = ros2_mav_demo.imu_sim:main',
            'rc_bridge = ros2_mav_demo.mav_rc_bridge:main',
            'gps_sim = ros2_mav_demo.gps_sim:main',
            'gps_bridge = ros2_mav_demo.mav_gps_bridge:main',
        ],
    },
)