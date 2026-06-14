#!/usr/bin/env bash
# Launches the full multi-sensor simulation pipeline (vision + mmWave) after building.
# Usage: ./scripts/run_multi_sensor_sim.sh [additional ros2 launch args]

set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKSPACE_ROOT"

echo "[run_multi_sensor_sim] Removing previous build/install/log directories..."
rm -rf build install log

echo "[run_multi_sensor_sim] Building usv_interfaces, ground_truth_sim, percision_sim..."
colcon build --packages-select usv_interfaces ground_truth_sim percision_sim

echo "[run_multi_sensor_sim] Sourcing install/setup.bash..."
# shellcheck disable=SC1091
set +u
source "$WORKSPACE_ROOT/install/setup.bash"
set -u

PARAMS_FILE="$(ros2 pkg prefix percision_sim)/share/percision_sim/config/multi_sensor_params.yaml"
echo "[run_multi_sensor_sim] Launching percision_sim multi_sensor_sim.launch.py with params ${PARAMS_FILE}"
ros2 launch percision_sim multi_sensor_sim.launch.py params_file:="$PARAMS_FILE" "$@"
