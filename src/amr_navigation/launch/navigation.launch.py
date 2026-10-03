"""Localization (dual EKF + navsat_transform) and the Nav2 stack (no static map)."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_nav = get_package_share_directory("amr_navigation")
    pkg_nav2_bringup = get_package_share_directory("nav2_bringup")

    use_sim_time = LaunchConfiguration("use_sim_time")

    ekf_params = os.path.join(pkg_nav, "config", "dual_ekf_navsat.yaml")
    nav2_params = os.path.join(pkg_nav, "config", "nav2_no_map.yaml")

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time", default_value="true", description="Use the Gazebo clock"
    )

    # ---- robot_localization: local EKF (odom->base_footprint) ----
    ekf_odom = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node_odom",
        output="screen",
        parameters=[ekf_params, {"use_sim_time": use_sim_time}],
        remappings=[("odometry/filtered", "odometry/local")],
    )

    # ---- robot_localization: global EKF (map->odom) ----
    ekf_map = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node_map",
        output="screen",
        parameters=[ekf_params, {"use_sim_time": use_sim_time}],
        remappings=[("odometry/filtered", "odometry/global")],
    )

    # ---- robot_localization: navsat_transform (GPS <-> map, /fromLL) ----
    navsat_transform = Node(
        package="robot_localization",
        executable="navsat_transform_node",
        name="navsat_transform",
        output="screen",
        parameters=[ekf_params, {"use_sim_time": use_sim_time}],
        remappings=[
            ("imu", "imu"),
            ("gps/fix", "gps/fix"),
            # Local EKF odom (not global): required for correct GPS->map fusion.
            ("odometry/filtered", "odometry/local"),
        ],
    )

    # ---- Nav2 stack (no map: planner, controller, behaviors, bt, waypoints) ----
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2_bringup, "launch", "navigation_launch.py")
        ),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "params_file": nav2_params,
            "autostart": "true",
        }.items(),
    )

    return LaunchDescription([
        declare_use_sim_time,
        ekf_odom,
        ekf_map,
        navsat_transform,
        nav2,
    ])
