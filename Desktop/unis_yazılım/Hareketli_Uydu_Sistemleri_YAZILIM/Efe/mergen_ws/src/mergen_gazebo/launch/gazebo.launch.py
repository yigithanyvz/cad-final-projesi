import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    gazebo_launch = PathJoinSubstitution([FindPackageShare('gazebo_ros'), 'launch', 'gazebo.launch.py'])
    world = PathJoinSubstitution([FindPackageShare('mergen_gazebo'), 'worlds', 'mergen_test.world'])
    stewart_sdf_dir = '/home/efe/Masaüstü/unis/yazilim/kerim unis/stewart_kerim/sdf'
    return LaunchDescription([
        SetEnvironmentVariable(
            name='GAZEBO_MODEL_PATH',
            value=os.pathsep.join([
                '/tmp/opencode',
                stewart_sdf_dir,
                '/usr/share/gazebo-11/models',
            ]),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gazebo_launch),
            launch_arguments={'world': world}.items(),
        )
    ])
