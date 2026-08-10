# Foxglove layouts

Versioned Foxglove layouts (export from Foxglove: Layout menu → Export). One
JSON per purpose:

- `episode-live.json` — watch a run: camera, scene, primitive calls, turn log
- `episode-debug.json` — post-hoc MCAP inspection: joint commands vs. reached
  positions (the stressor is visible here), failure traces

Data sources:
- Hardware: `foxglove_bridge` on the robot, or rosbag2 MCAP recordings.
- Isaac: MCAP written by the sweep runner (episode traces), opened directly in
  Foxglove.

Layouts are shared team config — commit changes, don't hoard local copies.
