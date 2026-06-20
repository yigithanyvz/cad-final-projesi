#!/usr/bin/env python3
import math
import re
import sys
from pathlib import Path


def values():
    base_height = 0.25
    base_radius = 1.0
    base_mass = 1000.0
    platform_height = 0.1
    platform_radius = base_radius
    platform_mass = 1.0
    ball_radius = 0.1
    base_platform_distance = 2.0
    piston_radius = ball_radius

    ball_dtc = math.sqrt(
        base_radius**2 - 4 * base_radius * ball_radius + 5 * ball_radius**2
    )
    ball_separation = math.sqrt(
        2 * ball_dtc**2
        - 2
        * ball_dtc**2
        * math.cos(
            1.047
            - 2 * math.asin(ball_radius / (base_radius - 2 * ball_radius))
        )
    )
    distance_to_midpoint = math.sqrt(ball_dtc**2 - (0.5 * ball_separation) ** 2)
    piston_pitch_angle = 1.571 - math.atan(
        (base_platform_distance - 0.5 * base_height - 0.5 * platform_height)
        / ball_separation
    )
    piston_yaw_angle = 1.571 - (
        0.5
        * (
            3.142
            - (
                1.047
                - 2 * math.asin(ball_radius / (base_radius - 2 * ball_radius))
            )
        )
        - math.asin(ball_radius / (base_radius - 2 * ball_radius))
    )
    piston_length = math.sqrt(
        (base_platform_distance - 0.5 * base_height - 0.5 * platform_height) ** 2
        + ball_separation**2
    )

    return {
        "BASE_HEIGHT": base_height,
        "BASE_RADIUS": base_radius,
        "BASE_MASS": base_mass,
        "PLATFORM_HEIGHT": platform_height,
        "PLATFORM_RADIUS": platform_radius,
        "PLATFORM_MASS": platform_mass,
        "BASE_PLATFORM_DISTANCE": base_platform_distance,
        "BALL_RADIUS": ball_radius,
        "BALL_DTC": ball_dtc,
        "BALL_SEPARATION": ball_separation,
        "PISTON_RADIUS": piston_radius,
        "PISTON_PITCH_ANGLE": piston_pitch_angle,
        "PISTON_YAW_ANGLE": piston_yaw_angle,
        "DISTANCE_TO_MIDPOINT": distance_to_midpoint,
        "PISTON_LENGTH": piston_length,
    }


def main():
    if len(sys.argv) != 3:
        print("usage: render_model_sdf.py TEMPLATE OUTPUT", file=sys.stderr)
        return 2

    template_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    text = template_path.read_text()

    text = re.sub(r"<%.*?%>\s*", "", text, count=1, flags=re.DOTALL)
    replacements = values()

    class MathNamespace:
        sin = staticmethod(math.sin)
        cos = staticmethod(math.cos)
        asin = staticmethod(math.asin)
        atan = staticmethod(math.atan)
        sqrt = staticmethod(math.sqrt)

    eval_globals = {"__builtins__": {}, "Math": MathNamespace}
    eval_locals = replacements.copy()

    def replace(match):
        expression = match.group(1)
        try:
            value = eval(expression, eval_globals, eval_locals)
        except Exception as exc:
            raise RuntimeError(f"failed to evaluate ERB expression: {expression}") from exc
        return f"{value:.12g}"

    text = re.sub(r"<%=\s*(.*?)\s*%>", replace, text)
    text = re.sub(
        r"(<(?:radius|length)>\s*[-+0-9.eE]+)\"(\s*</(?:radius|length)>)",
        r"\1\2",
        text,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
