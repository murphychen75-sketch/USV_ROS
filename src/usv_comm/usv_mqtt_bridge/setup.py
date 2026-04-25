from setuptools import find_packages, setup


package_name = "usv_mqtt_bridge"


setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", ["config/params.yaml"]),
        (f"share/{package_name}/launch", ["launch/usv_mqtt_bridge.launch.py"]),
        (f"share/{package_name}/docs", ["docs/message_contract.md"]),
    ],
    install_requires=["setuptools", "paho-mqtt>=1.6"],
    zip_safe=True,
    maintainer="Cursor",
    maintainer_email="cursor@example.com",
    description="ROS 2 MQTT bridge node for USV telemetry and commands.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "usv_mqtt_bridge_node = usv_mqtt_bridge.node:main",
        ],
    },
)
