"""Entry point for the TDK2 traceability application.

Starts an FTP server for camera images and polls a Siemens PLC (DB90)
for measurement data, organizing everything by date and EAN code.
"""

import logging
import signal
import sys
import time

from plc_reader import (
    connect_plc,
    format_timestamp_for_match,
    parse_db90,
    read_db90,
    save_to_csv,
)
from ftp_server import (
    FTP_ROOT,
    copy_images,
    find_matching_images,
    start_ftp_server,
)

# ── Configuration ──────────────────────────────────────────────────────
PLC_IP = "192.168.11.1"
PLC_RACK = 0
PLC_SLOT = 1
POLL_INTERVAL = 10  # seconds
FTP_PORT = 21
BASE_DIR = "measurements"

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

                # Try to match and copy camera images by Pos.1 timestamp
                pos1_ts = record["positions"][0]["timestamp"]
                ts_str = format_timestamp_for_match(pos1_ts)
                if ts_str:
                    img_dir = find_matching_images(ts_str, ftp_root=FTP_ROOT)
                    if img_dir:
                        count = copy_images(img_dir, folder)
                        logger.info("Matched %d images for EAN %s", count, current_ean)
                    else:
                        logger.debug("No FTP images found for timestamp %s", ts_str)

                last_ean = current_ean

        except Exception:
            logger.exception("Error during PLC poll")

        # Sleep in small increments so we can respond to shutdown quickly
        for _ in range(int(POLL_INTERVAL * 10)):
            if not running:
                break
            time.sleep(0.1)


def main():
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("Starting TDK2 Traceability Application")
    logger.info("PLC: %s (rack=%d, slot=%d, DB90)", PLC_IP, PLC_RACK, PLC_SLOT)

    # Start FTP server
    ftp_server = start_ftp_server(port=FTP_PORT)
    logger.info("FTP server running on port %d", FTP_PORT)

    # Connect to PLC
    try:
        client = connect_plc(PLC_IP, PLC_RACK, PLC_SLOT)
        logger.info("Connected to PLC at %s", PLC_IP)
    except Exception:
        logger.exception("Failed to connect to PLC at %s", PLC_IP)
        ftp_server.close_all()
        sys.exit(1)

    # Run polling loop
    try:
        poll_loop(client)
    finally:
        logger.info("Shutting down...")
        client.disconnect()
        ftp_server.close_all()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
