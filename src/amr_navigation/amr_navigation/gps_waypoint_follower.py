#!/usr/bin/env python3
"""Follow a list of GPS waypoints with Nav2 on ROS 2 Humble.

Humble's Nav2 does not expose the /follow_gps_waypoints action, so this node:
  1. reads waypoints (lat/lon/yaw) from a YAML file,
  2. converts each one to a map-frame pose using robot_localization's
     /fromLL service (navsat_transform_node),
  3. sends the resulting poses to Nav2 via BasicNavigator.followWaypoints().
"""

import math
import os
import time

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geographic_msgs.msg import GeoPoint
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.node import Node
from robot_localization.srv import FromLL
from tf2_ros import Buffer, TransformException, TransformListener


def yaw_to_quaternion(yaw):
    """Return (x, y, z, w) for a rotation of `yaw` about the Z axis."""
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class GpsWaypointFollower(Node):
    def __init__(self):
        super().__init__("gps_waypoint_follower")

        default_wp = os.path.join(
            get_package_share_directory("amr_navigation"), "config", "waypoints.yaml"
        )
        self.declare_parameter("waypoints_file", default_wp)
        self.declare_parameter("direct_to_goal", False)
        self.waypoints_file = (
            self.get_parameter("waypoints_file").get_parameter_value().string_value
        )
        self.direct_to_goal = (
            self.get_parameter("direct_to_goal").get_parameter_value().bool_value
        )

        self.from_ll_client = self.create_client(FromLL, "/fromLL")
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

    def load_waypoints(self):
        with open(self.waypoints_file, "r") as f:
            data = yaml.safe_load(f)
        wps = data.get("waypoints", [])
        self.get_logger().info(
            f"Loaded {len(wps)} waypoints from {self.waypoints_file}"
        )
        return wps

    def wait_for_from_ll(self):
        self.get_logger().info("Waiting for /fromLL service (navsat_transform)...")
        while not self.from_ll_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().warn("/fromLL not available yet, retrying...")
        self.get_logger().info("/fromLL is available.")

    def wait_for_map_tf(self, timeout_sec=60.0):
        """Block until map->base_footprint is available at the current sim time."""
        self.get_logger().info("Waiting for map -> base_footprint TF...")
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            try:
                self._tf_buffer.lookup_transform(
                    "map",
                    "base_footprint",
                    rclpy.time.Time(),
                    timeout=rclpy.duration.Duration(seconds=0.5),
                )
                self.get_logger().info("map -> base_footprint TF is ready.")
                return
            except TransformException:
                rclpy.spin_once(self, timeout_sec=0.2)
        raise RuntimeError("Timed out waiting for map -> base_footprint TF")

    def stamp_poses(self, poses):
        stamp = self.get_clock().now().to_msg()
        for pose in poses:
            pose.header.frame_id = "map"
            pose.header.stamp = stamp
        return poses

    def gps_to_map_pose(self, lat, lon, yaw):
        req = FromLL.Request()
        req.ll_point = GeoPoint(latitude=float(lat), longitude=float(lon), altitude=0.0)
        future = self.from_ll_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        if future.result() is None:
            raise RuntimeError("Call to /fromLL failed")

        map_point = future.result().map_point
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.pose.position.x = map_point.x
        pose.pose.position.y = map_point.y
        pose.pose.position.z = 0.0
        qx, qy, qz, qw = yaw_to_quaternion(float(yaw))
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        self.get_logger().info(
            f"GPS ({lat:.7f}, {lon:.7f}) -> map ({map_point.x:.2f}, {map_point.y:.2f})"
        )
        return pose


def main():
    rclpy.init()
    follower = GpsWaypointFollower()

    follower.wait_for_from_ll()
    raw_waypoints = follower.load_waypoints()

    poses = follower.stamp_poses(
        [
            follower.gps_to_map_pose(
                wp["latitude"], wp["longitude"], wp.get("yaw", 0.0)
            )
            for wp in raw_waypoints
        ]
    )

    navigator = BasicNavigator()
    follower.get_logger().info("Waiting for Nav2 to become active...")
    navigator.waitUntilNav2Active(localizer="bt_navigator")
    follower.wait_for_map_tf()

    if follower.direct_to_goal:
        follower.get_logger().info("Navigating straight to point B...")
        navigator.goToPose(poses[-1])
    else:
        follower.get_logger().info(
            f"Following {len(poses)} GPS waypoints A -> ... -> B"
        )
        navigator.followWaypoints(poses)

    while not navigator.isTaskComplete():
        feedback = navigator.getFeedback()
        if feedback is not None:
            if hasattr(feedback, "number_of_poses_remaining"):
                follower.get_logger().info(
                    f"Waypoints remaining: {feedback.number_of_poses_remaining}"
                )
            elif hasattr(feedback, "distance_remaining"):
                follower.get_logger().info(
                    f"Distance remaining: {feedback.distance_remaining:.2f} m"
                )
        rclpy.spin_once(follower, timeout_sec=0.5)

    result = navigator.getResult()
    if result == TaskResult.SUCCEEDED:
        follower.get_logger().info("Reached point B (all waypoints completed).")
    elif result == TaskResult.CANCELED:
        follower.get_logger().warn("GPS waypoint navigation was canceled.")
    else:
        follower.get_logger().error("GPS waypoint navigation failed.")

    follower.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
