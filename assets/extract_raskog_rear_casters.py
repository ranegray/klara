#!/usr/bin/env python3
"""Extract the rear caster pair from the vendor RASKOG wheel meshes.

Each vendor wheel STL contains four disconnected components: one component for
each corner of the cart. In the vendor mesh frame, positive X is the rear of
the robot. This script retains the two positive-X components in each material
mesh and writes fixed rear-caster visuals for the default Klara URDF.
"""

from __future__ import annotations

import struct
from array import array
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MESH_DIRECTORY = (
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
SOURCES = {
    "raskogwheel1.stl": "raskog_rear_caster_hardware.stl",
    "raskogwheel2.stl": "raskog_rear_caster_tires.stl",
}


def read_stl(path: Path) -> tuple[bytes, int]:
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"STL is too small: {path}")
    count = UINT32.unpack_from(data, 80)[0]
    if len(data) != 84 + count * TRIANGLE.size:
        raise ValueError(f"invalid binary STL size: {path}")
    return data, count


def connected_components(data: bytes, count: int) -> list[list[int]]:
    parents = array("i", range(count))
    ranks = bytearray(count)

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
    for triangle_index in range(count):
        offset = 84 + triangle_index * TRIANGLE.size + 12
        for vertex_offset in (0, 12, 24):
            vertex = data[offset + vertex_offset : offset + vertex_offset + 12]
            owner = vertex_owner.setdefault(vertex, triangle_index)
            union(triangle_index, owner)

    groups: dict[int, list[int]] = {}
    for triangle_index in range(count):
        groups.setdefault(find(triangle_index), []).append(triangle_index)
    return list(groups.values())


def center_x(data: bytes, group: list[int]) -> float:
    lower = float("inf")
    upper = float("-inf")
    for triangle_index in group:
        values = TRIANGLE.unpack_from(data, 84 + triangle_index * TRIANGLE.size)
        for vertex in (values[3:6], values[6:9], values[9:12]):
            lower = min(lower, vertex[0])
            upper = max(upper, vertex[0])
    return (lower + upper) / 2.0


def extract_rear(source: Path, output: Path) -> tuple[int, int]:
    data, count = read_stl(source)
    groups = connected_components(data, count)
    if len(groups) != 4:
        raise ValueError(f"expected four caster components in {source}, found {len(groups)}")
    rear_groups = [group for group in groups if center_x(data, group) > 0.0]
    if len(rear_groups) != 2:
        raise ValueError(f"expected two rear caster components in {source}")
    indices = sorted(index for group in rear_groups for index in group)
    triangles = b"".join(
        data[84 + index * TRIANGLE.size : 84 + (index + 1) * TRIANGLE.size]
        for index in indices
    )
    label = f"Klara rear casters: {output.stem}".encode("ascii")[:80].ljust(80, b"\0")
    output.write_bytes(label + UINT32.pack(len(indices)) + triangles)
    return len(indices), count


def main() -> None:
    for source_name, output_name in SOURCES.items():
        output = MESH_DIRECTORY / output_name
        selected, total = extract_rear(MESH_DIRECTORY / source_name, output)
        print(
            f"wrote {output.relative_to(REPOSITORY_ROOT)} "
            f"({selected}/{total} triangles)"
        )


if __name__ == "__main__":
    main()
