import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share_dir = get_package_share_directory("stewart")
    stewart_launch = os.path.join(share_dir, "launch", "stewart.launch.py")

    return LaunchDescription(
        [
            DeclareLaunchArgument("gui", default_value="true"),
            DeclareLaunchArgument("verbose", default_value="true"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(stewart_launch),
                launch_arguments={
                    "gui": LaunchConfiguration("gui"),
                    "verbose": LaunchConfiguration("verbose"),
                }.items(),
            ),
            Node(
                package="stewart",
                executable="ik",
                name="ik",
                output="screen",
            ),
        ]
    )
