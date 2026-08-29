#!/usr/bin/env python3
"""Assemble XLeRobot 0.4 wheelbase parts from the upstream print-bed STL.

The source STL contains 17 disconnected, print-oriented components. Eight of
those components make up the two dual-wheel hub and mount assemblies. This
script extracts those components, applies the placements from the upstream
``XLeRobot040_dualwheelbase.step`` assembly, and writes wheel-local meshes for
the Klara URDF. Coordinates remain in millimetres; the URDF applies a 0.001
scale when loading them.

The 5-inch walker tires are purchased parts and are therefore recreated as a
lightweight parametric visual mesh rather than extracted from this STL. Their
dimensions and six-spoke appearance follow the Zantle WW01 wheel shown in the
upstream assembly guide; the URDF retains a cylinder for collision physics.
"""

from __future__ import annotations

import math
import struct
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_STL = REPOSITORY_ROOT / "assets" / "XLeRobot_0_4_0_extra.stl"
OUTPUT_DIRECTORY = (
    REPOSITORY_ROOT
    / "ros2_ws"
    / "src"
    / "klara_description"
    / "meshes"
    / "xlerobot"
    / "assets"
)

TRIANGLE = struct.Struct("<12fH")
UINT32 = struct.Struct("<I")
EXPECTED_TRIANGLES = 218_100
ASSEMBLY_Y = 122.65
ASSEMBLY_Z = 823.14
LEFT_WHEEL_AXIS_X = -201.684890747
RIGHT_WHEEL_AXIS_X = -514.315315247
WHEEL_HALF_WIDTH = 11.835
WHEEL_SEGMENTS = 96

Vector = tuple[float, float, float]
Matrix = tuple[Vector, Vector, Vector]


@dataclass(frozen=True)
class Placement:
    component: str
    rotation: Matrix
    target_center: Vector


@dataclass
class Component:
    triangle_indices: list[int]
    center: Vector


PLACEMENTS = {
    "right_mount": Placement(
        "mount",
        ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
        (-406.5, 111.8125, 836.5),
    ),
    "left_mount": Placement(
        "mount",
        ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
        (-309.5, 111.8125, 836.5),
    ),
    "right_hub_inner": Placement(
        "thick_low_y",
        ((0.0, 0.0, 1.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0)),
        (-490.750030518, 122.650001526, 823.106628418),
    ),
    "left_hub_inner": Placement(
        "thick_high_y",
        ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
        (-225.249961853, 122.650001526, 823.106628418),
    ),
    "right_hub_outer": Placement(
        "thin_low_y",
        ((0.0, 0.0, 1.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0)),
        (-533.650878906, 122.650001526, 823.111083984),
    ),
    "left_hub_outer": Placement(
        "thin_high_y",
        ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
        (-182.349105835, 122.650001526, 823.111083984),
    ),
    "right_mount_clip": Placement(
        "clip_low_x",
        ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
        (-366.5, 67.283712387, 866.25),
    ),
    "left_mount_clip": Placement(
        "clip_high_x",
        ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
        (-349.5, 67.283712387, 866.25),
    ),
}


def read_binary_stl(path: Path) -> tuple[bytes, int]:
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"STL is too small: {path}")
    triangle_count = UINT32.unpack_from(data, 80)[0]
    expected_size = 84 + triangle_count * TRIANGLE.size
    if len(data) != expected_size:
        raise ValueError(f"expected {expected_size} bytes, found {len(data)}: {path}")
    if triangle_count != EXPECTED_TRIANGLES:
        raise ValueError(
            f"expected {EXPECTED_TRIANGLES} triangles, found {triangle_count}: {path}"
        )
    return data, triangle_count


def connected_components(data: bytes, triangle_count: int) -> list[list[int]]:
    parents = array("i", range(triangle_count))
    ranks = bytearray(triangle_count)

    def find(item: int) -> int:
        while parents[item] != item:
            parents[item] = parents[parents[item]]
            item = parents[item]
        return item

    def union(left: int, right: int) -> None:
        left = find(left)
        right = find(right)
        if left == right:
            return
        if ranks[left] < ranks[right]:
            left, right = right, left
        parents[right] = left
        if ranks[left] == ranks[right]:
            ranks[left] += 1

    vertex_owner: dict[bytes, int] = {}
    for triangle_index in range(triangle_count):
        offset = 84 + triangle_index * TRIANGLE.size + 12
        for vertex_offset in (0, 12, 24):
            vertex = data[offset + vertex_offset : offset + vertex_offset + 12]
            owner = vertex_owner.setdefault(vertex, triangle_index)
            union(triangle_index, owner)

    groups: dict[int, list[int]] = {}
    for triangle_index in range(triangle_count):
        groups.setdefault(find(triangle_index), []).append(triangle_index)
    return list(groups.values())


