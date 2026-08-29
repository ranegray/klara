# klara_description

`klara_description` contains the vendored XLeRobot 0.4.0 URDF and mesh assets used by this stack.

The model was imported from the upstream XLeRobot repository archive at `simulation/xlerobot_urdf.zip`. Mesh references in the copied URDF were rewritten from relative archive paths to ROS package URIs so `robot_state_publisher`, RViz, and downstream launch files can resolve them after installation.

URDF files:

- `urdf/xlerobot_0_4_0_vendor.urdf`: vendor import with ROS package mesh URIs and no intentional joint edits.
- `urdf/xlerobot.urdf`: Klara's XLeRobot 0.4 dual-wheel model. The checked-in
  Isaac USD importer explicitly makes its base mobile for differential-drive
  articulation.

## Dual-wheel geometry

The printable hubs and mounts are derived from
`assets/XLeRobot_0_4_0_extra.stl`, which stores its parts disconnected and in
print-bed orientation. Run the assembly script from the repository root to
regenerate the URDF-ready meshes:

```bash
python3 assets/assemble_xlerobot_dual_wheels.py
```

The part orientations come from the upstream `XLeRobot040_dualwheelbase.step`
assembly. That standalone assembly does not contain the IKEA cart and therefore
does not define a cart-relative axle placement. The source STL also does not
include the purchased 5-inch walker tires, so the script generates a 127 mm
rounded tire and six-spoke core matching the Zantle WW01 wheel used by the
upstream build. Hub, core, and tire visuals remain attached to `left_wheel` and
`right_wheel` so they rotate with the continuous joints. Tire collisions remain
simple cylinders for stable simulation physics.

Physical differential-drive dimensions:

- Wheel radius: `0.0635 m` (documented 5-inch outside diameter).
- Current cart-relative wheel-center separation/track: `0.45 m`, preserving the
  visually verified placement on the RASKOG base. Measure the physical robot
  axle-center to axle-center before treating this as a calibrated odometry
  value. The `0.312630188 m` spacing found between selected interfaces in the
  standalone STEP is not a valid cart-mounted track measurement.
- Tire axial width: `0.0236716 m` (the STEP gap between the inner and outer hub
  adapters).
- Inner tire gap: `0.288958588 m`; outside tire span: `0.336301788 m`.
- Axle height: `0.0635 m` above the ground plane.
- Wheel joint rated effort: `0.980665 N m`; maximum no-load speed:
  `4.72 rad/s`, based on the 12 V STS3215 rated torque and speed.

The `0.20 kg` rotating-wheel mass and inertia tensors are geometry/material
estimates. Weigh an assembled physical wheel (including both printed adapters)
and update these values before using torque response as a Sim-to-Real target.

The default parked-base model removes the two front RASKOG caster visuals and
retains the two rear casters for stability, matching the physical two-wheel
configuration. Run `python3 assets/extract_raskog_rear_casters.py` to recreate
the rear-only visual meshes from the vendor's four-caster meshes. The originals
remain in the package and in the untouched vendor URDF. The fixed printed
drive-mount envelopes are omitted from the default model because they are
cosmetic. The generated mount meshes remain available without contributing
collision, inertial, or joint behavior.

Provenance is tracked in [`third_party/XLeRobot-URDF-PROVENANCE.md`](../../../third_party/XLeRobot-URDF-PROVENANCE.md). The upstream license copy is stored at [`third_party/XLeRobot-LICENSE`](../../../third_party/XLeRobot-LICENSE).

## First Launch Target

```bash
cd ros2_ws
colcon build --symlink-install --packages-select klara_description
source install/setup.bash
ros2 launch klara_description view_robot.launch.py
```

This should publish `robot_description` and start `robot_state_publisher`. Fake or real joint state publication is handled by later packages.
