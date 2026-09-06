"""Bake shot-local translations and render a PNG frame sequence."""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_layout import build_scene


def offset_at(keyframes: list[dict], frame: int) -> Vector:
    for left, right in zip(keyframes, keyframes[1:]):
        if left["frame"] <= frame <= right["frame"]:
            fraction = (frame - left["frame"]) / (right["frame"] - left["frame"])
            start = Vector(tuple(left["offset"][axis] for axis in ("x", "y", "z")))
            end = Vector(tuple(right["offset"][axis] for axis in ("x", "y", "z")))
            return start.lerp(end, fraction)
    raise ValueError(f"No motion segment covers frame {frame}.")


def render_animation(animation: dict, fps: int, output: Path) -> None:
    build_scene(animation["layout"])
    scene = bpy.context.scene
    timing = animation["shot"]["frames"]
    frame_count = timing["end"] - timing["start"]

    for track in animation["tracks"]:
        for object_id in track["object_ids"]:
            obj = bpy.data.objects[object_id]
            origin = obj.location.copy()
            for frame in range(frame_count):
                obj.location = origin + offset_at(track["keyframes"], frame)
                obj.keyframe_insert(data_path="location", frame=frame + 1)

    # Integer-frame baking preserves the specified linear samples.
    # Domain frame 0 maps to Blender frame 1.
    scene.frame_start = 1
    scene.frame_end = frame_count
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    output.mkdir(parents=True, exist_ok=False)
    scene.render.filepath = str(output / "frame_")
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    animation = json.loads(
        (args.directory / "animation.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (args.directory / "manifest.json").read_text(encoding="utf-8")
    )
    render_animation(animation, manifest["fps"], args.output.resolve())
