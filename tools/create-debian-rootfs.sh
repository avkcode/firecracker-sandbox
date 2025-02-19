#!/bin/bash

# Variables
VMLINUX_URL="https://s3.amazonaws.com/spec.ccfc.min/img/quickstart_guide/x86_64/kernels/vmlinux.bin"
VMLINUX_FILE="vmlinux"

ROOTFS_DIR="debian-rootfs"
ROOTFS_IMAGE="firecracker-rootfs.ext4"
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

# Step 5: Configure networking inside the rootfs
echo "Configuring networking inside the rootfs..."
cat <<EOF | sudo tee "$ROOTFS_DIR/etc/rc.local" > /dev/null
#!/bin/sh
# Configure network interface
ip addr add 192.168.1.2/24 dev eth0
ip link set eth0 up
ip route add default via 192.168.1.1

# Configure DNS
tee /etc/resolv.conf <<DNS_EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
DNS_EOF

exit 0
EOF

# Make rc.local executable
sudo chmod +x "$ROOTFS_DIR/etc/rc.local"

# Ensure rc.local is run at boot
sudo ln -sf /etc/rc.local "$ROOTFS_DIR/etc/rc.d/S99rc.local"

# Step 6: Package the rootfs into an ext4 image
echo "Packaging the rootfs into an ext4 image..."
dd if=/dev/zero of="$ROOTFS_IMAGE" bs=1M count="$IMAGE_SIZE" status=progress || { echo "Failed to create ext4 image."; exit 1; }
mkfs.ext4 "$ROOTFS_IMAGE" || { echo "Failed to format ext4 image."; exit 1; }

# Mount the ext4 image and copy the rootfs
echo "Copying rootfs into the ext4 image..."
sudo mount -o loop "$ROOTFS_IMAGE" /mnt || { echo "Failed to mount ext4 image."; exit 1; }
sudo cp -a "./$ROOTFS_DIR"/* /mnt/ || { echo "Failed to copy rootfs into ext4 image."; exit 1; }
sudo umount /mnt || { echo "Failed to unmount ext4 image."; exit 1; }

# Step 7: Download the Firecracker-compatible kernel
echo "Downloading Firecracker-compatible kernel..."
wget "$VMLINUX_URL" -O "$VMLINUX_FILE" || { echo "Failed to download kernel."; exit 1; }
chmod +x "$VMLINUX_FILE"
echo "Kernel downloaded and made executable: $VMLINUX_FILE"

# Step 8: Clean up temporary files
echo "Cleaning up temporary files..."
rm -rf "$ROOTFS_DIR" wget-log* || { echo "Failed to clean up temporary files."; exit 1; }

echo "Debian rootfs created successfully: $ROOTFS_IMAGE"
echo "Firecracker setup complete. Kernel: $VMLINUX_FILE, Rootfs: $ROOTFS_IMAGE"
