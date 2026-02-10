#!/usr/bin/env python3
"""
Build script for Windows portable package using PyInstaller.
Run this script on Windows to create the TDK2-Traceability portable package.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'


def print_step(message):
    print(f"{Colors.GREEN}>>> {message}{Colors.RESET}")


def print_warning(message):
    print(f"{Colors.YELLOW}WARNING: {message}{Colors.RESET}")


def print_error(message):
    print(f"{Colors.RED}ERROR: {message}{Colors.RESET}")


def main():
    print("=" * 60)
    print("TDK2-Traceability Windows Package Builder")
    print("=" * 60)

    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)

    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    package_dir = dist_dir / "TDK2-Traceability-Portable"
    scripts_dir = project_root / "scripts"

    print_step("Cleaning previous builds...")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    print_step("Running PyInstaller...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "build.spec"],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        print(result.stdout)
        if result.stderr:
            print("PyInstaller warnings:")
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        print_error("PyInstaller build failed!")
        print(e.stderr)
        return 1

    exe_path = dist_dir / "TDK2-Traceability.exe"
    if not exe_path.exists():
        print_error(f"TDK2-Traceability.exe not found at {exe_path}")
        return 1

    print_step("Creating package structure...")
    package_dir.mkdir(parents=True, exist_ok=True)

    # Move executable and _internal folder
    if (dist_dir / "_internal").exists():
        shutil.move(str(dist_dir / "_internal"), str(package_dir / "_internal"))
    shutil.move(str(exe_path), str(package_dir / "TDK2-Traceability.exe"))

    # Create runtime directories
    (package_dir / "measurements").mkdir(parents=True, exist_ok=True)
    (package_dir / "ftp_incoming").mkdir(parents=True, exist_ok=True)

    # Copy startup scripts
    print_step("Copying startup scripts...")
    scripts_dest = package_dir / "scripts"
    scripts_dest.mkdir(exist_ok=True)

    if scripts_dir.exists():
        for script_file in scripts_dir.glob("*.bat"):
            shutil.copy2(script_file, scripts_dest / script_file.name)

    # Create README.txt
    print_step("Creating README.txt...")
    readme_content = """TDK2 Traceability Application - Windows Portable Package

QUICK START:
1. Double-click TDK2-Traceability.exe to run the application
2. The application will start the FTP server and begin polling the PLC

CONFIGURATION:
Edit main.py constants before building, or modify the source:
- PLC_IP: PLC IP address (default: 192.168.1.1)
- PLC_RACK: PLC rack (default: 0)
- PLC_SLOT: PLC slot (default: 1)
- POLL_INTERVAL: Polling interval in seconds (default: 10)
- FTP_PORT: FTP server port (default: 21)

DATA FILES:
- Measurement CSV files: measurements\\<date>\\<EAN>\\data.csv
- Camera images: measurements\\<date>\\<EAN>\\images\\
- FTP incoming: ftp_incoming\\

AUTO-STARTUP:
1. Run scripts\\install_startup.bat as Administrator
2. To remove, run scripts\\uninstall_startup.bat

TROUBLESHOOTING:
- Verify network connectivity to PLC: ping 192.168.1.1
- Check that FTP port 21 is not blocked by firewall
- Review console output for error messages
"""

    with open(package_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)

    # Create ZIP archive
    print_step("Creating ZIP archive...")
    zip_path = dist_dir / "TDK2-Traceability-Portable.zip"
    shutil.make_archive(
        str(dist_dir / "TDK2-Traceability-Portable"),
        'zip',
        str(dist_dir),
        'TDK2-Traceability-Portable'
    )

    zip_size = zip_path.stat().st_size / (1024 * 1024)
    print_step(f"Package created: {zip_path}")
    print_step(f"Package size: {zip_size:.1f} MB")

    print("\n" + "=" * 60)
    print("Build completed successfully!")
    print("=" * 60)
    print(f"\nPackage location: {package_dir}")
    print(f"ZIP archive: {zip_path}")
    print("\nTo test the package:")
    print(f"  cd {package_dir}")
    print("  TDK2-Traceability.exe")

    return 0


if __name__ == "__main__":
    sys.exit(main())
