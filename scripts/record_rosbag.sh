#!/usr/bin/env bash
# Record the key topics into a rosbag2 for later playback.
# Usage: ./scripts/record_rosbag.sh [output_dir]

set -e

OUT="${1:-amr_demo_$(date +%Y%m%d_%H%M%S)}"

ros2 bag record -o "${OUT}" \
  /tf /tf_static \
  /scan \
  /gps/fix \
  /imu \
  /camera/image_raw /camera/depth/image_raw /camera/points /camera/camera_info \
  /odom /odometry/local /odometry/global /odometry/gps \
  /cmd_vel \
  /plan \
  /global_costmap/costmap /local_costmap/costmap

echo "Rosbag saved to ${OUT}"
