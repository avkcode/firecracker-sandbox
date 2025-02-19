#!/bin/bash

# Variables
KERNEL_VERSION="6.11"
KERNEL_URL="https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${KERNEL_VERSION}.tar.xz"
KERNEL_DIR="linux-${KERNEL_VERSION}"
KERNEL_ARCHIVE="linux-${KERNEL_VERSION}.tar.xz"

# Step 1: Install dependencies
echo "Installing build dependencies..."
sudo apt update || { echo "Failed to update package list."; exit 1; }
sudo apt install -y build-essential libncurses-dev bison flex libssl-dev libelf-dev || { echo "Failed to install dependencies."; exit 1; }

# Step 2: Download the kernel source
echo "Downloading Linux kernel ${KERNEL_VERSION}..."
wget "$KERNEL_URL" -O "$KERNEL_ARCHIVE" || { echo "Failed to download kernel source."; exit 1; }

# Step 3: Extract the archive
echo "Extracting kernel source..."
tar -xf "$KERNEL_ARCHIVE" || { echo "Failed to extract kernel archive."; exit 1; }
cd "$KERNEL_DIR" || { echo "Failed to enter kernel directory."; exit 1; }

# Step 4: Configure the kernel
echo "Configuring the kernel..."
make defconfig || { echo "Failed to configure the kernel."; exit 1; }

# Step 5: Enable additional kernel options for Firecracker compatibility
echo "Enabling CONFIG_VIRTIO_BLK, CONFIG_VIRTIO_PCI, and CONFIG_BLK_DEV_SD..."
scripts/config --set-val CONFIG_VIRTIO_BLK y
scripts/config --set-val CONFIG_VIRTIO_PCI y
scripts/config --set-val CONFIG_BLK_DEV_SD y

# Optional: Disable unnecessary modules to reduce kernel size
scripts/config --disable MODULES
scripts/config --disable BLK_DEV_BSG

# Step 6: Compile the kernel
echo "Compiling the kernel (this may take a while)..."
make -j$(nproc) || { echo "Kernel compilation failed."; exit 1; }

# Step 7: Copy the vmlinux file
echo "Copying vmlinux to the parent directory..."
cp vmlinux ../vmlinux || { echo "Failed to copy vmlinux."; exit 1; }

# Step 8: Clean up temporary files
echo "Cleaning up temporary files..."
cd ..
rm -rf "$KERNEL_DIR" "$KERNEL_ARCHIVE" wget-log* || { echo "Failed to clean up temporary files."; exit 1; }

echo "Kernel build complete. Only vmlinux is retained in the current directory."
