"""Render a previously validated ShotLayout using Blender's Python."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def xyz(value: dict) -> tuple:
    return value["x"], value["y"], value["z"]


def linear_color(hex_color: str) -> tuple:
    channels = [
        int(hex_color[index:index + 2], 16) / 255
        for index in (1, 3, 5)
    ]
    return tuple(
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ) + (1.0,)


def add_object(spec: dict) -> None:
    builders = {
        "box": bpy.ops.mesh.primitive_cube_add,
        "ellipsoid": bpy.ops.mesh.primitive_uv_sphere_add,
        "cylinder": bpy.ops.mesh.primitive_cylinder_add,
    }
    builders[spec["shape"]]()
    obj = bpy.context.object
    obj.name = spec["object_id"]
    obj.dimensions = xyz(spec["dimensions"])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = xyz(spec["position"])
    obj.rotation_euler = tuple(
        math.radians(value) for value in xyz(spec["rotation_degrees"])
    )

    material = bpy.data.materials.new(f"{obj.name}_material")
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = linear_color(
        spec["material"]["color_hex"]
    )
    shader.inputs["Roughness"].default_value = spec["material"]["roughness"]
    shader.inputs["Metallic"].default_value = spec["material"]["metallic"]
    obj.data.materials.append(material)


def add_camera(spec: dict) -> None:
    bpy.ops.object.camera_add(location=xyz(spec["position"]))
    camera = bpy.context.object
    direction = Vector(xyz(spec["target"])) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = spec["focal_length_mm"]
    camera.data.sensor_width = 36
    camera.data.sensor_fit = "HORIZONTAL"
    camera.data.clip_start = 0.001
    bpy.context.scene.camera = camera


def render_layout(layout: dict, output: Path) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    for spec in layout["objects"]:
        add_object(spec)
    add_camera(layout["camera"])

    world = bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.15, 0.15, 0.15, 1.0
    )
    scene.world = world

    bpy.ops.object.light_add(type="AREA", location=(2.0, -3.0, 5.0))
    light = bpy.context.object
    light.data.energy = 500
    light.data.shape = "DISK"
    light.data.size = 4
    target = Vector(xyz(layout["camera"]["target"]))
    light.rotation_euler = (target - light.location).to_track_quat(
        "-Z", "Y"
    ).to_euler()

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("layout", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    layout = json.loads(args.layout.read_text(encoding="utf-8"))
    render_layout(layout, args.output.resolve())
