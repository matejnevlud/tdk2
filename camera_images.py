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

    all_entries = os.listdir(camera_dir)
    logger.info(
        "Scanning camera dir '%s' for PLC timestamp %s — found %d entries",
        camera_dir,
        plc_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"),
        len(all_entries),
    )

    best_path = None
    best_delta = None
    parsed_count = 0

    for entry in all_entries:
        entry_path = os.path.join(camera_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        dir_dt = parse_camera_dir_name(entry)
        if dir_dt is None:
            logger.info("  Skipping entry '%s' — cannot parse as timestamp", entry)
            continue
        parsed_count += 1
        delta = abs((dir_dt - plc_timestamp).total_seconds())
        logger.info(
            "  Dir '%s' -> %s  delta=%.4fs",
            entry,
            dir_dt.strftime("%Y-%m-%d %H:%M:%S.%f"),
            delta,
        )
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_path = entry_path

    if best_path is not None:
        logger.info(
            "  BEST MATCH: '%s' (delta=%.4fs) for PLC timestamp %s",
            os.path.basename(best_path),
            best_delta,
            plc_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"),
        )
        # Log contents of matched dir
        contents = os.listdir(best_path)
        logger.info("  Matched dir contains %d files: %s", len(contents), contents)
    else:
        logger.warning(
            "No matching camera dir found! Scanned %d entries, %d parseable dirs, "
            "PLC timestamp=%s, camera_dir='%s'",
            len(all_entries),
            parsed_count,
            plc_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"),
            camera_dir,
        )

    return best_path


def copy_position_image(camera_folder: str, position: int, dest_folder: str) -> bool:
    """Find and copy the POZ<position>_ image from camera_folder to dest_folder/images/.

    Returns True if an image was found and copied, False otherwise.
    """
    prefix = f"POZ{position}_"
    images_dir = os.path.join(dest_folder, "images")
    os.makedirs(images_dir, exist_ok=True)

    all_files = os.listdir(camera_folder)
    logger.info(
        "Looking for '%s*' in '%s' (%d files: %s)",
        prefix,
        camera_folder,
        len(all_files),
        all_files,
    )

    for filename in all_files:
        if filename.startswith(prefix) and os.path.isfile(
            os.path.join(camera_folder, filename)
        ):
            src = os.path.join(camera_folder, filename)
            dst = os.path.join(images_dir, filename)
            shutil.copy2(src, dst)
            logger.info(
                "Copied POZ%d image: '%s' -> '%s'", position, src, dst
            )
            return True

    logger.warning(
        "No file with prefix '%s' found in '%s'. Available files: %s",
        prefix,
        camera_folder,
        all_files,
    )
    return False
