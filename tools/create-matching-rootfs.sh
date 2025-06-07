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

# Function to check system resources
check_system_resources() {
    # Check disk space
    local required_disk_space=5000  # 5GB in MB
    local available_disk_space=$(df -m . | awk 'NR==2 {print $4}')
    
    echo "Available disk space: ${available_disk_space}MB"
    echo "Required disk space: ${required_disk_space}MB"
    
    if [ "$available_disk_space" -lt "$required_disk_space" ]; then
        echo "ERROR: Not enough disk space. Need at least ${required_disk_space}MB, but only ${available_disk_space}MB available."
        exit 1
    fi
    
    # Check available memory
    local required_memory=1024  # 1GB in MB
    local available_memory=$(free -m | awk '/^Mem:/ {print $7}')
    
    echo "Available memory: ${available_memory}MB"
    echo "Recommended memory: ${required_memory}MB"
    
    if [ "$available_memory" -lt "$required_memory" ]; then
        echo "WARNING: Low memory detected. This might cause debootstrap to fail."
        echo "Consider adding swap space or increasing available memory."
        echo "Continuing anyway in 5 seconds..."
        sleep 5
    fi
    
    echo "System resource check completed."
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
    echo "This may take a while..."
    
    # Create a temporary directory for debootstrap cache
    DEBOOTSTRAP_CACHE="$(mktemp -d)"
    echo "Using temporary cache directory: $DEBOOTSTRAP_CACHE"
    
    # Try debootstrap with different options and retry mechanism
    MAX_RETRIES=3
    RETRY_COUNT=0
    SUCCESS=false
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$SUCCESS" = false ]; do
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "Attempt $RETRY_COUNT of $MAX_RETRIES..."
        
        # Clean up any partial installation
        if [ -d "$ROOTFS_DIR/var" ]; then
            echo "Cleaning up previous partial installation..."
            rm -rf "$ROOTFS_DIR"/*
        fi
        
        # Different approaches based on retry count
        if [ $RETRY_COUNT -eq 1 ]; then
            echo "Using standard debootstrap approach..."
            debootstrap --verbose --variant=minbase --keyring=/usr/share/keyrings/debian-archive-keyring.gpg \
                --cache-dir="$DEBOOTSTRAP_CACHE" bullseye "$ROOTFS_DIR" http://deb.debian.org/debian && SUCCESS=true
        elif [ $RETRY_COUNT -eq 2 ]; then
            echo "Using alternative mirror and increased verbosity..."
            debootstrap --verbose --variant=minbase --keyring=/usr/share/keyrings/debian-archive-keyring.gpg \
                --cache-dir="$DEBOOTSTRAP_CACHE" bullseye "$ROOTFS_DIR" http://ftp.debian.org/debian && SUCCESS=true
        else
            echo "Final attempt with minimal package set and debug options..."
            DEBIAN_FRONTEND=noninteractive debootstrap --verbose --variant=minbase --include=systemd-sysv,iproute2 \
                --exclude=tasksel,tasksel-data --keyring=/usr/share/keyrings/debian-archive-keyring.gpg \
                --cache-dir="$DEBOOTSTRAP_CACHE" bullseye "$ROOTFS_DIR" http://deb.debian.org/debian && SUCCESS=true
        fi
        
        if [ "$SUCCESS" = false ]; then
            echo "Attempt $RETRY_COUNT failed. Waiting before retry..."
            sleep 5
        fi
    done
    
    # Clean up cache directory
    rm -rf "$DEBOOTSTRAP_CACHE"
    
    if [ "$SUCCESS" = false ]; then
        echo "ERROR: debootstrap failed after $MAX_RETRIES attempts."
        echo "Common issues include:"
        echo "  - Insufficient disk space or memory"
        echo "  - Network connectivity problems"
        echo "  - Corrupt package files"
        echo ""
        echo "Try the following:"
        echo "  1. Add swap space: sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile"
        echo "  2. Use a different Debian mirror"
        echo "  3. Run with --no-check-gpg option if keyring issues persist"
        exit 1
    fi
    
    echo "Debootstrap completed successfully!"
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

    # Configure serial console
    mkdir -p "$ROOTFS_DIR/etc/systemd/system/serial-getty@ttyS0.service.d"
    cat > "$ROOTFS_DIR/etc/systemd/system/serial-getty@ttyS0.service.d/override.conf" << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear %I 115200 linux
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
nameserver 1.1.1.1
nameserver 8.8.8.8
DNS_EOF

# Enable IP forwarding for better connectivity
echo 1 > /proc/sys/net/ipv4/ip_forward

# Wait for network to be ready
sleep 2

# Test network connectivity and retry if needed
for i in \$(seq 1 5); do
    if ping -c 1 -W 1 8.8.8.8 >/dev/null 2>&1; then
        echo "Network is up and running!"
        break
    fi
    echo "Retrying network setup (attempt \$i)..."
    ip link set eth0 down
    sleep 1
    ip link set eth0 up
    # Check if IP is already assigned before adding it
    if ! ip addr show dev eth0 | grep -q "192.168.1.2"; then
        ip addr add 192.168.1.2/24 dev eth0
    fi
    # Check if default route exists before adding it
    if ! ip route show | grep -q "default via 192.168.1.1"; then
        ip route add default via 192.168.1.1
    fi
    sleep 2
done

exit 0
EOF
    
    # Make rc.local executable
    chmod +x "$ROOTFS_DIR/etc/rc.local"
    
    # Configure locale to avoid warnings
    mkdir -p "$ROOTFS_DIR/etc/default"
    echo 'LANG="C.UTF-8"' > "$ROOTFS_DIR/etc/default/locale"
    
    # Generate and configure locales
    chroot "$ROOTFS_DIR" /bin/bash -c "apt update && apt install -y locales"
    echo "en_US.UTF-8 UTF-8" > "$ROOTFS_DIR/etc/locale.gen"
    chroot "$ROOTFS_DIR" /bin/bash -c "locale-gen"
    cat > "$ROOTFS_DIR/etc/environment" << EOF
LANG=C.UTF-8
LC_ALL=C.UTF-8
EOF
    
    # Install essential packages including systemd and init
    chroot "$ROOTFS_DIR" /bin/bash -c "apt update && DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends iproute2 iputils-ping net-tools curl wget vim systemd-sysv init systemd-container apt-utils"
    
    # Verify init exists
    if [ ! -f "$ROOTFS_DIR/sbin/init" ]; then
        echo "WARNING: /sbin/init not found, creating symlink to systemd"
        chroot "$ROOTFS_DIR" /bin/bash -c "ln -sf /lib/systemd/systemd /sbin/init"
    fi
    
    # Clean up apt cache to reduce image size
    chroot "$ROOTFS_DIR" /bin/bash -c "apt clean && rm -rf /var/lib/apt/lists/*"
    
    # Create a systemd service to run rc.local at boot
    mkdir -p "$ROOTFS_DIR/etc/systemd/system"
    cat > "$ROOTFS_DIR/etc/systemd/system/rc-local.service" << EOF
[Unit]
Description=/etc/rc.local Compatibility
ConditionPathExists=/etc/rc.local
After=network.target

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
    
    # Create symlink for service instead of using systemctl in chroot
    mkdir -p "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants"
    ln -sf "/etc/systemd/system/rc-local.service" "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants/rc-local.service"
    
    # Enable serial-getty service
    mkdir -p "$ROOTFS_DIR/etc/systemd/system/getty.target.wants"
    ln -sf "/lib/systemd/system/serial-getty@.service" "$ROOTFS_DIR/etc/systemd/system/getty.target.wants/serial-getty@ttyS0.service"
    
    # Make systemd not wait for devices at all
    mkdir -p "$ROOTFS_DIR/etc/systemd/system.conf.d"
    cat > "$ROOTFS_DIR/etc/systemd/system.conf.d/10-timeout.conf" << EOF
[Manager]
DefaultTimeoutStartSec=2s
DefaultDeviceTimeoutSec=1s
EOF

    # Create udev rules for console devices
    mkdir -p "$ROOTFS_DIR/etc/udev/rules.d"
    cat > "$ROOTFS_DIR/etc/udev/rules.d/90-console.rules" << EOF
KERNEL=="console", MODE="0666"
KERNEL=="ttyS0", SYMLINK+="console", MODE="0666"
EOF

    # Ensure /dev/pts is properly mounted
    mkdir -p "$ROOTFS_DIR/etc/systemd/system/dev-pts.mount.d"
    cat > "$ROOTFS_DIR/etc/systemd/system/dev-pts.mount.d/override.conf" << EOF
[Unit]
Description=Devpts file system
DefaultDependencies=no
Conflicts=umount.target
Before=local-fs.target umount.target
After=swap.target

[Mount]
What=devpts
Where=/dev/pts
Type=devpts
Options=mode=620,gid=5,nosuid,noexec,ptmxmode=000
DirectoryMode=755

[Install]
WantedBy=local-fs.target
EOF

    # Create a symlink for console
    mkdir -p "$ROOTFS_DIR/dev"
    ln -sf ttyS0 "$ROOTFS_DIR/dev/console"
    
    # Create a custom getty service for console instead of using serial-getty
    cat > "$ROOTFS_DIR/etc/systemd/system/console-getty.service" << EOF
[Unit]
Description=Console Getty
After=systemd-user-sessions.service plymouth-quit-wait.service
ConditionPathExists=/dev/console

[Service]
ExecStart=/sbin/agetty --autologin root --noclear --keep-baud console 115200,38400,9600 linux
Type=idle
Restart=always
RestartSec=0
TTYReset=no
TTYVHangup=no
IgnoreSIGPIPE=no
SendSIGHUP=yes
Environment="LANG=C.UTF-8"
Environment="LC_ALL=C.UTF-8"

[Install]
WantedBy=multi-user.target
EOF

    # Enable the custom console service
    mkdir -p "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants"
    ln -sf "/etc/systemd/system/console-getty.service" "$ROOTFS_DIR/etc/systemd/system/multi-user.target.wants/console-getty.service"

    # Disable the problematic serial-getty service
    mkdir -p "$ROOTFS_DIR/etc/systemd/system"
    ln -sf "/dev/null" "$ROOTFS_DIR/etc/systemd/system/serial-getty@ttyS0.service"
    
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

# Check system resources
check_system_resources

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
