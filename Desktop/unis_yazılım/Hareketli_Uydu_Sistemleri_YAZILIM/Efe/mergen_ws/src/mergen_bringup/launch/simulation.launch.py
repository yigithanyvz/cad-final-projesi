from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    gazebo = IncludeLaunchDescription(PythonLaunchDescriptionSource(
        PathJoinSubstitution([FindPackageShare('mergen_gazebo'), 'launch', 'gazebo.launch.py'])
    ))
    imu_filter = IncludeLaunchDescription(PythonLaunchDescriptionSource(
        PathJoinSubstitution([FindPackageShare('mergen_estimation'), 'launch', 'imu_filter.launch.py'])
    ))
    control = IncludeLaunchDescription(PythonLaunchDescriptionSource(
        PathJoinSubstitution([FindPackageShare('mergen_control'), 'launch', 'control.launch.py'])
    ))
    return LaunchDescription([gazebo, imu_filter, control])
