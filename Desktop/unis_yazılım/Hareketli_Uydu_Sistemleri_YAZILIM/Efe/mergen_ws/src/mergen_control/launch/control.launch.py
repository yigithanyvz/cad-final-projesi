from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='mergen_control',
            executable='control_node',
            name='mergen_control_node',
            output='screen',
        )
    ])
