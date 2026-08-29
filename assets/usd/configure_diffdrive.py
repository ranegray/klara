#!/usr/bin/env python3
"""Add ROS 2 differential-drive control to the generated Klara USD.

Run with Isaac Sim's Python launcher after importing the URDF::

    <isaac-sim>/python.sh assets/usd/configure_diffdrive.py

The authored ActionGraph consumes ``geometry_msgs/msg/Twist`` messages from
``/cmd_vel`` and sends left/right wheel velocity targets to Isaac's
Articulation Controller.  Geometry constants match ``xlerobot.urdf``.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


DEFAULT_USD = Path(__file__).resolve().with_name("klara.usd")
ROBOT_PRIM = "/xlerobot"
ARTICULATION_ROOT = f"{ROBOT_PRIM}/Geometry/world/chassis"
GRAPH_PATH = f"{ROBOT_PRIM}/Graphs/cmd_vel"
LEFT_WHEEL_JOINT = f"{ROBOT_PRIM}/Physics/left_wheel_joint"
RIGHT_WHEEL_JOINT = f"{ROBOT_PRIM}/Physics/right_wheel_joint"

WHEEL_JOINT_NAMES = ["left_wheel_joint", "right_wheel_joint"]
WHEEL_RADIUS_M = 0.0635
WHEEL_DISTANCE_M = 0.45
MAX_WHEEL_SPEED_RAD_S = 4.72
MAX_LINEAR_SPEED_M_S = WHEEL_RADIUS_M * MAX_WHEEL_SPEED_RAD_S
MAX_ANGULAR_SPEED_RAD_S = 2.0 * MAX_LINEAR_SPEED_M_S / WHEEL_DISTANCE_M
MAX_WHEEL_EFFORT_N_M = 0.980665
WHEEL_STATIC_FRICTION = 1.0
WHEEL_DYNAMIC_FRICTION = 0.8
CASTER_STATIC_FRICTION = 0.001
CASTER_DYNAMIC_FRICTION = 0.001

# This is an Isaac implicit velocity-servo gain, not passive wheel friction.
# NVIDIA's articulated-wheel tutorial uses 1e4 for velocity-controlled wheels.
VELOCITY_DRIVE_DAMPING = 1.0e4

REQUIRED_EXTENSIONS = (
    "isaacsim.core.nodes",
    "isaacsim.robot.wheeled_robots.nodes",
    "isaacsim.ros2.bridge",
    "omni.graph.nodes",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add a ROS 2 /cmd_vel differential-drive ActionGraph to Klara USD."
    )
    parser.add_argument(
        "--usd",
        type=Path,
        default=DEFAULT_USD,
        help=f"USD to update (default: {DEFAULT_USD})",
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="show the Isaac Sim window while configuring (headless by default)",
    )
    return parser.parse_args()


def require_prim(stage: object, path: str) -> object:
    prim = stage.GetPrimAtPath(path)
    if not prim.IsValid():
        raise RuntimeError(f"required USD prim is missing: {path}")
    return prim


def configure_wheel_drives(stage: object) -> None:
    from pxr import UsdPhysics

    for joint_path in (LEFT_WHEEL_JOINT, RIGHT_WHEEL_JOINT):
        joint_prim = require_prim(stage, joint_path)
        drive = UsdPhysics.DriveAPI.Get(joint_prim, "angular")
        if not drive:
            drive = UsdPhysics.DriveAPI.Apply(joint_prim, "angular")
        drive.GetStiffnessAttr().Set(0.0)
        drive.GetDampingAttr().Set(VELOCITY_DRIVE_DAMPING)
        drive.GetMaxForceAttr().Set(MAX_WHEEL_EFFORT_N_M)
        drive.GetTargetVelocityAttr().Set(0.0)


def create_physics_material(
    stage: object,
    path: str,
    static_friction: float,
    dynamic_friction: float,
) -> object:
    from pxr import UsdPhysics, UsdShade

    material = UsdShade.Material.Define(stage, path)
    physics_material = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
    physics_material.CreateStaticFrictionAttr().Set(static_friction)
    physics_material.CreateDynamicFrictionAttr().Set(dynamic_friction)
    physics_material.CreateRestitutionAttr().Set(0.0)
    return material


def configure_contact_materials(stage: object) -> None:
    """Give the drive tires traction and let fixed caster proxies slide.

    The rear caster wheels are intentionally simplified as chassis-attached
    spheres. Near-zero friction approximates free rolling/swiveling without
    making those proxies brake differential-drive motion.
    """
    from pxr import UsdGeom, UsdShade

    wheel_material = create_physics_material(
        stage,
        f"{ROBOT_PRIM}/Physics/Materials/drive_tire",
        WHEEL_STATIC_FRICTION,
        WHEEL_DYNAMIC_FRICTION,
    )
    caster_material = create_physics_material(
        stage,
        f"{ROBOT_PRIM}/Physics/Materials/rear_caster_proxy",
        CASTER_STATIC_FRICTION,
        CASTER_DYNAMIC_FRICTION,
    )

    wheel_colliders = []
    caster_colliders = []
    for prim in stage.Traverse():
        prim_path = str(prim.GetPath())
        if prim.IsA(UsdGeom.Cylinder) and (
            prim_path.startswith(f"{ARTICULATION_ROOT}/left_wheel/")
            or prim_path.startswith(f"{ARTICULATION_ROOT}/right_wheel/")
        ):
            wheel_colliders.append(prim)
        elif prim.IsA(UsdGeom.Sphere) and prim_path.startswith(f"{ARTICULATION_ROOT}/"):
            caster_colliders.append(prim)

    if len(wheel_colliders) != 2:
        raise RuntimeError(f"expected 2 wheel cylinder colliders, found {len(wheel_colliders)}")
    if len(caster_colliders) != 2:
        raise RuntimeError(
            f"expected 2 rear caster sphere colliders, found {len(caster_colliders)}"
        )

    for collider in wheel_colliders:
        UsdShade.MaterialBindingAPI.Apply(collider).Bind(
            wheel_material,
            materialPurpose="physics",
        )
    for collider in caster_colliders:
        UsdShade.MaterialBindingAPI.Apply(collider).Bind(
            caster_material,
            materialPurpose="physics",
        )


def configure_cmd_vel_graph(stage: object) -> None:
    import omni.graph.core as og
    from pxr import Sdf, UsdPhysics

    articulation_prim = require_prim(stage, ARTICULATION_ROOT)
    if not articulation_prim.HasAPI(UsdPhysics.ArticulationRootAPI):
        raise RuntimeError(f"prim is not an articulation root: {ARTICULATION_ROOT}")
    require_prim(stage, LEFT_WHEEL_JOINT)
    require_prim(stage, RIGHT_WHEEL_JOINT)

    if stage.GetPrimAtPath(GRAPH_PATH).IsValid():
        stage.RemovePrim(GRAPH_PATH)

    keys = og.Controller.Keys
    og.Controller.edit(
        {"graph_path": GRAPH_PATH, "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: [
                ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
                ("Context", "isaacsim.ros2.bridge.ROS2Context"),
                ("SubscribeTwist", "isaacsim.ros2.bridge.ROS2SubscribeTwist"),
                ("BreakLinearVelocity", "omni.graph.nodes.BreakVector3"),
                ("BreakAngularVelocity", "omni.graph.nodes.BreakVector3"),
                (
                    "DifferentialController",
                    "isaacsim.robot.wheeled_robots.DifferentialController",
                ),
                ("ArticulationController", "isaacsim.core.nodes.IsaacArticulationController"),
            ],
            keys.SET_VALUES: [
                ("SubscribeTwist.inputs:topicName", "/cmd_vel"),
                ("DifferentialController.inputs:wheelRadius", WHEEL_RADIUS_M),
                ("DifferentialController.inputs:wheelDistance", WHEEL_DISTANCE_M),
                ("DifferentialController.inputs:maxWheelSpeed", MAX_WHEEL_SPEED_RAD_S),
                ("DifferentialController.inputs:maxLinearSpeed", MAX_LINEAR_SPEED_M_S),
                ("DifferentialController.inputs:maxAngularSpeed", MAX_ANGULAR_SPEED_RAD_S),
                ("ArticulationController.inputs:jointNames", WHEEL_JOINT_NAMES),
                ("ArticulationController.inputs:targetPrim", [Sdf.Path(ARTICULATION_ROOT)]),
            ],
            keys.CONNECT: [
                ("OnPlaybackTick.outputs:tick", "SubscribeTwist.inputs:execIn"),
                ("OnPlaybackTick.outputs:deltaSeconds", "DifferentialController.inputs:dt"),
                ("SubscribeTwist.outputs:execOut", "DifferentialController.inputs:execIn"),
                (
                    "SubscribeTwist.outputs:linearVelocity",
                    "BreakLinearVelocity.inputs:tuple",
                ),
                (
                    "BreakLinearVelocity.outputs:x",
                    "DifferentialController.inputs:linearVelocity",
                ),
                (
                    "SubscribeTwist.outputs:angularVelocity",
                    "BreakAngularVelocity.inputs:tuple",
                ),
                (
                    "BreakAngularVelocity.outputs:z",
                    "DifferentialController.inputs:angularVelocity",
                ),
                (
                    "DifferentialController.outputs:velocityCommand",
                    "ArticulationController.inputs:velocityCommand",
                ),
                ("OnPlaybackTick.outputs:tick", "ArticulationController.inputs:execIn"),
                ("Context.outputs:context", "SubscribeTwist.inputs:context"),
            ],
        },
    )


def export_stage_atomically(stage: object, usd_path: Path) -> None:
    with tempfile.NamedTemporaryFile(
        dir=usd_path.parent,
        prefix=f".{usd_path.stem}.",
        suffix=usd_path.suffix,
        delete=False,
    ) as temporary_output:
        temporary_path = Path(temporary_output.name)
    try:
        if not stage.GetRootLayer().Export(str(temporary_path)):
            raise RuntimeError(f"failed to export configured USD to {temporary_path}")
        os.replace(temporary_path, usd_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def configure_usd(usd_path: Path, windowed: bool) -> None:
    if not usd_path.is_file():
        raise ValueError(f"USD does not exist: {usd_path}")

    try:
        from isaacsim.simulation_app import SimulationApp
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Isaac Sim is not available. Run this script with Isaac Sim's ./python.sh."
        ) from error

    simulation_app = SimulationApp({"headless": not windowed})
    try:
        import omni.kit.app
        import omni.usd

        extension_manager = omni.kit.app.get_app().get_extension_manager()
        for extension in REQUIRED_EXTENSIONS:
            if not extension_manager.is_extension_enabled(extension):
                extension_manager.set_extension_enabled_immediate(extension, True)
                simulation_app.update()

        context = omni.usd.get_context()
        if not context.open_stage(str(usd_path)):
            raise RuntimeError(f"Isaac Sim could not open USD: {usd_path}")
        simulation_app.update()
        stage = context.get_stage()
        if stage is None:
            raise RuntimeError(f"Isaac Sim did not create a stage for: {usd_path}")

        configure_wheel_drives(stage)
        configure_contact_materials(stage)
        configure_cmd_vel_graph(stage)
        export_stage_atomically(stage, usd_path)
        print(f"Configured ROS 2 differential drive in {usd_path}", flush=True)
        print(
            f"/cmd_vel -> {WHEEL_JOINT_NAMES}; radius={WHEEL_RADIUS_M} m, "
            f"track={WHEEL_DISTANCE_M} m",
            flush=True,
        )
    finally:
        simulation_app.close()


def main() -> int:
    args = parse_args()
    usd_path = args.usd.expanduser().resolve()
    try:
        configure_usd(usd_path, args.windowed)
    except (RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
