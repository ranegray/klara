# USD assets

Isaac Sim USD for the XLeRobot, converted from the source-of-truth URDF in
[`ros2_ws/src/klara_description/urdf/`](../../ros2_ws/src/klara_description/urdf/).

Convention:

- The URDF (and its meshes) in `klara_description` remain the single source of
  truth for robot geometry. Never hand-edit kinematics in USD; fix the URDF
  and re-convert.
- Convert with Isaac Sim's URDF importer; note the Isaac Sim version used in
  the commit message.
- Commit converted USD here if it stays small (a few MB); larger scene assets
  go to `data/` (gitignored) with a download note here.
- Joint drive gains / physics tuning applied on top of the import live here in
  USD and are experiment-relevant: record changes in the commit history, since
  sim fidelity is a defensible-question topic.
