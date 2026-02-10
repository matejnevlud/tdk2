"""Entry point for the TDK2 traceability application.

Monitors a shared camera image folder and polls a Siemens PLC (DB90)
for measurement data, organizing everything by date and EAN code.
"""

import logging
import os
import signal
import sys
import time

from plc_reader import (
    connect_plc,
    parse_db90,
    read_db90,
    save_to_csv,
)
from camera_images import (
    copy_position_image,
    find_closest_camera_dir,
)

# ── Configuration ──────────────────────────────────────────────────────
PLC_IP = "192.168.11.1"
PLC_RACK = 0
PLC_SLOT = 1
POLL_INTERVAL = 1  # seconds
CAMERA_DIR = "C:\\Users\\TDK\\Desktop\\TDK2-Traceability-Portable-2\\ftp_incoming"
BASE_DIR = "X:\\"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

running = True


def handle_signal(sig, frame):
    global running
    logger.info("Shutdown requested (signal %d)", sig)
    running = False


def poll_loop(client):
    """Main polling loop: reads DB90, detects new pieces, saves data and images."""
    last_ean = None

    while running:
        try:
            data = read_db90(client)
            record = parse_db90(data)
            current_ean = record["ean"]

            if current_ean and current_ean != last_ean:
                logger.info("New piece detected: EAN=%s", current_ean)
                folder = save_to_csv(record, base_dir=BASE_DIR)
                logger.info("Data saved to %s/data.csv", folder)

                # Match and copy camera images for positions 1-3
                logger.info(
                    "Starting camera image matching for EAN=%s, dest='%s'",
                    current_ean,
                    folder,
                )
                for pos in range(1, 4):
                    pos_ts = record["positions"][pos - 1]["timestamp"]
                    if pos_ts is None:
                        logger.info(
                            "Position %d: no PLC timestamp available, skipping image match",
                            pos,
                        )
                        continue
                    logger.info(
                        "Position %d: PLC timestamp = %s, searching in '%s'",
                        pos,
                        pos_ts.strftime("%Y-%m-%d %H:%M:%S.%f"),
                        CAMERA_DIR,
                    )
                    cam_dir = find_closest_camera_dir(pos_ts, CAMERA_DIR)
                    if cam_dir:
                        count = copy_position_image(cam_dir, pos, folder)
                        if count:
                            logger.info("Position %d: %d image(s) copied successfully", pos, count)
                        else:
                            logger.warning("Position %d: matched dir but no POZ%d image found", pos, pos)
                    else:
                        logger.warning(
                            "Position %d: no camera directory matched for timestamp %s",
                            pos,
                            pos_ts.strftime("%Y-%m-%d %H:%M:%S.%f"),
                        )

                last_ean = current_ean

        except Exception:
            logger.exception("Error during PLC poll")

        # Sleep in small increments so we can respond to shutdown quickly
        for _ in range(int(POLL_INTERVAL * 10)):
            if not running:
                break
            time.sleep(0.1)


LOGO = """
  ＮＥＶＬＵＤ
  Ｉｎｄｕｓｔｒｉｅｓ

  TDK2 Traceability System v0.1.0
"""


def main():
    print(LOGO)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("Starting TDK2 Traceability Application")

    # Check output directory is accessible
    if not os.path.isdir(BASE_DIR):
        logger.error("Output directory %s does not exist or is not accessible!", BASE_DIR)
        sys.exit(1)

    # Check camera directory exists
    if not os.path.isdir(CAMERA_DIR):
        logger.error("Camera directory %s does not exist or is not accessible!", CAMERA_DIR)
        sys.exit(1)

    logger.info("Output directory: %s", BASE_DIR)
    logger.info("Camera directory: %s", CAMERA_DIR)
    logger.info("PLC: %s (rack=%d, slot=%d, DB90)", PLC_IP, PLC_RACK, PLC_SLOT)

    # Connect to PLC
    try:
        client = connect_plc(PLC_IP, PLC_RACK, PLC_SLOT)
        logger.info("Connected to PLC at %s", PLC_IP)
    except Exception:
        logger.exception("Failed to connect to PLC at %s", PLC_IP)
        sys.exit(1)

    # Run polling loop
    try:
        poll_loop(client)
    finally:
        logger.info("Shutting down...")
        client.disconnect()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
