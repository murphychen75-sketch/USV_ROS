import re

setup_path = '/home/cczh/USV_ROS/src/USV_Simulation/src/usv_sim_full/setup.py'

with open(setup_path, 'r') as f:
    setup_content = f.read()

target = "'thruster_diagnostics = usv_sim_full.scripts.thruster_diagnostics:main',"
replacement = "'thruster_diagnostics = usv_sim_full.scripts.thruster_diagnostics:main',\n            'usv_sim_wrapper = usv_sim_full.scripts.usv_sim_wrapper:main',"

new_content = setup_content.replace(target, replacement)
with open(setup_path, 'w') as f:
    f.write(new_content)

