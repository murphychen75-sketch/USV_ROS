from setuptools import find_packages, setup


package_name = "usv_mavlink_bridge"


setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml", "README.md"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Cursor",
    maintainer_email="cursor@example.com",
    description="Placeholder ROS 2 package for future USV MAVLink bridge integration.",
    license="MIT",
    tests_require=["pytest"],
)
