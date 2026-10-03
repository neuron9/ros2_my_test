"""Single-command bringup: Gazebo + robot + localization + Nav2 + RViz +
GPS waypoint follower."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            TimerAction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_gazebo = get_package_share_directory("amr_gazebo")
    pkg_nav = get_package_share_directory("amr_navigation")

    use_sim_time = LaunchConfiguration("use_sim_time")
    use_rviz = LaunchConfiguration("use_rviz")
    autostart_waypoints = LaunchConfiguration("autostart_waypoints")
    waypoints_file = LaunchConfiguration("waypoints_file")

    rviz_config = os.path.join(pkg_nav, "rviz", "amr.rviz")
    default_waypoints = os.path.join(pkg_nav, "config", "waypoints.yaml")

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time", default_value="true", description="Use the Gazebo clock"
    )
    declare_use_rviz = DeclareLaunchArgument(
        "use_rviz", default_value="true", description="Launch RViz"
    )
    declare_autostart_wp = DeclareLaunchArgument(
        "autostart_waypoints",
        default_value="true",
        description="Automatically start following GPS waypoints after startup",
    )
    declare_waypoints_file = DeclareLaunchArgument(
        "waypoints_file",
        default_value=default_waypoints,
        description="Path to the GPS waypoints YAML file",
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo, "launch", "gazebo.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )

    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav, "launch", "navigation.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config],
        parameters=[{"use_sim_time": use_sim_time}],
        condition=IfCondition(use_rviz),
    )

    sensor_monitor = Node(
        package="amr_navigation",
        executable="sensor_monitor",
        name="sensor_monitor",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # Give Gazebo, localization and Nav2 time to come up before sending goals.
    waypoint_follower = TimerAction(
        period=25.0,
        actions=[
            Node(
                package="amr_navigation",
                executable="gps_waypoint_follower",
                name="gps_waypoint_follower",
                output="screen",
                parameters=[
                    {"use_sim_time": use_sim_time},
                    {"waypoints_file": waypoints_file},
                ],
                condition=IfCondition(autostart_waypoints),
            )
        ],
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_use_rviz,
        declare_autostart_wp,
        declare_waypoints_file,
        gazebo,
        navigation,
        rviz,
        sensor_monitor,
        waypoint_follower,
    ])
