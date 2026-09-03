"""Expose Klara's ROS 2 graph to Foxglove over WebSocket.

Start Isaac Sim and press Play before launching this file.  The D455 graph in
``assets/usd/klara.usd`` publishes color/depth images and CameraInfo; Foxglove
Bridge discovers those topics automatically along with the rest of the graph.

Example::

    ros2 launch klara_bringup foxglove.launch.py

Then connect Foxglove to ``ws://localhost:8765``.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    address_arg = DeclareLaunchArgument(
        "address",
        default_value="0.0.0.0",
        description="Network address on which Foxglove Bridge listens.",
    )
    port_arg = DeclareLaunchArgument(
        "port",
        default_value="8765",
        description="WebSocket port on which Foxglove Bridge listens.",
    )

    foxglove_bridge = Node(
        package="foxglove_bridge",
        executable="foxglove_bridge",
        name="foxglove_bridge",
        output="screen",
        parameters=[
            {
                "address": LaunchConfiguration("address"),
                "port": ParameterValue(LaunchConfiguration("port"), value_type=int),
            }
        ],
    )

    return LaunchDescription([address_arg, port_arg, foxglove_bridge])
