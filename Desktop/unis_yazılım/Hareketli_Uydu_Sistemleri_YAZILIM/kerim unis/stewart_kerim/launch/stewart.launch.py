import os

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def extend_env(name, value):
    current = os.environ.get(name)
    if current:
        value = value + os.pathsep + current
    return SetEnvironmentVariable(name=name, value=value)


def generate_launch_description():
    share_dir = get_package_share_directory("stewart")
    prefix_dir = get_package_prefix("stewart")
    gazebo_share = get_package_share_directory("gazebo_ros")

    model_path = os.pathsep.join(
        [
            os.path.join(share_dir, "sdf"),
            "/usr/share/gazebo-11/models",
        ]
    )
    plugin_path = os.path.join(prefix_dir, "lib", "stewart")
    world_path = os.path.join(share_dir, "world", "stewart.world")

    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_share, "launch", "gazebo.launch.py")
        ),
        launch_arguments={
            "world": world_path,
            "gui": LaunchConfiguration("gui"),
            "verbose": LaunchConfiguration("verbose"),
        }.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("gui", default_value="true"),
            DeclareLaunchArgument("verbose", default_value="true"),
            extend_env("GAZEBO_MODEL_PATH", model_path),
            extend_env("GAZEBO_PLUGIN_PATH", plugin_path),
            SetEnvironmentVariable(name="GAZEBO_MODEL_DATABASE_URI", value=""),
            gazebo_launch,
        ]
    )
