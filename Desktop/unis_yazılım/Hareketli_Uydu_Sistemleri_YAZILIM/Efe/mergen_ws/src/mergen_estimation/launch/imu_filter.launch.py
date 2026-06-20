from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='mergen_estimation',
            executable='imu_filter_node',
            name='mergen_imu_filter_node',
            output='screen',
        )
    ])
