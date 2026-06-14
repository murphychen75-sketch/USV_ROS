import sys

from setuptools import find_packages, setup


package_name = "usv_mqtt_bridge"

# Some colcon/ament tooling variants may forward an '--editable' flag directly to
# setup.py. setuptools' distutils argument parser does not recognize it, so we
# strip it here to keep builds compatible across environments.
def _strip_unsupported_flag(flag: str, expects_value: bool = False) -> None:
    while flag in sys.argv:
        idx = sys.argv.index(flag)
        sys.argv.pop(idx)
        if expects_value and idx < len(sys.argv):
            sys.argv.pop(idx)


_strip_unsupported_flag("--editable", expects_value=False)
_strip_unsupported_flag("--build-directory", expects_value=True)
_strip_unsupported_flag("--uninstall", expects_value=False)


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
    entry_points={
        "console_scripts": [
            "usv_mqtt_bridge_node = usv_mqtt_bridge.node:main",
            "topic_json_adapter_node = usv_mqtt_bridge.adapters.topic:main",
            "service_json_adapter_node = usv_mqtt_bridge.adapters.service:main",
            "action_json_adapter_node = usv_mqtt_bridge.adapters.action:main",
        ],
    },
)
