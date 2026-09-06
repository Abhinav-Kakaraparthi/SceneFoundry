"""Deterministic open-hand geometry for blocking previews."""

from math import cos, radians, sin

from scenefoundry.domain.objects import Dimensions, VisualObject
from scenefoundry.domain.spatial import Vector3


def world_position(
    offset: tuple[float, float, float],
    source: VisualObject,
) -> Vector3:
    """Apply XYZ Euler rotation to a local offset, then translate."""
    x, y, z = offset
    rx, ry, rz = map(radians, source.rotation_degrees.as_tuple())
    y, z = y * cos(rx) - z * sin(rx), y * sin(rx) + z * cos(rx)
    x, z = x * cos(ry) + z * sin(ry), -x * sin(ry) + z * cos(ry)
    x, y = x * cos(rz) - y * sin(rz), x * sin(rz) + y * cos(rz)
    return Vector3(
        x=source.position.x + x,
        y=source.position.y + y,
        z=source.position.z + z,
    )


def build_hand_proxy(source: VisualObject) -> tuple[VisualObject, ...]:
    """Fit an open hand inside the source's local dimensions.

    Fingers point toward local -Y; the wrist attaches at +Y.
    The thumb lies on +X. This proxy has no joints or animation.
    """
    width = source.dimensions.x
    length = source.dimensions.y
    thickness = source.dimensions.z

    parts = [
        ("palm", (0.0, 0.175, 0.0), (0.76, 0.65, 1.0)),
        ("thumb", (0.40, 0.06, 0.0), (0.20, 0.40, 0.70)),
    ]
    for index, (x, reach) in enumerate(
        ((-0.27, 0.42), (-0.09, 0.50), (0.09, 0.46), (0.27, 0.36)),
        start=1,
    ):
        parts.append((
            f"finger_{index}",
            (x, -reach / 2, 0.0),
            (0.14, reach, 0.75),
        ))

    return tuple(
        VisualObject(
            object_id=f"{source.object_id}_{name}",
            shape="ellipsoid",
            dimensions=Dimensions(
                x=size[0] * width,
                y=size[1] * length,
                z=size[2] * thickness,
            ),
            position=world_position(
                (center[0] * width, center[1] * length, center[2] * thickness),
                source,
            ),
            rotation_degrees=source.rotation_degrees,
            material=source.material,
        )
        for name, center, size in parts
    )
