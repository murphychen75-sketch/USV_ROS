from setuptools import setup

package_name = 'usv_mavlink_bridge'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
        ('share/' + package_name + '/launch', ['launch/usv_mavlink_bridge.launch.py']),
        ('share/' + package_name + '/config', ['config/bridge_topics.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='your_name',
    maintainer_email='your@email.com',
    description='USV MAVLink bridge package',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'heartbeat = usv_mavlink_bridge.mav_heartbeat:main',
            'imu_bridge = usv_mavlink_bridge.mav_imu_bridge:main',
            'imu_sim = usv_mavlink_bridge.imu_sim:main',
            'rc_bridge = usv_mavlink_bridge.mav_rc_bridge:main',
            'gps_sim = usv_mavlink_bridge.gps_sim:main',
            'gps_bridge = usv_mavlink_bridge.mav_gps_bridge:main',
            'autopilot_state_bridge = usv_mavlink_bridge.autopilot_state_bridge:main',
        ],
    },
)