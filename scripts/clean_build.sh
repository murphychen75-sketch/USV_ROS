#!/usr/bin/env bash
set -euo pipefail

# Build the workspace in a clean ROS environment to avoid stale prefix-path warnings
# and reduce OpenCV ABI conflict noise caused by /usr/local precedence.

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_ROS_SETUP="/opt/ros/humble/setup.bash"

print_help() {
  cat <<'EOF'
Usage:
  scripts/clean_build.sh [colcon args...]

Examples:
  scripts/clean_build.sh
  scripts/clean_build.sh --packages-select gy_radar_driver usv_sim_full
  scripts/clean_build.sh --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo

What this script does:
  1) Clears inherited AMENT/CMAKE/COLCON prefix env vars for a clean first build.
  2) Sources /opt/ros/humble/setup.bash.
  3) Pins LD_LIBRARY_PATH to system dirs first to avoid /usr/local OpenCV conflicts.
  4) Runs colcon build with safe defaults:
     --symlink-install
     --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_IGNORE_PATH=/usr/local

Notes:
  - Any extra args are appended to colcon build.
  - After build, run: source install/setup.bash
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_help
  exit 0
fi

if [[ ! -f "$DEFAULT_ROS_SETUP" ]]; then
  echo "[ERROR] ROS setup not found: $DEFAULT_ROS_SETUP" >&2
  exit 1
fi

cd "$WORKSPACE_DIR"

# Clean inherited prefix paths from previous workspace states.
unset AMENT_PREFIX_PATH || true
unset CMAKE_PREFIX_PATH || true
unset COLCON_PREFIX_PATH || true

# shellcheck source=/dev/null
set +u
source "$DEFAULT_ROS_SETUP"
set -u

# Keep system OpenCV ahead of /usr/local to avoid linker warning noise.
export LD_LIBRARY_PATH="/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

echo "[INFO] Workspace: $WORKSPACE_DIR"
echo "[INFO] Running clean colcon build..."

colcon build \
  --symlink-install \
  --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_IGNORE_PATH=/usr/local \
  "$@"

echo "[INFO] Build completed. Next: source install/setup.bash"
