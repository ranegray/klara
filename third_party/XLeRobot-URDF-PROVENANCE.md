# XLeRobot URDF Provenance

Imported on: 2026-04-26

Upstream project: [Vector-Wangel/XLeRobot](https://github.com/Vector-Wangel/XLeRobot)

Local upstream checkout: `/Users/ranegray/Development/robotics/XLeRobot`

Upstream commit used: `137865981ca9e828d0923804cf77ededd22c7816`

Original archive: `simulation/xlerobot_urdf.zip`

Imported files:

- `ros2_ws/src/xle_description/urdf/xlerobot_0_4_0_vendor.urdf`
- `ros2_ws/src/xle_description/urdf/xlerobot.urdf`
- `ros2_ws/src/xle_description/meshes/xlerobot/`

Import changes:

- Rewrote URDF mesh references from `meshes/xlerobot/assets/...` to `package://xle_description/meshes/xlerobot/assets/...` in both URDF files.
- Preserved `xlerobot_0_4_0_vendor.urdf` as the vendor URDF with no intentional joint edits.
- Made `xlerobot.urdf` the default parked-base ROS derivative by changing root `joint_0` from `floating` to `fixed`.
- Did not edit geometry, arm joints, inertial properties, collision meshes, limits, or frame names.

Later local geometry changes:

- On 2026-08-29, assembled the XLeRobot 0.4 dual-wheel hub and mount parts from
  `assets/XLeRobot_0_4_0_extra.stl` using placements from upstream
  `hardware/step/XLeRobot_040/XLeRobot040_dualwheelbase.step`.
- Added the derived meshes only to `urdf/xlerobot.urdf`; the vendor URDF remains
  unchanged.
- Recreated the separately purchased 5-inch Zantle WW01 walker tires as
  parametric 127 mm rounded-tire and six-spoke-core visual meshes. Their simple
  cylinder collisions remain aligned with the ground plane.
- After checkpoint commit `77fd3c7`, removed the two front RASKOG caster
  visuals while retaining the two rear casters for stability. The rear-only
  caster meshes are deterministic subsets of the unchanged vendor meshes.
- Omitted the printed drive-mount envelopes from the default model as
  visual-only geometry. Their generated meshes remain available, and no
  collision, inertial, wheel-joint, or drivetrain properties depend on them.
- Measured 312.630188 mm between selected hub interfaces and a 23.6716 mm tire
  gap in `XLeRobot040_dualwheelbase.step`. The former was initially mistaken
  for the installed wheel track, then rejected because the standalone STEP has
  no IKEA-cart datum. The cart-relative joint centers retain their visually
  verified 450 mm separation pending a direct physical axle-center measurement.
  The documented 5-inch wheel sets a 63.5 mm radius and axle height.
- Aligned the two rear caster sphere collisions with the retained vendor caster
  meshes and their ground-contact plane.
- The Isaac USD import forces a mobile base (`fix_base=False`) so the generated
  asset can function as a differential-drive articulation.
- The vendor URDF remains unchanged.

License handling:

- The upstream XLeRobot repository is licensed under Apache-2.0 at the checked commit.
- A local copy of the upstream license is stored at `third_party/XLeRobot-LICENSE`.

Verification notes:

- This import is ready for ROS package resolution.
- Runtime verification still requires a ROS 2 environment with `robot_state_publisher` and mesh loading tools available.
