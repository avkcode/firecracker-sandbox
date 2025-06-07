#!/bin/bash
# Script to set up networking for Firecracker VM

set -e

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root or with sudo."
    exit 1
fi

# Create a tap device
ip tuntap add tap0 mode tap
ip addr add 192.168.1.1/24 dev tap0
ip link set tap0 up

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Get the main network interface
MAIN_IF=$(ip route | grep default | awk '{print $5}')
if [ -z "$MAIN_IF" ]; then
    echo "Could not determine main network interface."
    echo "Please manually set up NAT rules."
    exit 1
fi

echo "Using $MAIN_IF as the main network interface."

# Set up NAT
iptables -t nat -A POSTROUTING -o "$MAIN_IF" -j MASQUERADE
iptables -A FORWARD -i tap0 -o "$MAIN_IF" -j ACCEPT
iptables -A FORWARD -i "$MAIN_IF" -o tap0 -j ACCEPT

echo "Network setup complete!"
echo "Firecracker VM should now have internet access."
echo "To clean up after use, run:"
echo "  ip link delete tap0"
echo "  iptables -t nat -D POSTROUTING -o $MAIN_IF -j MASQUERADE"
echo "  iptables -D FORWARD -i tap0 -o $MAIN_IF -j ACCEPT"
echo "  iptables -D FORWARD -i $MAIN_IF -o tap0 -j ACCEPT"
