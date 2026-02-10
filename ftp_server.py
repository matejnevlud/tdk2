"""FTP server for receiving camera images from the vision controller."""

import logging
import os
import threading

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

logger = logging.getLogger(__name__)

FTP_ROOT = "ftp_incoming"


def start_ftp_server(port: int = 21, ftp_root: str = FTP_ROOT) -> FTPServer:
    """Create and start the FTP server in a daemon thread. Returns the server instance."""
    os.makedirs(ftp_root, exist_ok=True)

    authorizer = DummyAuthorizer()
    authorizer.add_anonymous(ftp_root, perm="elradfmw")

    handler = FTPHandler
    handler.authorizer = authorizer
    handler.passive_ports = range(60000, 60100)
    handler.banner = "TDK2 Traceability FTP Server"

    server = FTPServer(("0.0.0.0", port), handler)
    server.max_cons = 10
    server.max_cons_per_ip = 5

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("FTP server started on port %d, root: %s", port, ftp_root)

    return server


def find_matching_images(timestamp_str: str, ftp_root: str = FTP_ROOT) -> str | None:
    """Find an FTP directory whose name matches the given timestamp string.

    The camera controller creates directories named by timestamp.
    We look for a directory matching the normalized Pos.1 timestamp.
    Returns the full path to the matching directory, or None.
    """
    if not timestamp_str or not os.path.isdir(ftp_root):
        return None

    for entry in os.listdir(ftp_root):
        entry_path = os.path.join(ftp_root, entry)
        if os.path.isdir(entry_path) and entry == timestamp_str:
            return entry_path

    return None


def copy_images(src_dir: str, dest_folder: str) -> int:
    """Copy all image files from src_dir into dest_folder/images/.

    Returns the number of files copied.
    """
    import shutil

    images_dir = os.path.join(dest_folder, "images")
    os.makedirs(images_dir, exist_ok=True)

    count = 0
    for filename in os.listdir(src_dir):
        src_path = os.path.join(src_dir, filename)
        if os.path.isfile(src_path):
            shutil.copy2(src_path, os.path.join(images_dir, filename))
            count += 1

    if count > 0:
        logger.info("Copied %d images from %s to %s", count, src_dir, images_dir)

    return count
