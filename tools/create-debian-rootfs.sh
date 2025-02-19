#!/bin/bash

# Variables
ROOTFS_DIR="debian-rootfs"
ROOTFS_IMAGE="debian-rootfs.ext4"
IMAGE_SIZE="2048"  # Size in MB (2GB)

# Step 1: Install debootstrap (if not already installed)
echo "Installing debootstrap..."
sudo apt update || { echo "Failed to update package list."; exit 1; }
sudo apt install -y debootstrap || { echo "Failed to install debootstrap."; exit 1; }

# Step 2: Create a directory for the rootfs
echo "Creating a directory for the Debian rootfs..."
mkdir -p "$ROOTFS_DIR" || { echo "Failed to create rootfs directory."; exit 1; }

# Step 3: Bootstrap a minimal Debian system
echo "Bootstrapping a minimal Debian system..."
sudo debootstrap bullseye "./$ROOTFS_DIR" http://deb.debian.org/debian || { echo "Failed to bootstrap Debian system."; exit 1; }

# Step 4: Set the root password to 'root'
echo "Setting the root password to 'root'..."
sudo chroot "./$ROOTFS_DIR" /bin/bash -c "echo 'root:root' | chpasswd" || { echo "Failed to set root password."; exit 1; }

# Step 5: Package the rootfs into an ext4 image
echo "Packaging the rootfs into an ext4 image..."
dd if=/dev/zero of="$ROOTFS_IMAGE" bs=1M count="$IMAGE_SIZE" status=progress || { echo "Failed to create ext4 image."; exit 1; }
mkfs.ext4 "$ROOTFS_IMAGE" || { echo "Failed to format ext4 image."; exit 1; }

# Mount the ext4 image and copy the rootfs
echo "Copying rootfs into the ext4 image..."
sudo mount -o loop "$ROOTFS_IMAGE" /mnt || { echo "Failed to mount ext4 image."; exit 1; }
sudo cp -a "./$ROOTFS_DIR"/* /mnt/ || { echo "Failed to copy rootfs into ext4 image."; exit 1; }
sudo umount /mnt || { echo "Failed to unmount ext4 image."; exit 1; }

# Step 6: Clean up temporary files
echo "Cleaning up temporary files..."
rm -rf "$ROOTFS_DIR" wget-log* || { echo "Failed to clean up temporary files."; exit 1; }

echo "Debian rootfs created successfully: $ROOTFS_IMAGE"
