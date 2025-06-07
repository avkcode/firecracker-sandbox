#!/bin/bash

# VM Manager Script for Firecracker
# This script provides a simple interface for managing Firecracker VMs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display help
show_help() {
    echo -e "${BLUE}Firecracker VM Manager${NC}"
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start       Start the VM"
    echo "  stop        Stop the VM"
    echo "  restart     Restart the VM"
    echo "  status      Check VM status"
    echo "  rebuild     Rebuild the rootfs and restart VM"
    echo "  network     Setup networking"
    echo "  help        Show this help message"
    echo ""
}

# Function to check if VM is running
is_vm_running() {
    if pgrep -f "firecracker" > /dev/null; then
        return 0 # true
    else
        return 1 # false
    fi
}

# Function to start VM
start_vm() {
    echo -e "${BLUE}Starting Firecracker VM...${NC}"
    
    # Check if VM is already running
    if is_vm_running; then
        echo -e "${YELLOW}VM is already running.${NC}"
        return
    fi
    
    # Setup networking
    setup_network
    
    # Start VM
    echo -e "${GREEN}Launching VM...${NC}"
    firecracker --api-sock /tmp/firecracker.socket --config-file vm-config.json &
    
    # Wait a moment for VM to start
    sleep 2
    
    if is_vm_running; then
        echo -e "${GREEN}VM started successfully!${NC}"
    else
        echo -e "${RED}Failed to start VM.${NC}"
    fi
}

# Function to stop VM
stop_vm() {
    echo -e "${BLUE}Stopping Firecracker VM...${NC}"
    
    if ! is_vm_running; then
        echo -e "${YELLOW}No VM is currently running.${NC}"
        return
    fi
    
    echo -e "${GREEN}Stopping VM...${NC}"
    pkill -f "firecracker" || true
    
    # Clean up socket
    rm -f /tmp/firecracker.socket
    
    echo -e "${GREEN}VM stopped.${NC}"
}

# Function to setup networking
setup_network() {
    echo -e "${BLUE}Setting up networking...${NC}"
    
    # Create tap device if it doesn't exist
    if ! ip link show tap0 &> /dev/null; then
        sudo ip tuntap add tap0 mode tap
        sudo ip link set tap0 up
        sudo ip addr add 192.168.1.1/24 dev tap0
        
        # Enable IP forwarding
        sudo sysctl -w net.ipv4.ip_forward=1
        
        # Setup NAT
        sudo iptables -t nat -A POSTROUTING -o $(ip route | grep default | awk '{print $5}') -j MASQUERADE
        sudo iptables -A FORWARD -i tap0 -o $(ip route | grep default | awk '{print $5}') -j ACCEPT
        sudo iptables -A FORWARD -i $(ip route | grep default | awk '{print $5}') -o tap0 -j ACCEPT
        
        echo -e "${GREEN}Network setup complete.${NC}"
    else
        echo -e "${YELLOW}Network already set up.${NC}"
    fi
}

# Function to rebuild rootfs and restart VM
rebuild_vm() {
    echo -e "${BLUE}Rebuilding rootfs and restarting VM...${NC}"
    
    # Stop VM if running
    if is_vm_running; then
        stop_vm
    fi
    
    # Rebuild rootfs
    echo -e "${GREEN}Building new rootfs...${NC}"
    sudo bash tools/create-simple-rootfs.sh
    
    # Start VM
    start_vm
}

# Function to check VM status
check_status() {
    if is_vm_running; then
        echo -e "${GREEN}VM Status: Running${NC}"
        echo "Process info:"
        ps aux | grep "[f]irecracker"
    else
        echo -e "${YELLOW}VM Status: Not running${NC}"
    fi
}

# Main execution
case "$1" in
    start)
        start_vm
        ;;
    stop)
        stop_vm
        ;;
    restart)
        stop_vm
        sleep 1
        start_vm
        ;;
    status)
        check_status
        ;;
    rebuild)
        rebuild_vm
        ;;
    network)
        setup_network
        ;;
    help|*)
        show_help
        ;;
esac
