#!/bin/bash

# Script to download and build the latest stable Linux kernel
# This script automates the process of fetching the latest kernel version,
# downloading the source, and building it with Firecracker-compatible options

set -e  # Exit immediately if a command exits with a non-zero status

# Variables
KERNEL_DIR="linux-latest"
BUILD_DIR="$(pwd)"
TEMP_DIR=$(mktemp -d)
THREADS=$(nproc)

# Function to get the latest stable kernel version
get_latest_kernel_version() {
    echo "Fetching the latest stable kernel version..."
    
    # Try using the releases.json API directly (most reliable)
    LATEST_VERSION=$(curl -s --max-time 15 https://www.kernel.org/releases.json | grep -o '"version": *"[0-9.]*"' | head -1 | grep -o '[0-9.]*')
    
    # Debug output
    echo "API method result: '$LATEST_VERSION'"
    
    # Try using wget if curl failed
    if [ -z "$LATEST_VERSION" ]; then
        echo "Curl method failed. Trying wget..."
        LATEST_VERSION=$(wget -q -O - https://www.kernel.org/releases.json | grep -o '"version": *"[0-9.]*"' | head -1 | grep -o '[0-9.]*')
        echo "Wget method result: '$LATEST_VERSION'"
    fi
    
    # Try direct HTML parsing with different patterns
    if [ -z "$LATEST_VERSION" ]; then
        echo "JSON methods failed. Trying direct HTML parsing..."
        LATEST_VERSION=$(curl -s --max-time 15 https://www.kernel.org/ | grep -o 'The latest stable version of the Linux kernel is [0-9.]*' | grep -o '[0-9.]*')
        echo "HTML parsing result: '$LATEST_VERSION'"
    fi
    
    # Fallback to hardcoded version
    if [ -z "$LATEST_VERSION" ]; then
        echo "All methods failed. Using hardcoded fallback version 6.11.0"
        LATEST_VERSION="6.11.0"
    fi
    
    echo "Latest stable kernel version: $LATEST_VERSION"
    return 0
}

# Function to download the kernel source
download_kernel_source() {
    local version=$1
    local major_version=$(echo $version | cut -d. -f1)
    local download_file="$TEMP_DIR/linux-$version.tar.xz"
    
    echo "Downloading Linux kernel $version..."
    
    # Try primary mirror
    echo "Trying primary mirror (cdn.kernel.org)..."
    wget -q --show-progress --timeout=60 --tries=3 "https://cdn.kernel.org/pub/linux/kernel/v$major_version.x/linux-$version.tar.xz" -O "$download_file"
    
    # Check if download was successful
    if [ $? -ne 0 ] || [ ! -s "$download_file" ]; then
        echo "Primary mirror download failed. Trying alternative mirror..."
        wget -q --show-progress --timeout=60 --tries=3 "https://mirrors.edge.kernel.org/pub/linux/kernel/v$major_version.x/linux-$version.tar.xz" -O "$download_file"
        
        # Check if second attempt was successful
        if [ $? -ne 0 ] || [ ! -s "$download_file" ]; then
            echo "Alternative mirror download failed. Trying third mirror..."
            wget -q --show-progress --timeout=60 --tries=3 "https://www.kernel.org/pub/linux/kernel/v$major_version.x/linux-$version.tar.xz" -O "$download_file"
            
            # Check if third attempt was successful
            if [ $? -ne 0 ] || [ ! -s "$download_file" ]; then
                echo "ERROR: All download attempts failed. Please check your internet connection or try again later."
                return 1
            fi
        fi
    fi
    
    echo "Download completed successfully. Verifying archive..."
    # Verify the archive is valid
    if ! tar -tf "$download_file" &>/dev/null; then
        echo "ERROR: Downloaded file is not a valid tar archive."
        return 1
    fi
    
    echo "Extracting kernel source..."
    tar -xf "$download_file" -C "$BUILD_DIR"
    
    # Verify extraction was successful
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to extract kernel source."
        return 1
    fi
    
    # Rename directory to linux-latest for consistency
    if [ -d "$BUILD_DIR/linux-$version" ] && [ ! -d "$BUILD_DIR/$KERNEL_DIR" ]; then
        mv "$BUILD_DIR/linux-$version" "$BUILD_DIR/$KERNEL_DIR"
    elif [ ! -d "$BUILD_DIR/linux-$version" ]; then
        echo "ERROR: Expected directory linux-$version not found after extraction."
        return 1
    fi
    
    echo "Kernel source extracted successfully."
    return 0
}

# Function to install build dependencies
install_dependencies() {
    echo "Installing build dependencies..."
    if [ -f /etc/debian_version ]; then
        sudo apt update
        sudo apt install -y build-essential libncurses-dev bison flex libssl-dev libelf-dev
    elif [ -f /etc/redhat-release ]; then
        sudo yum install -y gcc make ncurses-devel bison flex elfutils-libelf-devel openssl-devel
    else
        echo "Unsupported distribution. Please install the following packages manually:"
        echo "- GCC and build tools"
        echo "- ncurses development libraries"
        echo "- bison and flex"
        echo "- OpenSSL development libraries"
        echo "- libelf development libraries"
    fi
    return 0
}

# Function to configure and build the kernel
build_kernel() {
    echo "Configuring the kernel for Firecracker compatibility..."
    cd "$BUILD_DIR/$KERNEL_DIR"
    
    # Start with a minimal configuration
    make defconfig
    
    # Enable required options for Firecracker
    ./scripts/config --set-val CONFIG_VIRTIO_BLK y
    ./scripts/config --set-val CONFIG_VIRTIO_NET y
    ./scripts/config --set-val CONFIG_VIRTIO_PCI y
    ./scripts/config --set-val CONFIG_VIRTIO_MMIO y
    ./scripts/config --set-val CONFIG_BLK_DEV_SD y
    ./scripts/config --set-val CONFIG_NET_9P y
    ./scripts/config --set-val CONFIG_NET_9P_VIRTIO y
    ./scripts/config --set-val CONFIG_9P_FS y
    ./scripts/config --set-val CONFIG_EXT4_FS y
    ./scripts/config --set-val CONFIG_SERIAL_8250 y
    ./scripts/config --set-val CONFIG_SERIAL_8250_CONSOLE y
    
    # Additional required drivers for Firecracker
    ./scripts/config --set-val CONFIG_VIRTIO y
    ./scripts/config --set-val CONFIG_VIRTIO_RING y
    ./scripts/config --set-val CONFIG_VIRTIO_CONSOLE y
    ./scripts/config --set-val CONFIG_SCSI_VIRTIO y
    
    # Root filesystem support
    ./scripts/config --set-val CONFIG_DEVTMPFS y
    ./scripts/config --set-val CONFIG_DEVTMPFS_MOUNT y
    ./scripts/config --set-val CONFIG_BLOCK y
    ./scripts/config --set-val CONFIG_BLK_DEV y
    
    # Additional block device support
    ./scripts/config --set-val CONFIG_ATA y
    ./scripts/config --set-val CONFIG_ATA_PIIX y
    ./scripts/config --set-val CONFIG_SATA_AHCI y
    ./scripts/config --set-val CONFIG_ATA_SFF y
    ./scripts/config --set-val CONFIG_ATA_BMDMA y
    ./scripts/config --set-val CONFIG_ATA_GENERIC y
    
    # Ensure virtio block device support is enabled
    ./scripts/config --set-val CONFIG_VIRTIO_BLK_SCSI y
    ./scripts/config --set-val CONFIG_VIRTIO_PCI_MODERN y
    ./scripts/config --set-val CONFIG_VIRTIO_PCI_LEGACY y
    
    # File systems
    ./scripts/config --set-val CONFIG_EXT4_FS_POSIX_ACL y
    ./scripts/config --set-val CONFIG_EXT4_FS_SECURITY y
    ./scripts/config --set-val CONFIG_FS_POSIX_ACL y
    
    # Critical drivers for block device detection
    ./scripts/config --set-val CONFIG_BLK_DEV_LOOP y
    ./scripts/config --set-val CONFIG_BLK_DEV_RAM y
    ./scripts/config --set-val CONFIG_VIRTIO_BLK y
    
    # Disable RAID to avoid autodetection
    ./scripts/config --set-val CONFIG_MD n
    ./scripts/config --set-val CONFIG_MD_AUTODETECT n
    
    # Answer yes to all prompts during build
    echo "Ensuring all prompts are answered with 'y'..."
    sed -i 's/.*CONFIG_VIRTIO_MMIO_CMDLINE_DEVICES.*/CONFIG_VIRTIO_MMIO_CMDLINE_DEVICES=y/' .config
    
    # Disable modules to reduce kernel size
    ./scripts/config --set-val CONFIG_MODULES n
    
    # Disable unnecessary features
    ./scripts/config --set-val CONFIG_DEBUG_INFO n
    ./scripts/config --set-val CONFIG_BLK_DEV_BSG n
    
    # Build the kernel
    echo "Building the kernel with $THREADS threads (this may take a while)..."
    make -j$THREADS
    
    # Copy the vmlinux file to the build directory
    echo "Copying vmlinux to the build directory..."
    cp vmlinux "$BUILD_DIR/vmlinux"
    
    cd "$BUILD_DIR"
    return 0
}

# Function to prompt for manual kernel version input
prompt_for_kernel_version() {
    echo "Would you like to specify a kernel version manually? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "Please enter the kernel version (e.g., 6.11.0):"
        read -r manual_version
        if [[ -n "$manual_version" ]]; then
            echo "Using manually specified kernel version: $manual_version"
            LATEST_VERSION="$manual_version"
            return 0
        fi
    fi
    return 1
}

# Main execution
echo "===== Linux Kernel Build Script for Firecracker ====="

# Install dependencies
install_dependencies || { echo "WARNING: Failed to install dependencies. Continuing anyway..."; }

# Get the latest kernel version
get_latest_kernel_version
KERNEL_VERSION=$LATEST_VERSION

# Check if kernel version was obtained
if [ -z "$KERNEL_VERSION" ]; then
    echo "ERROR: Failed to determine kernel version automatically."
    # Prompt for manual input
    if prompt_for_kernel_version; then
        KERNEL_VERSION=$LATEST_VERSION
    else
        echo "No kernel version specified. Exiting."
        exit 1
    fi
fi

echo "Using kernel version: $KERNEL_VERSION"

# Download the kernel source
if ! download_kernel_source $KERNEL_VERSION; then
    echo "ERROR: Failed to download and extract kernel source. Exiting."
    exit 1
fi

# Build the kernel
if ! build_kernel; then
    echo "ERROR: Failed to build kernel. Exiting."
    exit 1
fi

# Clean up
echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo "===== Kernel build complete! ====="
echo "The vmlinux file is available at: $BUILD_DIR/vmlinux"
echo "You can now use this kernel with Firecracker."
echo "To create a matching rootfs, run: ./tools/create-matching-rootfs.sh"
