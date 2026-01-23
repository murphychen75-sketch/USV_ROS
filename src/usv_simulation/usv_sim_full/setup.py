from setuptools import setup, find_packages
from glob import glob
import os

package_name = 'usv_sim_full'

# 收集模型文件
model_data_files = []
if os.path.exists('models'):
    for model_file in glob('models/**/*', recursive=True):
        if os.path.isfile(model_file):
            model_dir = os.path.dirname(model_file)
            model_data_files.append((os.path.join('share', package_name, model_dir), [model_file]))

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/usv_sim_full']),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'scripts'), glob('scripts/*')),
        (os.path.join('share', package_name, 'templates'), glob('templates/*')),
        (os.path.join('share', package_name, 'test_env'), glob('test_env/*')),
        (os.path.join('share', package_name, 'launch/components'), glob('launch/components/*.py')),
    ] + model_data_files,  # 添加模型文件
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='MurphyChen',
    maintainer_email='murphy.chen@xxx.com',
    description='A YAML-driven USV simulation package with dynamic sensor configuration',
    license='MIT',
    
    entry_points={
        'console_scripts': [
            'obstacle_spawner = usv_sim_full.scripts.obstacle_spawner:main',
        ],
    },
)