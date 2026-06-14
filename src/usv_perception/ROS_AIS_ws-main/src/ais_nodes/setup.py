from setuptools import find_packages, setup

package_name = 'ais_nodes'
submodule_ais_receiver = "ais_nodes/AIS_receiver"
submodule_geo_utils = "ais_nodes/geo_utils"

setup(
    name=package_name,
    version='0.0.0',
    #packages=find_packages(exclude=['test']),
    packages=[package_name, submodule_ais_receiver, submodule_geo_utils],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='cczh',
    maintainer_email='vectorwang@hotmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    entry_points={
        'console_scripts': [
            'ais_parse_node = ais_nodes.ais_parse_node:main',
            'ais_db_node = ais_nodes.ais_db_node:main',
            'ais_tf_node = ais_nodes.ais_tf_node:main',
            'ais_map_pub_node = ais_nodes.ais_map_pub_node:main',
        ],
    },
)