def component_center(data: bytes, triangle_indices: Iterable[int]) -> Vector:
    lower = [math.inf, math.inf, math.inf]
    upper = [-math.inf, -math.inf, -math.inf]
    for triangle_index in triangle_indices:
        values = TRIANGLE.unpack_from(data, 84 + triangle_index * TRIANGLE.size)
        for vertex in (values[3:6], values[6:9], values[9:12]):
            for axis, value in enumerate(vertex):
                lower[axis] = min(lower[axis], value)
                upper[axis] = max(upper[axis], value)
    return tuple((minimum + maximum) / 2.0 for minimum, maximum in zip(lower, upper))


def select_components(data: bytes, groups: list[list[int]]) -> dict[str, Component]:
    by_triangle_count: dict[int, list[Component]] = {}
    for triangle_indices in groups:
        component = Component(triangle_indices, component_center(data, triangle_indices))
        by_triangle_count.setdefault(len(triangle_indices), []).append(component)

    def require(count: int, copies: int) -> list[Component]:
        components = by_triangle_count.get(count, [])
        if len(components) != copies:
            raise ValueError(
                f"expected {copies} disconnected component(s) with {count} triangles, "
                f"found {len(components)}"
            )
        return components

    mount = require(16_556, 1)[0]
    thick = sorted(require(18_272, 2), key=lambda component: component.center[1])
    thin = sorted(require(7_852, 2), key=lambda component: component.center[1])
    clips = sorted(require(1_368, 2), key=lambda component: component.center[0])
    return {
        "mount": mount,
        "thick_low_y": thick[0],
        "thick_high_y": thick[1],
        "thin_low_y": thin[0],
        "thin_high_y": thin[1],
        "clip_low_x": clips[0],
        "clip_high_x": clips[1],
    }


def determinant(matrix: Matrix) -> float:
    (a, b, c), (d, e, f), (g, h, i) = matrix
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def multiply(matrix: Matrix, vector: Vector) -> Vector:
    return tuple(sum(row[axis] * vector[axis] for axis in range(3)) for row in matrix)


def subtract(left: Vector, right: Vector) -> Vector:
    return tuple(a - b for a, b in zip(left, right))


def add(left: Vector, right: Vector) -> Vector:
    return tuple(a + b for a, b in zip(left, right))


def wheel_local(point: Vector, wheel_axis_x: float) -> Vector:
    # Proper rotation from the upstream assembly frame into the wheel link:
    # STEP X (axle) -> link Z, STEP Z (up) -> link Y.
    return (ASSEMBLY_Y - point[1], point[2] - ASSEMBLY_Z, point[0] - wheel_axis_x)


def normal(vertices: tuple[Vector, Vector, Vector]) -> Vector:
    first = subtract(vertices[1], vertices[0])
    second = subtract(vertices[2], vertices[0])
    cross = (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )
    magnitude = math.sqrt(sum(value * value for value in cross))
    if magnitude == 0.0:
        return (0.0, 0.0, 0.0)
    return tuple(value / magnitude for value in cross)


def pack_triangle(vertices: tuple[Vector, Vector, Vector]) -> bytes:
    values = (*normal(vertices), *vertices[0], *vertices[1], *vertices[2], 0)
    return TRIANGLE.pack(*values)


def revolved_profile(profile: tuple[tuple[float, float], ...]) -> list[bytes]:
    """Revolve a closed (radius, z) profile around the wheel's local Z axis."""
    triangles: list[bytes] = []
    for segment in range(WHEEL_SEGMENTS):
        angle = 2.0 * math.pi * segment / WHEEL_SEGMENTS
        next_angle = 2.0 * math.pi * (segment + 1) / WHEEL_SEGMENTS
        for index, (radius, z) in enumerate(profile):
            next_radius, next_z = profile[(index + 1) % len(profile)]
            first = (radius * math.cos(angle), radius * math.sin(angle), z)
            second = (
                radius * math.cos(next_angle),
                radius * math.sin(next_angle),
                z,
            )
            third = (
                next_radius * math.cos(next_angle),
                next_radius * math.sin(next_angle),
                next_z,
            )
            fourth = (
                next_radius * math.cos(angle),
                next_radius * math.sin(angle),
                next_z,
            )
            triangles.append(pack_triangle((first, second, third)))
            triangles.append(pack_triangle((first, third, fourth)))
    return triangles


def annular_cylinder(
    inner_radius: float,
    outer_radius: float,
    half_width: float,
) -> list[bytes]:
    return revolved_profile(
        (
            (inner_radius, -half_width),
            (outer_radius, -half_width),
            (outer_radius, half_width),
            (inner_radius, half_width),
        )
    )


