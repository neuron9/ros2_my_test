"""Start Gazebo Classic with the course world, publish the robot description
and spawn the AMR robot."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_gazebo = get_package_share_directory("amr_gazebo")
    pkg_description = get_package_share_directory("amr_description")
    pkg_gazebo_ros = get_package_share_directory("gazebo_ros")

    use_sim_time = LaunchConfiguration("use_sim_time")
    world = LaunchConfiguration("world")

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time", default_value="true", description="Use the Gazebo clock"
    )
    declare_world = DeclareLaunchArgument(
        "world",
        default_value=os.path.join(pkg_gazebo, "worlds", "course.world"),
        description="Full path to the Gazebo world file",
    )

    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, "launch", "gzserver.launch.py")
        ),
        launch_arguments={
            "world": world,
            "verbose": "true",
        }.items(),
    )

    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, "launch", "gzclient.launch.py")
        )
    )

    robot_state_publisher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_description, "launch", "description.launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )

    spawn_robot = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        name="spawn_amr",
        output="screen",
        arguments=[
            "-topic", "robot_description",
            "-entity", "amr",
            "-x", "0.0",
            "-y", "0.0",
            "-z", "0.12",
            "-Y", "0.0",
        ],
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_world,
        robot_state_publisher,
        gzserver,
        gzclient,
        spawn_robot,
    ])
