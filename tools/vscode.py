#!/usr/bin/env python3
import os
import sys
import subprocess
import platform
import argparse
import shutil
import hashlib
import requests
import tempfile
import time
import json
from pathlib import Path
from typing import Optional, Tuple, List

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_color(message: str, color: str) -> None:
    """Print colored message to terminal."""
    print(f"{color}{message}{Colors.ENDC}")

def check_linux() -> bool:
    """Check if the system is Linux."""
    if platform.system().lower() != 'linux':
        print_color("Error: This script is only for Linux systems.", Colors.FAIL)
        return False
    return True

def check_dependencies() -> Tuple[bool, List[str]]:
    """Check for required dependencies."""
    missing = []
    required = ['curl', 'tar', 'git']
    
    for dep in required:
        if not shutil.which(dep):
            missing.append(dep)
    
    return (len(missing) == 0, missing)

def get_latest_release_info(insiders: bool = False) -> Optional[dict]:
    """Get the latest release information for VSCode Server."""
    try:
        channel = "insider" if insiders else "stable"
        url = f"https://update.code.visualstudio.com/api/update/linux-x64/{channel}/latest"
        headers = {
            "User-Agent": "VSCode-Server-Installer/1.0",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print_color(f"Error fetching release info: {e}", Colors.WARNING)
        return None

def download_with_progress(url: str, dest: str) -> bool:
    """Download file with progress display."""
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            start_time = time.time()
            
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        elapsed = time.time() - start_time
                        speed = downloaded / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                        percent = (downloaded / total_size) * 100 if total_size > 0 else 0
                        sys.stdout.write(
                            f"\rDownloading... {percent:.1f}% "
                            f"({downloaded/(1024*1024):.1f}MB/{total_size/(1024*1024):.1f}MB) "
                            f"at {speed:.1f}MB/s"
                        )
                        sys.stdout.flush()
            print()
            return True
    except Exception as e:
        print_color(f"\nDownload failed: {e}", Colors.FAIL)
        return False

def verify_checksum(file_path: str, expected_hash: Optional[str]) -> bool:
    """Verify file checksum if provided."""
    if not expected_hash:
        return True
        
    print("Verifying download integrity...")
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha256.update(data)
    actual_hash = sha256.hexdigest()
    
    if actual_hash != expected_hash.lower():
        print_color(f"Checksum mismatch!\nExpected: {expected_hash}\nActual:   {actual_hash}", Colors.FAIL)
        return False
    return True

def install_extensions(extensions: List[str], user_install: bool = True) -> None:
    """Install recommended extensions."""
    if not extensions:
        return
        
    print("\nInstalling recommended extensions...")
    vscode_bin = os.path.expanduser("~/.vscode-server/bin/code-server") if user_install else "/usr/share/vscode-server/bin/code-server"
    
    for ext in extensions:
        try:
            print_color(f"Installing {ext}...", Colors.OKBLUE)
            subprocess.run([vscode_bin, "--install-extension", ext], check=True)
        except subprocess.CalledProcessError:
            print_color(f"Failed to install extension: {ext}", Colors.WARNING)

def setup_systemd_service(install_dir: str, port: int = 8080) -> None:
    """Create a systemd service for always-on VSCode server."""
    service_content = f"""[Unit]
Description=VSCode Remote Server
After=network.target

[Service]
Type=simple
ExecStart={install_dir}/bin/code-server --host 0.0.0.0 --port {port} --auth none
Restart=always
User={os.getenv('SUDO_USER', os.getenv('USER'))}

[Install]
WantedBy=multi-user.target
"""
    
    service_path = "/etc/systemd/system/vscode-server.service"
    try:
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", "vscode-server.service"], check=True)
        subprocess.run(["systemctl", "start", "vscode-server.service"], check=True)
        
        print_color("\nSystemd service created and started!", Colors.OKGREEN)
        print(f"VSCode Server is now running on http://localhost:{port}")
    except Exception as e:
        print_color(f"Failed to create systemd service: {e}", Colors.WARNING)

def install_vscode_server(
    user_install: bool = True,
    version: str = "stable",
    extensions: List[str] = None,
    systemd_service: bool = False,
    force: bool = False,
    port: int = 8080
) -> bool:
    """
    Install VS Code Server on the Linux machine.
    
    Args:
        user_install: Install for current user if True, system-wide if False
        version: Either 'stable' or 'insiders'
        extensions: List of extension IDs to install
        systemd_service: Whether to create a systemd service
        force: Force reinstall even if already installed
        port: Port to use for systemd service
    Returns:
        bool: True if installation succeeded
    """
    try:
        # Determine the install directory
        if user_install:
            install_dir = os.path.expanduser("~/.vscode-server")
        else:
            install_dir = "/usr/share/vscode-server"
        
        # Check if already installed
        if os.path.exists(f"{install_dir}/bin/code-server") and not force:
            print_color(f"VSCode Server already installed at {install_dir}", Colors.WARNING)
            return True
        
        # Get latest release info
        is_insiders = version.lower() == "insiders"
        release_info = get_latest_release_info(is_insiders)
        if not release_info:
            print_color("Failed to get release information. Trying fallback URL...", Colors.WARNING)
            
            # Fallback to direct download
            download_url = "https://aka.ms/vscode-server-launcher/x86_64-unknown-linux-gnu"
            version_display = "latest"
        else:
            download_url = release_info.get("url")
            version_display = release_info.get("name", "latest")
        
        print_color(
            f"\nInstalling VS Code Server ({version}) version {version_display} "
            f"to {install_dir}...",
            Colors.HEADER
        )
        
        # Create temp directory for download
        with tempfile.TemporaryDirectory() as temp_dir:
            tarball_path = os.path.join(temp_dir, "vscode-server.tar.gz")
            
            # Download the tarball
            if not download_with_progress(download_url, tarball_path):
                return False
            
            # Verify checksum if available
            if release_info and not verify_checksum(tarball_path, release_info.get("sha256hash")):
                return False
            
            # Create the installation directory
            os.makedirs(install_dir, exist_ok=True)
            
            # Extract the tarball
            print("\nExtracting VSCode Server...")
            extract_cmd = [
                "tar", "-xzf", tarball_path,
                "-C", install_dir,
                "--strip-components", "1"
            ]
            subprocess.run(extract_cmd, check=True)
        
        # Create a symlink to the binary if system-wide install
        if not user_install:
            bin_path = "/usr/local/bin/code-server"
            if os.path.exists(bin_path):
                os.remove(bin_path)
            os.symlink(
                f"{install_dir}/bin/code-server",
                bin_path
            )
        
        print_color("\nVS Code Server installed successfully!", Colors.OKGREEN)
        print(f"Binary location: {install_dir}/bin/code-server")
        
        # Install extensions if specified
        if extensions:
            install_extensions(extensions, user_install)
        
        # Setup systemd service if requested
        if systemd_service:
            if not user_install or os.geteuid() == 0:
                setup_systemd_service(install_dir, port)
            else:
                print_color(
                    "Systemd service setup requires root privileges. Skipping...",
                    Colors.WARNING
                )
        
        if user_install:
            print("\nYou can now connect to this server using VS Code with the Remote-SSH extension.")
        else:
            print("\nSystem-wide installation complete. The 'code-server' command is available.")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print_color(f"Error during installation: {e}", Colors.FAIL)
        return False
    except Exception as e:
        print_color(f"An unexpected error occurred: {e}", Colors.FAIL)
        return False

def main():
    if not check_linux():
        sys.exit(1)
    
    deps_ok, missing_deps = check_dependencies()
    if not deps_ok:
        print_color(
            f"Missing dependencies: {', '.join(missing_deps)}\n"
            "Please install them first (e.g., 'sudo apt install curl tar git')",
            Colors.FAIL
        )
        sys.exit(1)
    
    # Recommended extensions for remote development
    recommended_extensions = [
        "ms-vscode-remote.remote-ssh",
        "ms-vscode-remote.remote-containers",
        "ms-vscode-remote.remote-wsl"
    ]
    
    parser = argparse.ArgumentParser(
        description="Install VS Code Remote Server on Linux",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--system",
        action="store_true",
        help="Install system-wide (requires root)"
    )
    parser.add_argument(
        "--insiders",
        action="store_true",
        help="Install VS Code Insiders version"
    )
    parser.add_argument(
        "--extensions",
        action="store_true",
        help="Install recommended extensions"
    )
    parser.add_argument(
        "--systemd",
        action="store_true",
        help="Create systemd service for always-on server"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstall even if already installed"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to use for systemd service"
    )
    
    args = parser.parse_args()
    
    if args.system and os.geteuid() != 0:
        print_color("System-wide installation requires root privileges.", Colors.FAIL)
        sys.exit(1)
    
    version = "insiders" if args.insiders else "stable"
    extensions = recommended_extensions if args.extensions else []
    
    success = install_vscode_server(
        user_install=not args.system,
        version=version,
        extensions=extensions,
        systemd_service=args.systemd,
        force=args.force,
        port=args.port
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
