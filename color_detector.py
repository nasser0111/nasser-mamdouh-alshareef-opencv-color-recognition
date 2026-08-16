"""Reusable OpenCV color-detection logic.

The detector converts a BGR image to HSV, builds one mask for each configured
color, cleans the masks, and returns every region larger than ``min_area``.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class HSVInterval:
    """Inclusive lower and upper HSV bounds used by ``cv2.inRange``."""

    lower: tuple[int, int, int]
    upper: tuple[int, int, int]


@dataclass(frozen=True)
class ColorProfile:
    """Configuration for one recognized color."""

    name: str
    intervals: tuple[HSVInterval, ...]
    box_color_bgr: tuple[int, int, int]


@dataclass(frozen=True)
class Detection:
    """A detected colored region."""

    color: str
    x: int
    y: int
    width: int
    height: int
    center_x: int
    center_y: int
    area: float


# OpenCV stores hue in the range 0..179. Red needs two intervals because the
# hue scale wraps around at both ends.
DEFAULT_COLOR_PROFILES: tuple[ColorProfile, ...] = (
    ColorProfile(
        "Red",
        (
            HSVInterval((0, 90, 70), (9, 255, 255)),
            HSVInterval((170, 90, 70), (179, 255, 255)),
        ),
        (0, 0, 255),
    ),
    ColorProfile(
        "Orange",
        (HSVInterval((10, 90, 70), (20, 255, 255)),),
        (0, 140, 255),
    ),
    ColorProfile(
        "Yellow",
        (HSVInterval((21, 90, 70), (34, 255, 255)),),
        (0, 255, 255),
    ),
    ColorProfile(
        "Green",
        (HSVInterval((35, 70, 60), (84, 255, 255)),),
        (0, 200, 0),
    ),
    ColorProfile(
        "Cyan",
        (HSVInterval((85, 70, 60), (99, 255, 255)),),
        (255, 255, 0),
    ),
    ColorProfile(
        "Blue",
        (HSVInterval((100, 90, 60), (129, 255, 255)),),
        (255, 0, 0),
    ),
    ColorProfile(
        "Purple",
        (HSVInterval((130, 70, 60), (169, 255, 255)),),
        (255, 0, 200),
    ),
)


class ColorDetector:
    """Detect and annotate colored regions in BGR images."""

    def __init__(
        self,
        min_area: float = 1_000.0,
        profiles: tuple[ColorProfile, ...] = DEFAULT_COLOR_PROFILES,
    ) -> None:
        if min_area <= 0:
            raise ValueError("min_area must be greater than zero")
        if not profiles:
            raise ValueError("At least one color profile is required")

        self.min_area = float(min_area)
        self.profiles = profiles
        self._kernel = np.ones((5, 5), dtype=np.uint8)

    @staticmethod
    def _validate_frame(frame: np.ndarray) -> None:
        if not isinstance(frame, np.ndarray):
            raise TypeError("frame must be a NumPy array")
        if frame.size == 0 or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("frame must be a non-empty BGR image with 3 channels")

    def _mask_for_profile(
        self, hsv_frame: np.ndarray, profile: ColorProfile
    ) -> np.ndarray:
        combined_mask = np.zeros(hsv_frame.shape[:2], dtype=np.uint8)

        for interval in profile.intervals:
            lower = np.array(interval.lower, dtype=np.uint8)
            upper = np.array(interval.upper, dtype=np.uint8)
            interval_mask = cv2.inRange(hsv_frame, lower, upper)
            combined_mask = cv2.bitwise_or(combined_mask, interval_mask)

        # Opening removes isolated noise; closing fills small holes in objects.
        combined_mask = cv2.morphologyEx(
            combined_mask, cv2.MORPH_OPEN, self._kernel, iterations=1
        )
        combined_mask = cv2.morphologyEx(
            combined_mask, cv2.MORPH_CLOSE, self._kernel, iterations=2
        )
        return combined_mask

    @staticmethod
    def _draw_detection(
        image: np.ndarray, detection: Detection, box_color: tuple[int, int, int]
    ) -> None:
        x, y = detection.x, detection.y
        right = x + detection.width
        bottom = y + detection.height
        cv2.rectangle(image, (x, y), (right, bottom), box_color, 2)
        cv2.circle(
            image,
            (detection.center_x, detection.center_y),
            4,
            box_color,
            -1,
        )

        label = f"{detection.color} | area: {int(detection.area)}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.55
        thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(
            label, font, font_scale, thickness
        )

        label_top = max(0, y - text_height - baseline - 8)
        label_bottom = label_top + text_height + baseline + 8
        label_right = min(image.shape[1] - 1, x + text_width + 10)
        blue, green, red = box_color
        luminance = 0.114 * blue + 0.587 * green + 0.299 * red
        text_color = (0, 0, 0) if luminance >= 150 else (255, 255, 255)
        cv2.rectangle(
            image,
            (x, label_top),
            (label_right, label_bottom),
            box_color,
            -1,
        )
        cv2.putText(
            image,
            label,
            (x + 5, label_bottom - baseline - 4),
            font,
            font_scale,
            text_color,
            thickness,
            cv2.LINE_AA,
        )

    def detect(self, frame: np.ndarray) -> tuple[np.ndarray, list[Detection]]:
        """Return an annotated copy of ``frame`` and all color detections."""

        self._validate_frame(frame)

        annotated = frame.copy()
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        hsv_frame = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        detections_with_colors: list[
            tuple[Detection, tuple[int, int, int]]
        ] = []

        for profile in self.profiles:
            mask = self._mask_for_profile(hsv_frame, profile)
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for contour in contours:
                area = float(cv2.contourArea(contour))
                if area < self.min_area:
                    continue

                x, y, width, height = cv2.boundingRect(contour)
                detection = Detection(
                    color=profile.name,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    center_x=x + width // 2,
                    center_y=y + height // 2,
                    area=area,
                )
                detections_with_colors.append(
                    (detection, profile.box_color_bgr)
                )

        # Largest regions are listed first, which makes terminal output stable.
        detections_with_colors.sort(key=lambda item: item[0].area, reverse=True)
        for detection, box_color in detections_with_colors:
            self._draw_detection(annotated, detection, box_color)

        detections = [item[0] for item in detections_with_colors]
        return annotated, detections
