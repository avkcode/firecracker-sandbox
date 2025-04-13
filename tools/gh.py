#!/usr/bin/env python3
import os
import sys
import subprocess
import platform
import argparse
import shutil
import tempfile
import requests
from typing import Tuple, List, Optional

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
            arch = 'arm64' if '64' in arch else 'arm'
        elif arch.startswith('aarch64'):
            arch = 'arm64'
        else:
            arch = 'amd64'  # default to amd64

        return (distro, arch)
    except Exception as e:
        print_color(f"Error detecting system info: {e}", Colors.WARNING)
        return ('deb', 'amd64')  # defaults

def install_via_package_manager(distro: str) -> bool:
    """Install GitHub CLI using system package manager."""
    try:
        print_color("\nInstalling GitHub CLI via package manager...", Colors.HEADER)
        
        if distro == 'deb':
            # Debian/Ubuntu
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'gh'], check=True)
        elif distro == 'rpm':
            # RHEL/CentOS/Fedora
            subprocess.run(['sudo', 'dnf', 'install', '-y', 'gh'], check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        print_color(f"Package manager installation failed: {e}", Colors.WARNING)
        return False

def install_via_direct_download(arch: str) -> bool:
    """Install GitHub CLI by downloading directly from GitHub."""
    try:
        print_color("\nInstalling GitHub CLI via direct download...", Colors.HEADER)
        
        # Get latest release version
        latest_release = requests.get(
            "https://api.github.com/repos/cli/cli/releases/latest",
            timeout=10
        ).json()
        version = latest_release['tag_name'].lstrip('v')
        
        # Download package
        temp_dir = tempfile.mkdtemp()
        package_url = f"https://github.com/cli/cli/releases/download/v{version}/gh_{version}_linux_{arch}.tar.gz"
        package_path = os.path.join(temp_dir, "gh.tar.gz")
        
        print_color(f"Downloading GitHub CLI v{version}...", Colors.OKBLUE)
        subprocess.run([
            'curl', '-L', package_url, '-o', package_path
        ], check=True)
        
        # Extract and install
        print_color("Installing...", Colors.OKBLUE)
        subprocess.run([
            'tar', '-xf', package_path, '-C', temp_dir
        ], check=True)
        
        extracted_dir = os.path.join(temp_dir, f"gh_{version}_linux_{arch}")
        subprocess.run([
            'sudo', 'cp', os.path.join(extracted_dir, 'bin', 'gh'), '/usr/local/bin/'
        ], check=True)
        
        # Install man pages
        man_dir = '/usr/local/share/man/man1'
        os.makedirs(man_dir, exist_ok=True)
        subprocess.run([
            'sudo', 'cp', os.path.join(extracted_dir, 'share', 'man', 'man1', 'gh*.1'), man_dir
        ], check=True)
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        return True
    except Exception as e:
        print_color(f"Direct download installation failed: {e}", Colors.FAIL)
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False

def verify_installation() -> bool:
    """Verify gh CLI is properly installed."""
    try:
        version_output = subprocess.check_output(
            ['gh', '--version'],
            stderr=subprocess.PIPE,
            text=True
        )
        print_color("\nGitHub CLI installed successfully!", Colors.OKGREEN)
        print(version_output)
        return True
    except Exception as e:
        print_color(f"Verification failed: {e}", Colors.FAIL)
        return False

def authenticate_gh() -> bool:
    """Authenticate with GitHub."""
    try:
        print_color("\nAuthenticating with GitHub...", Colors.HEADER)
        print_color("Follow the prompts to authenticate with GitHub", Colors.OKBLUE)
        subprocess.run(['gh', 'auth', 'login'], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print_color(f"Authentication failed: {e}", Colors.FAIL)
        return False

def install_github_cli(
    force: bool = False,
    skip_auth: bool = False
) -> bool:
    """
    Install GitHub CLI tools on Linux.
    
    Args:
        force: Force reinstall even if already installed
        skip_auth: Skip GitHub authentication step
    Returns:
        bool: True if installation succeeded
    """
    try:
        # Check if already installed
        if shutil.which('gh') and not force:
            print_color("GitHub CLI is already installed.", Colors.WARNING)
            if not skip_auth:
                return authenticate_gh()
            return True

        # Get system info
        distro, arch = get_system_info()
        print_color(f"\nDetected system: {distro} package format, {arch} architecture", Colors.OKBLUE)

        # Try package manager first
        if not install_via_package_manager(distro):
            # Fall back to direct download
            if not install_via_direct_download(arch):
                return False

        # Verify installation
        if not verify_installation():
            return False

        # Authenticate
        if not skip_auth and not authenticate_gh():
            return False

        print_color("\nGitHub CLI installation complete!", Colors.OKGREEN)
        print("\nTry these commands:")
        print("  gh repo clone <repository>  # Clone a repository")
        print("  gh pr create               # Create a pull request")
        print("  gh issue create            # Create an issue")
        return True
    except Exception as e:
        print_color(f"An unexpected error occurred: {e}", Colors.FAIL)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Install GitHub CLI tools on Linux",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstall even if already installed"
    )
    parser.add_argument(
        "--skip-auth",
        action="store_true",
        help="Skip GitHub authentication step"
    )

    args = parser.parse_args()

    if not check_linux():
        sys.exit(1)

    success = install_github_cli(
        force=args.force,
        skip_auth=args.skip_auth
    )

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
