#!/usr/bin/env python3
"""Lightweight sensor reader: subscribes to the lidar, GPS, depth camera and IMU
topics and periodically logs a short status summary. Demonstrates explicit
reading of every required sensor stream."""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, Imu, LaserScan, NavSatFix, PointCloud2


class SensorMonitor(Node):
    def __init__(self):
        super().__init__("sensor_monitor")

        self.last_scan = None
        self.last_fix = None
        self.last_depth = False
        self.last_points = False
        self.last_imu = None

        self.create_subscription(
            LaserScan, "/scan", self.scan_cb, qos_profile_sensor_data
        )
        self.create_subscription(
            NavSatFix, "/gps/fix", self.fix_cb, qos_profile_sensor_data
        )
        self.create_subscription(
            Image, "/camera/depth/image_raw", self.depth_cb, qos_profile_sensor_data
        )
        self.create_subscription(
            PointCloud2, "/camera/points", self.points_cb, qos_profile_sensor_data
        )
        self.create_subscription(Imu, "/imu", self.imu_cb, qos_profile_sensor_data)

        self.create_timer(2.0, self.report)

    def scan_cb(self, msg):
        valid = [r for r in msg.ranges if msg.range_min < r < msg.range_max]
        self.last_scan = min(valid) if valid else None

    def fix_cb(self, msg):
        self.last_fix = (msg.latitude, msg.longitude, msg.altitude)

    def depth_cb(self, msg):
        self.last_depth = True

    def points_cb(self, msg):
        self.last_points = True

    def imu_cb(self, msg):
        self.last_imu = msg.angular_velocity.z

    def report(self):
        scan = f"{self.last_scan:.2f} m" if self.last_scan is not None else "n/a"
        if self.last_fix is not None:
            fix = f"{self.last_fix[0]:.6f}, {self.last_fix[1]:.6f}"
        else:
            fix = "n/a"
        imu = f"{self.last_imu:.3f} rad/s" if self.last_imu is not None else "n/a"
        self.get_logger().info(
            f"[sensors] lidar closest: {scan} | gps: {fix} | "
            f"depth img: {'ok' if self.last_depth else 'n/a'} | "
            f"depth cloud: {'ok' if self.last_points else 'n/a'} | imu wz: {imu}"
        )


def main():
    rclpy.init()
    node = SensorMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
