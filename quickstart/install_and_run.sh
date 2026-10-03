#!/usr/bin/env bash
# Install dependencies, build the workspace, and launch the AMR simulation.
#
# Usage (from repo root or anywhere):
#   ./quickstart/install_and_run.sh
#   ./quickstart/install_and_run.sh use_rviz:=false
#   ./quickstart/install_and_run.sh --skip-install
#   ./quickstart/install_and_run.sh --skip-build use_rviz:=false
#
# Requires: Ubuntu 22.04, sudo for apt/rosdep on first run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${WS_ROOT}"

SKIP_INSTALL=false
SKIP_BUILD=false
LAUNCH_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-install)
      SKIP_INSTALL=true
      shift
      ;;
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    -h | --help)
      sed -n '2,12p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      LAUNCH_ARGS+=("$1")
      shift
      ;;
  esac
done

APT_PACKAGES=(
  ros-humble-desktop
  ros-humble-gazebo-ros-pkgs
  ros-humble-gazebo-plugins
  ros-humble-navigation2
  ros-humble-nav2-bringup
  ros-humble-robot-localization
  ros-humble-nav2-simple-commander
  ros-humble-xacro
  ros-humble-geographic-msgs
  libgeographic-dev
  python3-colcon-common-extensions
  python3-rosdep
  python3-vcstool
)

install_system_deps() {
  if [[ "$(id -u)" -eq 0 ]]; then
    echo "ERROR: Do not run this script as root. It will call sudo when needed."
    exit 1
  fi

  if ! command -v apt-get >/dev/null 2>&1; then
    echo "ERROR: apt-get not found. This project runs on Ubuntu 22.04 (see README.md)."
    exit 1
  fi

  echo "==> Updating apt and installing ROS 2 / Gazebo / Nav2 packages..."
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${APT_PACKAGES[@]}"

  if ! command -v rosdep >/dev/null 2>&1; then
    echo "ERROR: rosdep missing after apt install."
    exit 1
  fi

  if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
    echo "==> Initializing rosdep (once per machine)..."
    sudo rosdep init || true
  fi
  rosdep update

  # shellcheck source=/dev/null
  source /opt/ros/humble/setup.bash

  echo "==> rosdep install for workspace packages..."
  rosdep install --from-paths src --ignore-src -r -y
}

ensure_ros() {
  if [[ ! -f /opt/ros/humble/setup.bash ]]; then
    cat <<'EOF'
ERROR: ROS 2 Humble is not installed (/opt/ros/humble missing).

Add the ROS 2 apt repository, then re-run this script without --skip-install:
  https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html

Or install ros-humble-desktop manually and run again.
EOF
    exit 1
  fi
  # shellcheck source=/dev/null
  source /opt/ros/humble/setup.bash
}

build_workspace() {
  echo "==> colcon build (symlink-install)..."
  colcon build --symlink-install
}

launch_sim() {
  if [[ ! -f install/setup.bash ]]; then
    echo "ERROR: install/setup.bash not found. Build first or omit --skip-build."
    exit 1
  fi
  # shellcheck source=/dev/null
  source install/setup.bash
  echo "==> ros2 launch amr_bringup bringup.launch.py ${LAUNCH_ARGS[*]:-<defaults>}"
  exec ros2 launch amr_bringup bringup.launch.py "${LAUNCH_ARGS[@]}"
}

if [[ "${SKIP_INSTALL}" == false ]]; then
  install_system_deps
else
  ensure_ros
fi

if [[ "${SKIP_BUILD}" == false ]]; then
  build_workspace
fi

launch_sim
