#!/usr/bin/python3

import os
import subprocess
import logging
import shutil
import requests
import json
import argparse
import platform
import tarfile
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Configure logging with timestamps and colors
logging.basicConfig(
    level=logging.INFO,
    format=f'{Fore.GREEN}%(asctime)s{Style.RESET_ALL} - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    help_description = """
    Linux Kernel Build Script for Firecracker Compatibility

    This script automates the process of downloading, configuring, and building a Linux kernel
    with Firecracker compatibility. It supports custom kernel configurations via a JSON file
    and allows the use of a predefined .config file.

    Example JSON configuration file:
    {
        "KERNEL_VERSION": "5.15.0",
        "KERNEL_CONFIG": {
            "CONFIG_VIRTIO": "y",
            "CONFIG_NET_9P": "n"
        }
    }

    Usage:
        ./build_kernel.py --config <config_file> [--predefined-config <predefined_config>] [--verbose] [--clean]

    Arguments:
        --config              Path to the JSON configuration file (required).
        --predefined-config   Path to a predefined .config file (optional).
        --verbose             Enable verbose logging for debugging (optional).
        --clean               Clean the build directory before starting (optional).
    """
    parser = argparse.ArgumentParser(
        description=help_description,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the JSON configuration file containing the kernel version and configuration options."
    )
    parser.add_argument(
        "--predefined-config",
        help="Path to a predefined .config file to use for kernel configuration."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging for debugging."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean the build directory before starting."
    )
    return parser.parse_args()

def load_config(config_file):
    """Load configuration from a JSON file."""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_file}.")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file {config_file} not found.")
        exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse {config_file}: {e}")
        exit(1)

def run_command(command, error_message):
    """Run a shell command and handle errors."""
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"{error_message}: {e}")
        exit(1)

def download_file(url, output):
    """Download a file from a URL."""
    try:
        logger.info(f"Downloading {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Downloaded {output} successfully.")
    except requests.RequestException as e:
        logger.error(f"Failed to download {url}: {e}")
        exit(1)

def apply_kernel_config(config_options):
    """Apply kernel configuration options."""
    for option, value in config_options.items():
        logger.info(f"Setting {option} to {value}...")
        result = subprocess.run(f"grep -q '^CONFIG_{option}=' .config", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            run_command(f"scripts/config --set-val {option} {value}", f"Failed to set {option} to {value}")
        else:
            logger.info(f"Option {option} is already set in .config; skipping.")

def display_kernel_config():
    """Display the final kernel configuration in JSON format."""
    logger.info("Displaying final kernel configuration in JSON format:")
    try:
        kernel_config = {}
        with open(".config", "r") as config_file:
            for line in config_file:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    kernel_config[key] = value
        print(json.dumps(kernel_config, indent=4))
    except FileNotFoundError:
        logger.error(".config file not found. Cannot display kernel configuration.")
        exit(1)

def get_major_version(kernel_version):
    """Extract the major version number from the kernel version string."""
    try:
        major_version = kernel_version.split(".")[0]
        return f"v{major_version}.x"
    except (IndexError, AttributeError):
        logger.error(f"Invalid kernel version format: {kernel_version}")
        exit(1)

def install_dependencies():
    """Detect the Linux distribution and install dependencies."""
    distro = platform.freedesktop_os_release().get("ID", "").lower()
    logger.info(f"Detected distribution: {distro}")

    if distro in ["ubuntu", "debian"]:
        run_command(
            "sudo apt update && sudo apt install -y build-essential libncurses-dev bison flex libssl-dev libelf-dev",
            "Failed to install dependencies on Ubuntu/Debian."
        )
    elif distro in ["centos", "rhel"]:
        run_command(
            "sudo yum install -y gcc ncurses-devel bison flex elfutils-libelf-devel openssl-devel",
            "Failed to install dependencies on CentOS/RHEL."
        )
    elif distro in ["fedora"]:
        run_command(
            "sudo dnf install -y gcc ncurses-devel bison flex elfutils-libelf-devel openssl-devel",
            "Failed to install dependencies on Fedora."
        )
    elif distro in ["arch", "manjaro"]:
        run_command(
            "sudo pacman -Syu --noconfirm base-devel ncurses bison flex elfutils openssl",
            "Failed to install dependencies on Arch/Manjaro."
        )
    else:
        logger.error(f"Unsupported distribution: {distro}")
        exit(1)

def main():
    # Parse command-line arguments
    args = parse_args()

    # Enable verbose logging if requested
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

    # Load configuration
    config = load_config(args.config)
    KERNEL_VERSION = config.get("KERNEL_VERSION")
    KERNEL_CONFIG = config.get("KERNEL_CONFIG", {})

    if not KERNEL_VERSION:
        logger.error("KERNEL_VERSION not found in the configuration file.")
        exit(1)

    MAJOR_VERSION_DIR = get_major_version(KERNEL_VERSION)
    KERNEL_URL = f"https://cdn.kernel.org/pub/linux/kernel/{MAJOR_VERSION_DIR}/linux-{KERNEL_VERSION}.tar.xz"
    KERNEL_DIR = f"linux-{KERNEL_VERSION}"
    KERNEL_ARCHIVE = f"linux-{KERNEL_VERSION}.tar.xz"

    # Install dependencies
    logger.info("Installing build dependencies...")
    install_dependencies()

    # Download and extract kernel source
    if not os.path.exists(KERNEL_DIR) or args.clean:
        if os.path.exists(KERNEL_DIR):
            logger.info("Cleaning build directory...")
            shutil.rmtree(KERNEL_DIR)
        logger.info(f"Downloading Linux kernel {KERNEL_VERSION}...")
        download_file(KERNEL_URL, KERNEL_ARCHIVE)
        logger.info("Extracting kernel source...")
        run_command(f"tar -xf {KERNEL_ARCHIVE}", "Failed to extract kernel archive")
    else:
        logger.info(f"Using existing kernel source directory: {KERNEL_DIR}")

    os.chdir(KERNEL_DIR)

    # Configure the kernel
    logger.info("Configuring the kernel...")
    if args.predefined_config:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        predefined_config_path = os.path.join(script_dir, args.predefined_config)
        if not os.path.isfile(predefined_config_path):
            logger.error(f"The specified configuration file '{predefined_config_path}' does not exist.")
            exit(1)
        logger.info(f"Using predefined .config file from {predefined_config_path}...")
        shutil.copy(predefined_config_path, ".config")
    else:
        run_command("yes '' | make defconfig", "Failed to configure the kernel")

    # Apply additional kernel configuration options from JSON
    if KERNEL_CONFIG:
        logger.info("Applying additional kernel configuration options from JSON...")
        apply_kernel_config(KERNEL_CONFIG)

    # Resolve undefined options automatically
    logger.info("Resolving undefined configuration options with default values...")
    run_command("make olddefconfig", "Failed to resolve undefined configuration options")

    # Display the final kernel configuration in JSON format
    display_kernel_config()

    # Compile the kernel
    logger.info("Compiling the kernel (this may take a while)...")
    run_command(f"make -j{os.cpu_count()}", "Kernel compilation failed")

    # Copy vmlinux to the parent directory
    logger.info("Copying vmlinux to the parent directory...")
    shutil.copy("vmlinux", "../vmlinux")

    # Clean up temporary files
    if args.clean:
        logger.info("Cleaning up temporary files...")
        os.chdir("..")
        shutil.rmtree(KERNEL_DIR)
        os.remove(KERNEL_ARCHIVE)

    logger.info("Kernel build complete. Only vmlinux is retained in the current directory.")

if __name__ == "__main__":
    main()
