#!/usr/bin/env python3
import os
import sys
import subprocess
import platform
import argparse
import shutil
import requests
import tempfile
import time
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
    required = ['curl', 'grep', 'systemctl']
    
    for dep in required:
        if not shutil.which(dep):
            missing.append(dep)
    
    return (len(missing) == 0, missing)

def get_system_info() -> Tuple[str, str]:
    """Get Linux distribution and architecture."""
    try:
        # Get distribution
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release') as f:
                distro_info = f.read()
            if 'debian' in distro_info.lower() or 'ubuntu' in distro_info.lower():
                distro = 'deb'
            elif 'rhel' in distro_info.lower() or 'centos' in distro_info.lower() or 'fedora' in distro_info.lower():
                distro = 'rpm'
            else:
                distro = 'deb'  # default to deb
        else:
            distro = 'deb'  # default to deb

        # Get architecture
        arch = platform.machine().lower()
        if arch in ['x86_64', 'amd64']:
            arch = 'amd64'
        elif arch.startswith('arm'):
            arch = 'arm'
        elif arch.startswith('aarch64'):
            arch = 'arm64'
        else:
            arch = 'amd64'  # default to amd64

        return (distro, arch)
    except Exception as e:
        print_color(f"Error detecting system info: {e}", Colors.WARNING)
        return ('deb', 'amd64')  # defaults

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

def install_gitlab_runner_package(distro: str, arch: str) -> bool:
    """Install GitLab Runner using the official repository."""
    try:
        print_color("\nAdding GitLab Runner repository...", Colors.HEADER)
        
        # Add repository
        if distro == 'deb':
            # For Debian/Ubuntu
            repo_script = """
            curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | sudo bash
            """
            subprocess.run(
                ["bash", "-c", repo_script],
                check=True
            )
            
            # Install package
            subprocess.run(
                ["sudo", "apt-get", "install", "-y", "gitlab-runner"],
                check=True
            )
        else:
            # For RHEL/CentOS/Fedora
            repo_script = """
            curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.rpm.sh" | sudo bash
            """
            subprocess.run(
                ["bash", "-c", repo_script],
                check=True
            )
            
            # Install package
            subprocess.run(
                ["sudo", "yum", "install", "-y", "gitlab-runner"],
                check=True
            )
        
        return True
    except subprocess.CalledProcessError as e:
        print_color(f"Error installing package: {e}", Colors.FAIL)
        return False

def register_runner(
    registration_token: str,
    url: str = "https://gitlab.com",
    description: str = "My Runner",
    tags: str = "",
    executor: str = "shell",
    docker_image: str = "alpine:latest"
) -> bool:
    """Register the GitLab Runner."""
    try:
        print_color("\nRegistering GitLab Runner...", Colors.HEADER)
        
        cmd = [
            "sudo", "gitlab-runner", "register",
            "--non-interactive",
            "--url", url,
            "--registration-token", registration_token,
            "--description", description,
            "--executor", executor,
            "--tag-list", tags
        ]
        
        if executor == "docker":
            cmd.extend(["--docker-image", docker_image])
        
        subprocess.run(cmd, check=True)
        
        print_color("\nGitLab Runner registered successfully!", Colors.OKGREEN)
        return True
    except subprocess.CalledProcessError as e:
        print_color(f"Error registering runner: {e}", Colors.FAIL)
        return False

def install_gitlab_runner(
    registration_token: Optional[str] = None,
    url: str = "https://gitlab.com",
    description: str = "My Runner",
    tags: str = "",
    executor: str = "shell",
    docker_image: str = "alpine:latest",
    force: bool = False
) -> bool:
    """
    Install and configure GitLab Runner on Linux.
    
    Args:
        registration_token: GitLab registration token (optional)
        url: GitLab instance URL
        description: Runner description
        tags: Comma-separated tags
        executor: Runner executor (shell, docker, etc.)
        docker_image: Default Docker image (if using docker executor)
        force: Force reinstall even if already installed
    Returns:
        bool: True if installation succeeded
    """
    try:
        # Check if already installed
        if shutil.which("gitlab-runner") and not force:
            print_color("GitLab Runner is already installed.", Colors.WARNING)
            return True
        
        # Get system info
        distro, arch = get_system_info()
        print_color(f"\nDetected system: {distro} package format, {arch} architecture", Colors.OKBLUE)
        
        # Install GitLab Runner
        if not install_gitlab_runner_package(distro, arch):
            return False
        
        # Register runner if token provided
        if registration_token:
            if not register_runner(
                registration_token,
                url,
                description,
                tags,
                executor,
                docker_image
            ):
                return False
        
        print_color("\nGitLab Runner installation complete!", Colors.OKGREEN)
        print("Available commands:")
        print("  sudo gitlab-runner start    # Start the runner")
        print("  sudo gitlab-runner stop     # Stop the runner")
        print("  sudo gitlab-runner status   # Check runner status")
        print("  sudo gitlab-runner --help  # Show all commands")
        
        return True
        
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
            "Please install them first (e.g., 'sudo apt install curl grep systemd')",
            Colors.FAIL
        )
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description="Install GitLab Runner on Linux",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--token",
        help="GitLab Runner registration token (optional)"
    )
    parser.add_argument(
        "--url",
        default="https://gitlab.com",
        help="GitLab instance URL"
    )
    parser.add_argument(
        "--description",
        default="My Runner",
        help="Runner description"
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags for the runner"
    )
    parser.add_argument(
        "--executor",
        default="shell",
        choices=["shell", "docker", "docker-ssh", "ssh", "parallels", "virtualbox", "kubernetes"],
        help="Runner executor type"
    )
    parser.add_argument(
        "--docker-image",
        default="alpine:latest",
        help="Default Docker image (if using docker executor)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstall even if already installed"
    )
    
    args = parser.parse_args()
    
    success = install_gitlab_runner(
        registration_token=args.token,
        url=args.url,
        description=args.description,
        tags=args.tags,
        executor=args.executor,
        docker_image=args.docker_image,
        force=args.force
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
