"""Automated tests for the color detector using synthetic images."""

import unittest

import cv2
import numpy as np

from color_detector import ColorDetector


class ColorDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = ColorDetector(min_area=100)

    def test_all_configured_colors_are_recognized(self) -> None:
        samples = {
            "Red": (0, 0, 255),
            "Orange": (0, 140, 255),
            "Yellow": (0, 255, 255),
            "Green": (0, 200, 0),
            "Cyan": (255, 255, 0),
            "Blue": (255, 0, 0),
            "Purple": (255, 0, 200),
        }

        for expected_name, bgr_color in samples.items():
            with self.subTest(color=expected_name):
                image = np.zeros((220, 280, 3), dtype=np.uint8)
                cv2.rectangle(image, (70, 50), (210, 180), bgr_color, -1)
                _, detections = self.detector.detect(image)
                detected_names = {item.color for item in detections}
                self.assertIn(expected_name, detected_names)

    def test_region_smaller_than_minimum_area_is_ignored(self) -> None:
        detector = ColorDetector(min_area=1_000)
        image = np.zeros((120, 120, 3), dtype=np.uint8)
        cv2.rectangle(image, (10, 10), (20, 20), (0, 0, 255), -1)

        _, detections = detector.detect(image)

        self.assertEqual(detections, [])

    def test_input_image_is_not_modified(self) -> None:
        image = np.zeros((120, 120, 3), dtype=np.uint8)
        cv2.rectangle(image, (20, 20), (100, 100), (255, 0, 0), -1)
        original = image.copy()

        self.detector.detect(image)

        self.assertTrue(np.array_equal(image, original))

    def test_invalid_frame_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty BGR image"):
            self.detector.detect(np.array([], dtype=np.uint8))

    def test_invalid_minimum_area_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            ColorDetector(min_area=0)


if __name__ == "__main__":
    unittest.main()