def spoke_prism(angle: float) -> list[bytes]:
    """Create one tapered spoke as a closed prism in wheel-local coordinates."""
    radial = (math.cos(angle), math.sin(angle))
    tangent = (-math.sin(angle), math.cos(angle))

    def point(radius: float, tangent_offset: float, z: float) -> Vector:
        return (
            radial[0] * radius + tangent[0] * tangent_offset,
            radial[1] * radius + tangent[1] * tangent_offset,
            z,
        )

    vertices = (
        point(9.5, -4.3, -5.5),
        point(9.5, 4.3, -5.5),
        point(49.0, 6.0, -5.5),
        point(49.0, -6.0, -5.5),
        point(9.5, -4.3, 5.5),
        point(9.5, 4.3, 5.5),
        point(49.0, 6.0, 5.5),
        point(49.0, -6.0, 5.5),
    )
    faces = (
        (0, 3, 2),
        (0, 2, 1),
        (4, 5, 6),
        (4, 6, 7),
        (0, 1, 5),
        (0, 5, 4),
        (1, 2, 6),
        (1, 6, 5),
        (2, 3, 7),
        (2, 7, 6),
        (3, 0, 4),
        (3, 4, 7),
    )
    return [pack_triangle(tuple(vertices[index] for index in face)) for face in faces]


def walker_tire() -> list[bytes]:
    # Rounded solid-rubber tread with the 127 mm outside diameter of the WW01.
    return revolved_profile(
        (
            (51.5, -8.2),
            (52.3, -10.0),
            (55.5, -WHEEL_HALF_WIDTH),
            (60.5, -WHEEL_HALF_WIDTH),
            (62.8, -9.4),
            (63.5, -5.0),
            (63.5, 5.0),
            (62.8, 9.4),
            (60.5, WHEEL_HALF_WIDTH),
            (55.5, WHEEL_HALF_WIDTH),
            (52.3, 10.0),
            (51.5, 8.2),
        )
    )


def walker_core() -> list[bytes]:
    triangles = annular_cylinder(47.0, 52.2, 7.0)
    triangles.extend(annular_cylinder(4.2, 12.0, 8.5))
    for spoke in range(6):
        triangles.extend(spoke_prism(2.0 * math.pi * spoke / 6.0))
    return triangles


def transformed_triangles(
    data: bytes,
    component: Component,
    placement: Placement,
    wheel_axis_x: float,
) -> list[bytes]:
    reflected = determinant(placement.rotation) < 0.0
    output: list[bytes] = []
    for triangle_index in component.triangle_indices:
        values = TRIANGLE.unpack_from(data, 84 + triangle_index * TRIANGLE.size)
        source_vertices = (values[3:6], values[6:9], values[9:12])
        target_vertices = []
        for source_vertex in source_vertices:
            centered = subtract(source_vertex, component.center)
            assembled = add(multiply(placement.rotation, centered), placement.target_center)
            target_vertices.append(wheel_local(assembled, wheel_axis_x))
        if reflected:
            target_vertices[1], target_vertices[2] = target_vertices[2], target_vertices[1]
        output.append(pack_triangle(tuple(target_vertices)))
    return output


def write_stl(path: Path, triangles: list[bytes]) -> None:
    label = f"Klara XLeRobot dual wheel: {path.stem}".encode("ascii")[:80]
    header = label.ljust(80, b"\0")
    path.write_bytes(header + UINT32.pack(len(triangles)) + b"".join(triangles))


def build_mesh(
    data: bytes,
    components: dict[str, Component],
    placement_names: tuple[str, ...],
    wheel_axis_x: float,
) -> list[bytes]:
    triangles: list[bytes] = []
    for placement_name in placement_names:
        placement = PLACEMENTS[placement_name]
        triangles.extend(
            transformed_triangles(
                data,
                components[placement.component],
                placement,
                wheel_axis_x,
            )
        )
    return triangles


def main() -> None:
    data, triangle_count = read_binary_stl(SOURCE_STL)
    components = select_components(data, connected_components(data, triangle_count))
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    outputs = {
        "dual_wheel_left_hub.stl": build_mesh(
            data,
            components,
            ("left_hub_inner", "left_hub_outer"),
            LEFT_WHEEL_AXIS_X,
        ),
        "dual_wheel_right_hub.stl": build_mesh(
            data,
            components,
            ("right_hub_inner", "right_hub_outer"),
            RIGHT_WHEEL_AXIS_X,
        ),
        "dual_wheel_left_mount.stl": build_mesh(
            data,
            components,
            ("left_mount", "left_mount_clip"),
            LEFT_WHEEL_AXIS_X,
        ),
        "dual_wheel_right_mount.stl": build_mesh(
            data,
            components,
            ("right_mount", "right_mount_clip"),
            RIGHT_WHEEL_AXIS_X,
        ),
        "dual_wheel_tire.stl": walker_tire(),
        "dual_wheel_core.stl": walker_core(),
    }
    for filename, triangles in outputs.items():
        path = OUTPUT_DIRECTORY / filename
        write_stl(path, triangles)
        print(f"wrote {path.relative_to(REPOSITORY_ROOT)} ({len(triangles)} triangles)")


if __name__ == "__main__":
    main()
