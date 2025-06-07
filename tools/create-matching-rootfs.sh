#!/bin/bash

# Script to create a Debian rootfs that matches the latest kernel
# This script creates a minimal Debian rootfs with networking configured for Firecracker

set -e  # Exit immediately if a command exits with a non-zero status

# Variables
ROOTFS_DIR="debian-rootfs"
ROOTFS_IMAGE="firecracker-rootfs.ext4"
IMAGE_SIZE="2048"  # Size in MB (2GB)

# Function to check if running as root
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "This script must be run as root or with sudo."
        exit 1
    fi
}

# Function to install dependencies
install_dependencies() {
    echo "Installing required packages..."
    apt update
    apt install -y debootstrap e2fsprogs debian-archive-keyring curl wget
    
    # Ensure we have the latest Debian keyring
    mkdir -p /usr/share/keyrings
    curl -fsSL https://ftp-master.debian.org/keys/archive-key-11.asc | gpg --dearmor -o /usr/share/keyrings/debian-archive-keyring.gpg
}

# Function to create the rootfs
create_rootfs() {
    echo "Creating Debian rootfs directory..."
    mkdir -p "$ROOTFS_DIR"
    
    echo "Running debootstrap to create a minimal Debian system..."
    debootstrap --variant=minbase --keyring=/usr/share/keyrings/debian-archive-keyring.gpg bullseye "$ROOTFS_DIR" http://deb.debian.org/debian
    
    echo "Configuring the rootfs..."
    
    # Set root password to 'root'
    echo "Setting root password to 'root'..."
    chroot "$ROOTFS_DIR" /bin/bash -c "echo 'root:root' | chpasswd"
    
    # Configure hostname
    echo "firecracker-vm" > "$ROOTFS_DIR/etc/hostname"
    
    # Configure hosts file
    cat > "$ROOTFS_DIR/etc/hosts" << EOF
127.0.0.1       localhost
127.0.1.1       firecracker-vm

# The following lines are desirable for IPv6 capable hosts
::1             localhost ip6-localhost ip6-loopback
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters
EOF
    
    # Create network directory and configure network interfaces
    mkdir -p "$ROOTFS_DIR/etc/network"
    cat > "$ROOTFS_DIR/etc/network/interfaces" << EOF
# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
auto eth0
iface eth0 inet dhcp
EOF
    
    # Create rc.local for network setup
    cat > "$ROOTFS_DIR/etc/rc.local" << EOF
#!/bin/sh
# Configure network interface
ip addr add 192.168.1.2/24 dev eth0
ip link set eth0 up
ip route add default via 192.168.1.1

# Configure DNS
cat > /etc/resolv.conf << DNS_EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
DNS_EOF

exit 0
EOF
    
    # Make rc.local executable
    chmod +x "$ROOTFS_DIR/etc/rc.local"
    
    # Install essential packages
    chroot "$ROOTFS_DIR" /bin/bash -c "apt update && apt install -y --no-install-recommends iproute2 iputils-ping net-tools curl wget vim"
    
    # Clean up apt cache to reduce image size
    chroot "$ROOTFS_DIR" /bin/bash -c "apt clean && rm -rf /var/lib/apt/lists/*"
    
    # Create a systemd service to run rc.local at boot
    mkdir -p "$ROOTFS_DIR/etc/systemd/system"
    cat > "$ROOTFS_DIR/etc/systemd/system/rc-local.service" << EOF
[Unit]
Description=/etc/rc.local Compatibility
ConditionPathExists=/etc/rc.local

[Service]
Type=forking
ExecStart=/etc/rc.local
TimeoutSec=0
StandardOutput=tty
RemainAfterExit=yes
SysVStartPriority=99

[Install]
WantedBy=multi-user.target
EOF
    
    # Enable the service
    chroot "$ROOTFS_DIR" /bin/bash -c "systemctl enable rc-local.service"
    
    echo "Rootfs creation complete!"
}

# Function to create the ext4 image
create_ext4_image() {
    echo "Creating ext4 image file of size ${IMAGE_SIZE}MB..."
    dd if=/dev/zero of="$ROOTFS_IMAGE" bs=1M count="$IMAGE_SIZE" status=progress
    
    echo "Formatting image as ext4..."
    mkfs.ext4 "$ROOTFS_IMAGE"
    
    echo "Mounting image..."
    mkdir -p /mnt/rootfs
    mount -o loop "$ROOTFS_IMAGE" /mnt/rootfs
    
    echo "Copying rootfs to image..."
    cp -a "$ROOTFS_DIR"/* /mnt/rootfs/
    
    echo "Unmounting image..."
    umount /mnt/rootfs
    rmdir /mnt/rootfs
    
    echo "Ext4 image created successfully: $ROOTFS_IMAGE"
}

# Main execution
echo "===== Debian Rootfs Creation Script for Firecracker ====="

# Check if running as root
check_root

# Install dependencies
install_dependencies

# Create the rootfs
create_rootfs

# Create the ext4 image
create_ext4_image

# Clean up
echo "Cleaning up temporary files..."
rm -rf "$ROOTFS_DIR"

echo "===== Rootfs creation complete! ====="
echo "The rootfs image is available at: $ROOTFS_IMAGE"
echo "You can now use this rootfs with Firecracker and the matching kernel."
