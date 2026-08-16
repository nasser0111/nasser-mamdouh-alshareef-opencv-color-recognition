"""Generate reproducible sample and result images for the README."""

from pathlib import Path

import cv2
import numpy as np

from color_detector import ColorDetector


def main() -> None:
    assets_directory = Path(__file__).resolve().parent / "assets"
    assets_directory.mkdir(parents=True, exist_ok=True)

    canvas = np.full((520, 960, 3), (35, 35, 35), dtype=np.uint8)
    samples = (
        ("Red", (0, 0, 255)),
        ("Orange", (0, 140, 255)),
        ("Yellow", (0, 255, 255)),
        ("Green", (0, 200, 0)),
        ("Cyan", (255, 255, 0)),
        ("Blue", (255, 0, 0)),
        ("Purple", (255, 0, 200)),
    )

    for index, (name, color) in enumerate(samples):
        column = index % 4
        row = index // 4
        left = 50 + column * 225
        top = 55 + row * 225
        cv2.rectangle(canvas, (left, top), (left + 160, top + 145), color, -1)
        cv2.putText(
            canvas,
            name,
            (left + 28, top + 190),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (235, 235, 235),
            2,
            cv2.LINE_AA,
        )

    sample_path = assets_directory / "sample_input.png"
    result_path = assets_directory / "demo_result.png"
    if not cv2.imwrite(str(sample_path), canvas):
        raise OSError(f"Could not save {sample_path}")

    detector = ColorDetector(min_area=500)
    result, detections = detector.detect(canvas)
    if len(detections) != len(samples):
        raise RuntimeError(
            f"Demo validation failed: expected {len(samples)} detections, "
            f"received {len(detections)}"
        )
    if not cv2.imwrite(str(result_path), result):
        raise OSError(f"Could not save {result_path}")

    print(f"Created {sample_path}")
    print(f"Created {result_path}")
    print(f"Validated {len(detections)} color detections")


if __name__ == "__main__":
    main()
