import re

launch_file = '/home/cczh/USV_ROS/src/USV_Simulation/src/usv_sim_full/launch/main.launch.py'

with open(launch_file, 'r') as f:
    content = f.read()

# I want to add usv_sim_wrapper Node to the return list.
wrapper_logic = """
    import re
    sanitized_robot_name = re.sub(r"[^A-Za-z0-9_\\-]", '_', str(robot_name))
    
    wrapper_node = Node(
        package='usv_sim_full',
        executable='usv_sim_wrapper',
        name='usv_sim_wrapper',
        output='screen',
        parameters=[{
            'odom_topic': f'/model/{sanitized_robot_name}/odometry',
            'gps_topic': '/sensors/gps/data'
        }],
        parameters_overrides=[]
    )
    
    # 返回所有启动项
    return [
        infra_sim_include,
        robot_launch,
        viz_launch,
        wrapper_node
    ]
"""

content = content.replace('''    # 返回所有启动项
    return [
        infra_sim_include,
        robot_launch,
        viz_launch
    ]''', wrapper_logic)


with open(launch_file, 'w') as f:
    f.write(content)

