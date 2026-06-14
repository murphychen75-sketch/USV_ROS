from setuptools import find_packages, setup


package_name = "usv_monitor"


setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", ["config/monitor_params.yaml"]),
        (f"share/{package_name}/launch", ["launch/usv_monitor.launch.py"]),
    ],
    install_requires=["setuptools", "psutil"],
    zip_safe=True,
    maintainer="USV Developer",
    maintainer_email="developer@usv.com",
    description="USV monitor nodes for Jetson status and heartbeat.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "system_status_node = usv_monitor.system_status_node:main",
            "heartbeat_node = usv_monitor.heartbeat_node:main",
            "autopilot_control_service_node = usv_monitor.autopilot_control_service_node:main",
            "alarm_watchdog_node = usv_monitor.alarm_watchdog_node:main",
        ],
    },
)
