import re

setup_path = '/home/cczh/USV_ROS/src/USV_Simulation/src/usv_sim_full/setup.py'

with open(setup_path, 'r') as f:
    setup_content = f.read()

# Add usv_sim_wrapper to console_scripts
target = "'thruster_diagnostics = usv_sim_full.scripts.thruster_diagnostics:main',\n"
replacement = target + "            'usv_sim_wrapper = scripts.usv_sim_wrapper:main',\n"

# Looks like they use the module name in entry point, let's copy others:
# Actually wait: scripts are located at the root of `scripts` but not exposed as proper python packages because `find_packages()` might not find `scripts` if lacks __init__.py? Wait, wait:
# Odom TF is 'odom_tf_broadcaster = usv_sim_full.scripts.odom_tf_broadcaster:main'
# Oh, it's inside usv_sim_full/scripts folder! But I created it in src/usv_sim_full/scripts

