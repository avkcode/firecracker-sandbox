#!/usr/bin/env python3
import os
import sys
import subprocess
import platform
import argparse
import shutil
from typing import Tuple, Optional

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
    print(f"{color}{message}{Colors.ENDC}")

def check_linux() -> bool:
    if platform.system().lower() != 'linux':
        print_color("Error: This script is only for Linux systems.", Colors.FAIL)
        return False
    return True

def get_system_info() -> Tuple[str, str]:
    try:
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release') as f:
                distro_info = f.read()
            if 'debian' in distro_info.lower() or 'ubuntu' in distro_info.lower():
                distro = 'deb'
            elif 'rhel' in distro_info.lower() or 'centos' in distro_info.lower() or 'fedora' in distro_info.lower():
                distro = 'rpm'
            else:
                distro = 'deb'
        else:
            distro = 'deb'

        arch = platform.machine().lower()
        return (distro, arch)
    except Exception as e:
        print_color(f"Error detecting system info: {e}", Colors.WARNING)
        return ('deb', 'amd64')

def install_docker() -> bool:
    try:
        if shutil.which('docker'):
            print_color("Docker is already installed.", Colors.OKGREEN)
            return True

        print_color("\nInstalling Docker...", Colors.HEADER)
        subprocess.run(
            "curl -fsSL https://get.docker.com | sudo sh",
            shell=True,
            check=True
        )
        
        current_user = os.getenv('USER')
        if current_user:
            subprocess.run(
                ["sudo", "usermod", "-aG", "docker", current_user],
                check=True
            )
            print_color(f"Added user {current_user} to docker group. You may need to logout/login for this to take effect.", Colors.WARNING)

        print_color("Docker installed successfully", Colors.OKGREEN)
        return True
    except subprocess.CalledProcessError as e:
        print_color(f"Error installing Docker: {e}", Colors.FAIL)
        return False

def install_docker_compose() -> bool:
    try:
        if shutil.which('docker-compose'):
            print_color("Docker Compose is already installed.", Colors.OKGREEN)
            return True

        print_color("\nInstalling Docker Compose...", Colors.HEADER)
        
        # Get latest version
        try:
            compose_version = subprocess.check_output(
                ["curl", "-s", "https://api.github.com/repos/docker/compose/releases/latest"],
                text=True
            )
            compose_version = subprocess.check_output(
                ["grep", "'tag_name'"],
                input=compose_version,
                text=True
            )
            compose_version = subprocess.check_output(
                ["cut", "-d", "'\"'", "-f", "4"],
                input=compose_version,
                text=True
            ).strip()
        except Exception:
            # Fallback version if API call fails
            compose_version = "v2.24.5"

        # Download and install
        subprocess.run([
            "sudo", "curl", "-L",
            f"https://github.com/docker/compose/releases/download/{compose_version}/docker-compose-$(uname -s)-$(uname -m)",
            "-o", "/usr/local/bin/docker-compose"
        ], shell=True, check=True)
        
        subprocess.run([
            "sudo", "chmod", "+x", "/usr/local/bin/docker-compose"
        ], check=True)

        # Verify installation - fixed this line
        subprocess.run([
            "/usr/local/bin/docker-compose", "--version"
        ], check=True)

        print_color("Docker Compose installed successfully!", Colors.OKGREEN)
        return True
    except subprocess.CalledProcessError as e:
        print_color(f"Error installing Docker Compose: {e}", Colors.FAIL)
        return False

def create_sample_compose_file() -> bool:
    try:
        compose_content = """version: '3.8'

services:
  web:
    image: nginx:alpine
    ports:
      - "80:80"
    restart: unless-stopped

  db:
    image: postgres:13
    environment:
      POSTGRES_PASSWORD: example
    volumes:
      - db_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  db_data:
"""
        compose_path = "docker-compose.yml"
        
        if os.path.exists(compose_path):
            print_color("docker-compose.yml already exists. Skipping creation.", Colors.WARNING)
            return True

        with open(compose_path, 'w') as f:
            f.write(compose_content)

        print_color(f"Created sample docker-compose.yml at {os.path.abspath(compose_path)}", Colors.OKGREEN)
        return True
    except Exception as e:
        print_color(f"Error creating sample compose file: {e}", Colors.FAIL)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Install Docker and Docker Compose on Linux"
    )
    parser.add_argument(
        '--skip-docker',
        action='store_true',
        help='Skip Docker installation (only install Docker Compose)'
    )
    parser.add_argument(
        '--no-sample',
        action='store_true',
        help='Skip creation of sample docker-compose.yml'
    )
    args = parser.parse_args()

    if not check_linux():
        sys.exit(1)

    docker_installed = True
    if not args.skip_docker:
        docker_installed = install_docker()

    compose_installed = install_docker_compose()

    sample_created = True
    if not args.no_sample and docker_installed and compose_installed:
        sample_created = create_sample_compose_file()

    if docker_installed and compose_installed and sample_created:
        print_color("\nInstallation completed successfully!", Colors.OKGREEN)
        print("\nNext steps:")
        print("1. Try the sample application: docker-compose up -d")
        print("2. Access the web server at http://localhost")
        print("3. Stop the containers: docker-compose down")
        sys.exit(0)
    else:
        print_color("\nInstallation completed with errors.", Colors.FAIL)
        sys.exit(1)

if __name__ == "__main__":
    main()
