"""Camera image matching and copying for the vision controller.

The camera creates timestamped directories containing images for 3 positions.
We match PLC position timestamps to the closest camera directory to find
which image belongs to which piece.
"""

import logging
import os
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_camera_dir_name(name: str) -> datetime | None:
    """Parse a camera directory name like '2026-02-10_11-06-39-1234' into a datetime.

    The format is YYYY-MM-DD_HH-MM-SS-NNNN where NNNN is sub-second precision.
    We convert the trailing digits to microseconds for comparison.
    """
    try:
        # Split off the sub-second part: "2026-02-10_11-06-39-1234"
        # The base is "2026-02-10_11-06-39", the tail is "1234"
        parts = name.rsplit("-", 1)
        if len(parts) != 2:
            return None
        base_str, frac_str = parts
        dt = datetime.strptime(base_str, "%Y-%m-%d_%H-%M-%S")
        # Pad or truncate fractional part to 6 digits (microseconds)
        frac_str = frac_str.ljust(6, "0")[:6]
        return dt.replace(microsecond=int(frac_str))
    except (ValueError, IndexError):
        return None


def find_closest_camera_dir(plc_timestamp: datetime, camera_dir: str) -> str | None:
    """Find the camera directory whose timestamp is closest to plc_timestamp.

    Scans all directories in camera_dir, parses their names as datetimes,
    and returns the path of the closest match. Returns None if no dirs found.
    """
    if not os.path.isdir(camera_dir):
        logger.warning("Camera directory does not exist: %s", camera_dir)
        return None

    best_path = None
    best_delta = None

    for entry in os.listdir(camera_dir):
        entry_path = os.path.join(camera_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        dir_dt = parse_camera_dir_name(entry)
        if dir_dt is None:
            continue
        delta = abs((dir_dt - plc_timestamp).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_path = entry_path

    if best_path is not None:
        logger.info(
            "Matched dir '%s' (delta=%.3fs)",
            os.path.basename(best_path),
            best_delta,
        )
    else:
        logger.warning("No camera dir matched for timestamp %s", plc_timestamp)

    return best_path


def copy_position_image(camera_folder: str, position: int, dest_folder: str) -> int:
    """Move all POZ<position> images from camera_folder to dest_folder/images/.

    Matches filenames starting with 'POZ<position>' (e.g. POZ3_, POZ3a_, POZ3b_).
    The source file is deleted after a successful copy.
    Returns the number of files moved.
    """
    prefix = f"POZ{position}"
    images_dir = os.path.join(dest_folder, "images")
    os.makedirs(images_dir, exist_ok=True)

    copied = 0
    for filename in os.listdir(camera_folder):
        if filename.startswith(prefix) and os.path.isfile(
            os.path.join(camera_folder, filename)
        ):
            shutil.copy2(
                os.path.join(camera_folder, filename),
                os.path.join(images_dir, filename),
            )
            os.remove(os.path.join(camera_folder, filename))
            logger.info("Moved %s", filename)
            copied += 1

    if copied == 0:
        logger.warning("No POZ%d file found in %s", position, os.path.basename(camera_folder))

    if copied > 0 and not os.listdir(camera_folder):
        os.rmdir(camera_folder)

    return copied
