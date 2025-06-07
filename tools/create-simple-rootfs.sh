#!/bin/bash

# Script to create a simple ext4 rootfs for Firecracker
# This creates a minimal rootfs with busybox

set -e  # Exit immediately if a command exits with a non-zero status

# Variables
ROOTFS_DIR="simple-rootfs"
ROOTFS_IMAGE="firecracker-rootfs.ext4"
IMAGE_SIZE="64"  # Size in MB

# Function to check if running as root
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "This script must be run as root or with sudo."
        exit 1
    fi
}

# Function to create a minimal rootfs
create_rootfs() {
    echo "Creating minimal rootfs directory..."
    mkdir -p "$ROOTFS_DIR"
    
    echo "Installing busybox..."
    apt update
    apt install -y busybox-static
    
    # Create basic directory structure
    mkdir -p "$ROOTFS_DIR"/{bin,sbin,etc,proc,sys,dev,tmp,root,var,run,lib}
    chmod 1777 "$ROOTFS_DIR/tmp"
    
    # Copy busybox
    cp "$(which busybox)" "$ROOTFS_DIR/bin/"
    
    # Create symlinks for busybox
    pushd "$ROOTFS_DIR/bin" > /dev/null
    for cmd in $(./busybox --list); do
        if [ "$cmd" != "busybox" ]; then
            ln -sf busybox "$cmd"
        fi
    done
    popd > /dev/null
    
    # Create basic configuration files
    echo "firecracker-vm" > "$ROOTFS_DIR/etc/hostname"
    
    cat > "$ROOTFS_DIR/etc/hosts" << EOF
127.0.0.1       localhost
127.0.1.1       firecracker-vm
EOF
    
    # Create init script
    cat > "$ROOTFS_DIR/init" << 'EOF'
#!/bin/sh
# Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || echo "devtmpfs mount failed"

# Debug information
echo "Kernel version: $(uname -r)"
echo "Available block devices:"
ls -la /dev/vd* 2>/dev/null || echo "No virtio block devices found"
cat /proc/partitions

# Create device nodes if they don't exist
[ ! -e /dev/vda ] && mknod -m 660 /dev/vda b 254 0
[ ! -e /dev/vda1 ] && mknod -m 660 /dev/vda1 b 254 1

# Configure network
ip link set eth0 up 2>/dev/null || echo "Network setup failed"
ip addr add 192.168.1.2/24 dev eth0 2>/dev/null
ip route add default via 192.168.1.1 2>/dev/null

# Set up DNS
echo "nameserver 8.8.8.8" > /etc/resolv.conf

# Create a more user-friendly environment
mkdir -p /tmp /var/log /var/run
chmod 1777 /tmp

# Create a welcome message
cat > /etc/motd << MOTD
=======================================================
Welcome to Firecracker MicroVM!
=======================================================

Network: 192.168.1.2/24 (Gateway: 192.168.1.1)
DNS: 8.8.8.8

Commands:
  - ping 8.8.8.8     - Test network connectivity
  - uname -a         - Show kernel information
  - poweroff         - Shutdown the VM

=======================================================
MOTD

# Display welcome message
cat /etc/motd
echo ""

echo "Firecracker VM is running!"
echo "Type 'poweroff' to exit"

# Start a shell
exec /bin/sh
EOF
    
    chmod +x "$ROOTFS_DIR/init"
    
    echo "Rootfs creation complete!"
}

# Function to create the ext4 image
create_ext4_image() {
    echo "Creating ext4 image file of size ${IMAGE_SIZE}MB..."
    dd if=/dev/zero of="$ROOTFS_IMAGE" bs=1M count="$IMAGE_SIZE" status=progress
    
    echo "Formatting image as ext4..."
    mkfs.ext4 -F -L "rootfs" "$ROOTFS_IMAGE"
    
    echo "Mounting image..."
    mkdir -p /mnt/rootfs
    mount -o loop "$ROOTFS_IMAGE" /mnt/rootfs
    
    echo "Copying rootfs to image..."
    cp -a "$ROOTFS_DIR"/* /mnt/rootfs/
    
    # Create device nodes
    echo "Creating essential device nodes..."
    mkdir -p /mnt/rootfs/dev
    mknod -m 622 /mnt/rootfs/dev/console c 5 1
    mknod -m 666 /mnt/rootfs/dev/null c 1 3
    mknod -m 666 /mnt/rootfs/dev/zero c 1 5
    mknod -m 666 /mnt/rootfs/dev/ptmx c 5 2
    mknod -m 666 /mnt/rootfs/dev/tty c 5 0
    mknod -m 444 /mnt/rootfs/dev/random c 1 8
    mknod -m 444 /mnt/rootfs/dev/urandom c 1 9
    
    # Create virtio block device nodes
    echo "Creating virtio block device nodes..."
    mkdir -p /mnt/rootfs/dev/block
    mknod -m 660 /mnt/rootfs/dev/vda b 254 0
    
    # Create a more robust init script
    cat > /mnt/rootfs/init << 'EOF'
#!/bin/sh
# Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev || mknod -m 660 /dev/vda b 254 0

# Debug information
echo "Kernel version: $(uname -r)"
echo "Available block devices:"
ls -la /dev/vd* /dev/block/* 2>/dev/null || echo "No block devices found"
cat /proc/partitions

# Configure network
ip link set eth0 up
ip addr add 192.168.1.2/24 dev eth0
ip route add default via 192.168.1.1

# Set up DNS
echo "nameserver 8.8.8.8" > /etc/resolv.conf

echo "Firecracker VM is running!"
echo "Type 'poweroff' to exit"

# Start a shell
exec /bin/sh
EOF
    chmod +x /mnt/rootfs/init
    
    echo "Unmounting image..."
    umount /mnt/rootfs
    rmdir /mnt/rootfs
    
    echo "Ext4 image created successfully: $ROOTFS_IMAGE"
}

# Main execution
echo "===== Simple Rootfs Creation Script for Firecracker ====="

# Check if running as root
check_root

# Create the rootfs
create_rootfs

# Create the ext4 image
create_ext4_image

# Clean up
echo "Cleaning up temporary files..."
rm -rf "$ROOTFS_DIR"

echo "===== Rootfs creation complete! ====="
echo "The rootfs image is available at: $ROOTFS_IMAGE"
echo "You can now use this rootfs with Firecracker."
