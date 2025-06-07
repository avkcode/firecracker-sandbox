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
    LATEST_VERSION=$(curl -s https://www.kernel.org/ | grep -A 1 "latest_link" | grep -o 'Linux [0-9.]*' | grep -o '[0-9.]*')
    echo "Latest stable kernel version: $LATEST_VERSION"
    return 0
}

# Function to download the kernel source
download_kernel_source() {
    local version=$1
    local major_version=$(echo $version | cut -d. -f1)
    
    echo "Downloading Linux kernel $version..."
    wget -q --show-progress "https://cdn.kernel.org/pub/linux/kernel/v$major_version.x/linux-$version.tar.xz" -O "$TEMP_DIR/linux-$version.tar.xz"
    
    echo "Extracting kernel source..."
    tar -xf "$TEMP_DIR/linux-$version.tar.xz" -C "$BUILD_DIR"
    
    # Rename directory to linux-latest for consistency
    if [ -d "$BUILD_DIR/linux-$version" ] && [ ! -d "$BUILD_DIR/$KERNEL_DIR" ]; then
        mv "$BUILD_DIR/linux-$version" "$BUILD_DIR/$KERNEL_DIR"
    fi
    
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
install_dependencies

# Get the latest kernel version
get_latest_kernel_version
KERNEL_VERSION=$LATEST_VERSION

# Download the kernel source
download_kernel_source $KERNEL_VERSION

# Build the kernel
build_kernel

# Clean up
echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo "===== Kernel build complete! ====="
echo "The vmlinux file is available at: $BUILD_DIR/vmlinux"
echo "You can now use this kernel with Firecracker."
echo "To create a matching rootfs, run: ./tools/create-matching-rootfs.sh"
