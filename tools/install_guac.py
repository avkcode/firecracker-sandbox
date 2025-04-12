#!/usr/bin/env python3
import os
import sys
import subprocess
import platform
import argparse
import shutil
from typing import Tuple, List

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
        return (distro, arch)
    except Exception as e:
        print_color(f"Error detecting system info: {e}", Colors.WARNING)
        return ('deb', 'amd64')  # defaults

def check_linux() -> bool:
    """Check if the system is Linux."""
    if platform.system().lower() != 'linux':
        print_color("Error: This script is only for Linux systems.", Colors.FAIL)
        return False
    return True

def install_via_packages(distro: str) -> bool:
    """Install Guacamole using system packages."""
    try:
        print_color("\nInstalling Guacamole via system packages...", Colors.HEADER)
        
        if distro == 'deb':
            # Ubuntu/Debian
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run([
                'sudo', 'apt-get', 'install', '-y',
                'guacamole', 'guacamole-client', 'guacd',
                'libguac-client-rdp0', 'libguac-client-vnc0',
                'libguac-client-ssh0', 'libguac-client-kubernetes0'
            ], check=True)
            
        elif distro == 'rpm':
            # RHEL/CentOS
            subprocess.run([
                'sudo', 'yum', 'install', '-y',
                'guacamole', 'guacamole-client', 'guacd',
                'guacamole-common', 'guacamole-common-rdp',
                'guacamole-common-vnc', 'guacamole-common-ssh'
            ], check=True)
            
        return True
    except subprocess.CalledProcessError as e:
        print_color(f"Package installation failed: {e}", Colors.FAIL)
        return False

def install_via_docker() -> bool:
    """Install Guacamole using Docker (fallback method)."""
    try:
        print_color("\nInstalling Guacamole via Docker...", Colors.HEADER)
        
        # Check if Docker is installed
        if not shutil.which('docker'):
            print_color("Installing Docker...", Colors.OKBLUE)
            subprocess.run([
                'curl', '-fsSL', 'https://get.docker.com', 
                '|', 'sudo', 'sh'
            ], shell=True, check=True)
        
        # Create Docker Compose file
        compose_content = """
version: '3'
services:
  guacamole:
    image: guacamole/guacamole
    ports:
      - "8080:8080"
    depends_on:
      - guacd
      - mysql
    environment:
      MYSQL_HOSTNAME: mysql
      MYSQL_DATABASE: guacamole_db
      MYSQL_USER: guacamole_user
      MYSQL_PASSWORD: securepassword

  guacd:
    image: guacamole/guacd

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: guacamole_db
      MYSQL_USER: guacamole_user
      MYSQL_PASSWORD: securepassword
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
"""
        with open('docker-compose.yml', 'w') as f:
            f.write(compose_content)
            
        # Start containers
        subprocess.run(['sudo', 'docker-compose', 'up', '-d'], check=True)
        
        print_color("\nGuacamole installed via Docker!", Colors.OKGREEN)
        print("Access at: http://localhost:8080/guacamole")
        return True
        
    except Exception as e:
        print_color(f"Docker installation failed: {e}", Colors.FAIL)
        return False

def install_guacamole(use_packages: bool = True) -> bool:
    """Main installation function."""
    try:
        distro, _ = get_system_info()
        
        if use_packages:
            if not install_via_packages(distro):
                print_color("Falling back to Docker installation...", Colors.WARNING)
                return install_via_docker()
        else:
            print_color("Using Docker installation as requested...", Colors.OKBLUE)
            return install_via_docker()
            
        return True
    except Exception as e:
        print_color(f"Installation failed: {e}", Colors.FAIL)
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker', action='store_true', help='Use Docker installation')
    args = parser.parse_args()
    
    if not check_linux():
        sys.exit(1)
        
    success = install_guacamole(use_packages=not args.docker)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
