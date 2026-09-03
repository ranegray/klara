# USD assets

Isaac Sim USD for the XLeRobot, converted from the source-of-truth URDF in
[`ros2_ws/src/klara_description/urdf/`](../../ros2_ws/src/klara_description/urdf/).

## Import

The importer targets Isaac Sim 6.0.1. Run it with Isaac Sim's bundled Python
launcher; the script itself remains in this repository:

```bash
<isaac-sim>/python.sh <repo>/assets/usd/import_klara.py
```

For example, if Isaac Sim is extracted at `~/isaacsim`:

```bash
~/isaacsim/python.sh /home/justin/klara/assets/usd/import_klara.py
```

This reads `klara_description/urdf/xlerobot.urdf`, resolves its
`package://klara_description/...` mesh paths, and writes one flattened asset
to `assets/usd/klara.usd`. The importer explicitly makes the base mobile while
preserving the link structure and authored collision geometry. Existing output
is not replaced unless `--force` is passed.

The import keeps Isaac's asset transformer disabled. In Isaac Sim 6.0.1 that
transformer recenters the URDF's scaled, visual-only STL links but writes their
fixed-joint anchors in raw millimetres, producing 1,000x offsets when physics
starts. Preserving the authored URDF frames avoids those invalid anchors.

## Differential-drive velocity control

Add the ROS 2 velocity-command graph after importing:

```bash
~/isaacsim/python.sh /home/justin/klara/assets/usd/configure_diffdrive.py
```

The script adds this ActionGraph to `klara.usd`:

```text
/cmd_vel (geometry_msgs/Twist)
  -> Differential Controller (radius 0.0635 m, track 0.45 m)
  -> Articulation Controller
  -> [left_wheel_joint, right_wheel_joint]
```

It also configures both wheel drives for velocity control with zero stiffness,
a nonzero implicit-drive damping gain, the `4.72 rad/s` wheel-speed limit, and
the `0.980665 N m` effort limit. The drive-cylinder contact material has rubber
traction, while the two chassis-attached caster proxy spheres use near-zero
friction to approximate freely rolling/swiveling rear casters instead of
braking the base.

Add a Physics Ground Plane at `Z = 0`, start Isaac Sim with the ROS 2 bridge
enabled, open `klara.usd`, and press **Play**. Then send a forward command from
a sourced ROS 2 terminal:

```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.15}, angular: {z: 0.0}}"
```

Stop it with `Ctrl-C`, then publish one zero command:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

The graph clamps commands to `0.29972 m/s` linear speed, `1.33209 rad/s` yaw
speed, and `4.72 rad/s` at either wheel. The current `0.45 m` track preserves
the approved visual placement but still needs a physical axle-center
measurement before odometry is considered calibrated.

Use `--urdf` or `--output` to override either path; `--windowed` shows Isaac
Sim while the conversion runs. Add `--help` to the command above to list all
options without starting Isaac Sim.

Convention:

- The URDF (and its meshes) in `klara_description` remain the single source of
  truth for robot geometry. Never hand-edit kinematics in USD; fix the URDF
  and re-convert.
- Convert with this script and Isaac Sim 6.0.1; note the Isaac Sim version
  used in the commit message.
- Commit converted USD here if it stays small (a few MB); larger scene assets
  go to `data/` (gitignored) with a download note here.
- Joint drive gains / physics tuning applied on top of the import are scripted
  in `configure_diffdrive.py` and are experiment-relevant: record changes in
  the commit history, since sim fidelity is a defensible-question topic.
