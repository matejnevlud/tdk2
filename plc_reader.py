"""DB90 reading, parsing, and CSV saving for the traceability application."""

import csv
import os
import struct
from datetime import datetime

import snap7

DB_NUMBER = 90
DB_SIZE = 482


def connect_plc(ip: str, rack: int, slot: int) -> snap7.client.Client:
    client = snap7.client.Client()
    client.connect(ip, rack, slot)
    return client


def read_db90(client: snap7.client.Client) -> bytearray:
    return client.db_read(DB_NUMBER, 0, DB_SIZE)


def parse_ean(data: bytearray) -> str:
    raw = data[4:131]
    return raw.decode("ascii", errors="replace").rstrip("\x00 ")


def parse_dtl(data: bytearray, offset: int) -> datetime | None:
    """Parse a 12-byte Siemens DTL structure into a datetime."""
    chunk = data[offset : offset + 12]
    year, month, day, _weekday, hour, minute, sec, nanosec = struct.unpack_from(
        ">HBBBBBBi", chunk
    )
    if year == 0 and month == 0 and day == 0:
        return None
    try:
        microsec = nanosec // 1000
        return datetime(year, month, day, hour, minute, sec, microsec)
    except ValueError:
        return None


def parse_ljs_data(data: bytearray) -> list[float]:
    """Parse 63 Real (float32) values starting at offset 132."""
    return list(struct.unpack_from(">63f", data, 132))


def parse_db90(data: bytearray) -> dict:
    """Parse the full DB90 block into a dictionary."""
    id_val = struct.unpack_from(">b", data, 0)[0]
    presence = bool(data[1])
    result_total = struct.unpack_from(">b", data, 2)[0]
    ean = parse_ean(data)
    ljs = parse_ljs_data(data)

    positions = []
    for i in range(7):
        base = 384 + i * 14
        result = struct.unpack_from(">b", data, base)[0]
        ts = parse_dtl(data, base + 2)
        positions.append({"result": result, "timestamp": ts})

    return {
        "id": id_val,
        "presence": presence,
        "result_total": result_total,
        "ean": ean,
        "ljs": ljs,
        "positions": positions,
    }


def format_timestamp(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


def format_timestamp_for_match(dt: datetime | None) -> str:
    """Format timestamp for matching with FTP directory names."""
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d_%H-%M-%S")


CSV_HEADER = (
    ["timestamp", "id", "presence", "result_total", "ean"]
    + [f"ljs_{i}" for i in range(1, 64)]
    + [
        field
        for pos in range(1, 8)
        for field in (f"pos{pos}_result", f"pos{pos}_timestamp")
    ]
)


def save_to_csv(record: dict, base_dir: str = "measurements") -> str:
    """Save a parsed DB90 record to CSV. Returns the folder path used."""
    today = datetime.now().strftime("%Y-%m-%d")
    ean = record["ean"] or "UNKNOWN"
    # Replace characters illegal in Windows directory names: \ / : * ? " < > |
    safe_ean = ean.replace(":", "_").replace("\\", "_").replace("/", "_")
    safe_ean = safe_ean.replace("*", "_").replace("?", "_").replace('"', "_")
    safe_ean = safe_ean.replace("<", "_").replace(">", "_").replace("|", "_")
    folder = os.path.join(base_dir, today, safe_ean)
    os.makedirs(folder, exist_ok=True)
    csv_path = os.path.join(folder, "data.csv")

    file_exists = os.path.isfile(csv_path)

    row = {
        "timestamp": datetime.now().isoformat(),
        "id": record["id"],
        "presence": int(record["presence"]),
        "result_total": record["result_total"],
        "ean": record["ean"],
    }
    for i, val in enumerate(record["ljs"], start=1):
        row[f"ljs_{i}"] = f"{val:.6f}"
    for i, pos in enumerate(record["positions"], start=1):
        row[f"pos{i}_result"] = pos["result"]
        row[f"pos{i}_timestamp"] = format_timestamp(pos["timestamp"])

    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    return folder
