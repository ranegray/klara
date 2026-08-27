#!/usr/bin/env python3
"""Import the klara_description URDF as a single Isaac Sim USD asset.

Run this script with Isaac Sim's Python launcher, not the repository's uv environment:

    <isaac-sim>/python.sh <repo>/assets/usd/import_klara.py

The default input is klara_description's parked-base ``xlerobot.urdf`` and
the default output is ``assets/usd/klara.usd``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DESCRIPTION_PACKAGE = REPOSITORY_ROOT / "ros2_ws" / "src" / "klara_description"
DEFAULT_URDF = DESCRIPTION_PACKAGE / "urdf" / "xlerobot.urdf"
DEFAULT_OUTPUT = Path(__file__).resolve().with_name("klara.usd")
IMPORTER_EXTENSION = "isaacsim.asset.importer.urdf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import klara_description's URDF into a single Isaac Sim USD file."
    )
    parser.add_argument(
        "--urdf",
        type=Path,
        default=DEFAULT_URDF,
        help=f"source URDF (default: {DEFAULT_URDF})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"destination .usd file (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace the output if it already exists",
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="show the Isaac Sim window while importing (headless by default)",
    )
    return parser.parse_args()


def validate_paths(urdf_path: Path, output_path: Path, force: bool) -> None:
    if not urdf_path.is_file():
        raise ValueError(f"URDF does not exist: {urdf_path}")
    if urdf_path.suffix.lower() != ".urdf":
        raise ValueError(f"URDF input must end in .urdf: {urdf_path}")
    if output_path.suffix.lower() != ".usd":
        raise ValueError(f"output must end in .usd: {output_path}")
    if output_path.exists() and not force:
        raise FileExistsError(f"output already exists: {output_path} (pass --force to replace it)")


def import_urdf(urdf_path: Path, output_path: Path, windowed: bool) -> None:
    """Run Isaac's importer and flatten its result into one portable USD file."""
    try:
        from isaacsim.simulation_app import SimulationApp
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Isaac Sim is not available. Run this script with Isaac Sim's ./python.sh."
        ) from error

    simulation_app = SimulationApp({"headless": not windowed})
    try:
        # Kit/Omniverse modules can only be imported after SimulationApp starts.
        import omni.kit.app

        extension_manager = omni.kit.app.get_app().get_extension_manager()
        if not extension_manager.is_extension_enabled(IMPORTER_EXTENSION):
            extension_manager.set_extension_enabled_immediate(IMPORTER_EXTENSION, True)
            simulation_app.update()

        from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig
        from pxr import Usd

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="klara_urdf_import_") as temporary_directory:
            temporary_root = Path(temporary_directory)

            # Importer 3.0 derives the USD asset name from the URDF filename.
            # Renaming only this temporary copy gives us klara.usda without
            # modifying the source-of-truth URDF or its robot/link names.
            staged_urdf = temporary_root / "klara.urdf"
            shutil.copy2(urdf_path, staged_urdf)

            import_config = URDFImporterConfig(
                urdf_path=str(staged_urdf),
                usd_path=str(temporary_root / "imported"),
                merge_fixed_joints=False,
                merge_mesh=False,
                collision_from_visuals=False,
                allow_self_collision=False,
                ros_package_paths=[
                    {"name": "klara_description", "path": str(DESCRIPTION_PACKAGE)}
                ],
                robot_type="Default",
                fix_base=None,
                run_asset_transformer=True,
                run_multi_physics_conversion=True,
            )
            generated_path = Path(URDFImporter(import_config).import_urdf())
            if not generated_path.is_file():
                raise RuntimeError(f"Isaac's URDF importer did not create {generated_path}")

            stage = Usd.Stage.Open(str(generated_path), load=Usd.Stage.LoadAll)
            if stage is None:
                raise RuntimeError(f"could not open imported USD stage: {generated_path}")

            # Importer 3.0 creates a multi-file Asset Structure 3.0 package.
            # Flatten it so the checked-in/runtime artifact is exactly klara.usd.
            flattened_layer = stage.Flatten()
            with tempfile.NamedTemporaryFile(
                dir=output_path.parent,
                prefix=f".{output_path.stem}.",
                suffix=".usd",
                delete=False,
            ) as temporary_output:
                temporary_output_path = Path(temporary_output.name)

            try:
                if not flattened_layer.Export(str(temporary_output_path)):
                    raise RuntimeError(f"failed to export flattened USD to {temporary_output_path}")
                os.replace(temporary_output_path, output_path)
                print(f"Imported {urdf_path}", flush=True)
                print(f"Wrote {output_path}", flush=True)
            finally:
                temporary_output_path.unlink(missing_ok=True)
    finally:
        simulation_app.close()


def main() -> int:
    args = parse_args()
    urdf_path = args.urdf.expanduser().resolve()
    output_path = args.output.expanduser().resolve()

    try:
        validate_paths(urdf_path, output_path, args.force)
        import_urdf(urdf_path, output_path, args.windowed)
    except (FileExistsError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
