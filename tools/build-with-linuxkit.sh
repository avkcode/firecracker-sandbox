#!/bin/bash

# Variables
CONFIG_FILE="firecracker.yml"
VMLINUX_OUTPUT="firecracker-kernel"
ROOTFS_OUTPUT="firecracker-initrd.img"

# Step 1: Build the kernel and rootfs
echo "Building kernel and rootfs with LinuxKit..."
linuxkit build $CONFIG_FILE

# Step 2: Copy files to Firecracker directory
echo "Copying files to Firecracker directory..."
mv $VMLINUX_OUTPUT vmlinux
mv $ROOTFS_OUTPUT rootfs.ext4

echo "Build complete. Updated vmlinux and rootfs are ready for Firecracker."
