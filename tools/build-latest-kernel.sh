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
    
    # Method 1: Direct parsing of kernel.org HTML
    LATEST_VERSION=$(curl -s --max-time 10 https://www.kernel.org/ | grep -A 1 "latest_stable" | grep -o 'Linux [0-9.]*' | grep -o '[0-9.]*')
    
    # Debug output
    echo "Method 1 result: '$LATEST_VERSION'"
    
    # Method 2: Using releases.json API
    if [ -z "$LATEST_VERSION" ]; then
        echo "Method 1 failed. Trying releases.json API..."
        LATEST_VERSION=$(curl -s --max-time 10 https://www.kernel.org/releases.json | grep -o '"latest_stable": *"[0-9.]*"' | grep -o '[0-9.]*')
        echo "Method 2 result: '$LATEST_VERSION'"
    fi
    
    # Method 3: Using a different parsing approach
    if [ -z "$LATEST_VERSION" ]; then
        echo "Method 2 failed. Trying alternative parsing..."
        LATEST_VERSION=$(curl -s --max-time 10 https://www.kernel.org/ | grep -o 'Latest stable kernel version is [0-9.]*' | grep -o '[0-9.]*')
        echo "Method 3 result: '$LATEST_VERSION'"
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

# Main execution
echo "===== Linux Kernel Build Script for Firecracker ====="

# Install dependencies
install_dependencies || { echo "WARNING: Failed to install dependencies. Continuing anyway..."; }

# Get the latest kernel version
get_latest_kernel_version
KERNEL_VERSION=$LATEST_VERSION

# Check if kernel version was obtained
if [ -z "$KERNEL_VERSION" ]; then
    echo "ERROR: Failed to determine kernel version. Exiting."
    exit 1
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
