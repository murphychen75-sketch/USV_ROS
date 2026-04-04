#!/bin/bash
set -e

# Simple entrypoint that sources ROS 2 and the workspace (if built)
if [ -f /opt/ros/humble/setup.sh ]; then
  source /opt/ros/humble/setup.sh
fi

# Source install overlay if present
if [ -f /workspace/install/setup.bash ]; then
  source /workspace/install/setup.bash
fi

# Forward to user's command
exec "$@"
