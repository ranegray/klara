# Differential-drive `/cmd_vel` test

Before testing, make sure the robot has clear space. Start the ROS 2 bridge,
open the robot in Isaac Sim, and press **Play**.

In a sourced ROS 2 terminal, command the robot forward at `0.15 m/s`:

```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.15}, angular: {z: 0.0}}"
```

Press `Ctrl-C` to stop publishing, then send an explicit zero-velocity command:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```
