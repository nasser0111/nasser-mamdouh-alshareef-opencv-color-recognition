"""Run real-time or still-image color recognition with OpenCV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

from color_detector import ColorDetector, Detection

PROJECT_AUTHOR = "Nasser Mamdouh Alshareef"
WINDOW_TITLE = f"OpenCV Color Recognition | {PROJECT_AUTHOR} | Q/ESC: Exit"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recognize red, orange, yellow, green, cyan, blue, and purple "
            "objects using OpenCV and HSV color masks."
        )
    )
    parser.add_argument(
        "--image",
        type=Path,
        help="Process one image instead of opening the webcam.",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Webcam index for live mode (default: 0).",
    )
    parser.add_argument(
        "--min-area",
        type=float,
        default=1_000.0,
        help="Ignore colored regions smaller than this pixel area (default: 1000).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save the annotated result. In camera mode, press S to save a frame.",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Do not open a window (intended for still-image/automated runs).",
    )
    parser.add_argument(
        "--no-mirror",
        action="store_true",
        help="Do not horizontally mirror the live webcam image.",
    )
    return parser


def print_detections(detections: list[Detection]) -> None:
    if not detections:
        print("No colored object was detected.")
        return

    print(f"Detected {len(detections)} colored object(s):")
    for index, detection in enumerate(detections, start=1):
        print(
            f"  {index}. {detection.color}: "
            f"center=({detection.center_x}, {detection.center_y}), "
            f"area={detection.area:.0f}"
        )


def save_image(path: Path, image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise OSError(f"OpenCV could not save the output image: {path}")
    print(f"Saved result to: {path.resolve()}")


def run_image_mode(
    detector: ColorDetector,
    image_path: Path,
    output_path: Path | None,
    no_display: bool,
) -> int:
    if not image_path.is_file():
        raise FileNotFoundError(f"Input image was not found: {image_path}")

    frame = cv2.imread(str(image_path))
    if frame is None:
        raise ValueError(f"The input file is not a readable image: {image_path}")

    annotated, detections = detector.detect(frame)
    print_detections(detections)

    if output_path is not None:
        save_image(output_path, annotated)

    if not no_display:
        cv2.imshow(WINDOW_TITLE, annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return 0


def run_camera_mode(
    detector: ColorDetector,
    camera_index: int,
    output_path: Path | None,
    no_display: bool,
    mirror: bool,
) -> int:
    if no_display:
        raise ValueError("--no-display can only be used together with --image")

    camera = cv2.VideoCapture(camera_index)
    if not camera.isOpened():
        camera.release()
        raise OSError(
            f"Could not open camera {camera_index}. Check camera permissions or "
            "try --camera 1."
        )

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("Camera started. Press Q or ESC to exit; press S to save a frame.")
    saved_once = False

    try:
        while True:
            success, frame = camera.read()
            if not success:
                raise OSError("The camera opened, but a frame could not be read.")

            if mirror:
                frame = cv2.flip(frame, 1)

            annotated, detections = detector.detect(frame)
            status = f"Objects: {len(detections)} | Q/ESC: Exit | S: Save"
            cv2.putText(
                annotated,
                status,
                (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(WINDOW_TITLE, annotated)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("s"):
                chosen_path = output_path or Path("captured_result.jpg")
                save_image(chosen_path, annotated)
                saved_once = True
    finally:
        camera.release()
        cv2.destroyAllWindows()

    if output_path is not None and not saved_once:
        print("No image was saved because S was not pressed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"Project prepared by: {PROJECT_AUTHOR}")

    try:
        detector = ColorDetector(min_area=args.min_area)
        if args.image is not None:
            return run_image_mode(
                detector,
                image_path=args.image,
                output_path=args.output,
                no_display=args.no_display,
            )

        return run_camera_mode(
            detector,
            camera_index=args.camera,
            output_path=args.output,
            no_display=args.no_display,
            mirror=not args.no_mirror,
        )
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
