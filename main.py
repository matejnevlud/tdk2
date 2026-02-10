"""Entry point for the TDK2 traceability application.

Monitors a shared camera image folder and polls a Siemens PLC (DB90)
for measurement data, organizing everything by date and EAN code.
"""

import configparser
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
# Resolve config.ini next to the exe (or script) so it works after PyInstaller build
if getattr(sys, "frozen", False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(_APP_DIR, "config.ini")

DEFAULTS = {
    "plc_ip": "192.168.11.1",
    "plc_rack": "0",
    "plc_slot": "1",
    "poll_interval": "4",
    "camera_dir": r"C:\\Users\\TDK\Desktop\\TDK2-Traceability-Portable-2\\ftp_incoming",
    "base_dir": r"X:\\",
}


def load_config(path: str) -> configparser.ConfigParser:
    """Load config.ini, creating it with defaults if it doesn't exist."""
    config = configparser.ConfigParser()
    config["DEFAULT"] = DEFAULTS

    if os.path.isfile(path):
        config.read(path, encoding="utf-8")
    else:
        # Create the file so the user can edit it
        config["tdk2"] = {}
        with open(path, "w", encoding="utf-8") as f:
            f.write("# TDK2 Traceability Configuration\n")
            f.write("# Edit values below and restart the application.\n\n")
            config.write(f)

    return config


_cfg = load_config(CONFIG_PATH)
_sec = _cfg["tdk2"] if _cfg.has_section("tdk2") else _cfg["DEFAULT"]

PLC_IP = _sec.get("plc_ip")
PLC_RACK = _sec.getint("plc_rack")
PLC_SLOT = _sec.getint("plc_slot")
POLL_INTERVAL = _sec.getfloat("poll_interval")
CAMERA_DIR = _sec.get("camera_dir")
BASE_DIR = _sec.get("base_dir")

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
                for pos in range(1, 4):
                    pos_ts = record["positions"][pos - 1]["timestamp"]
                    if pos_ts is None:
                        continue
                    cam_dir = find_closest_camera_dir(pos_ts, CAMERA_DIR)
                    if cam_dir:
                        copy_position_image(cam_dir, pos, folder)

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
    logger.info("Config file: %s", CONFIG_PATH)

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
