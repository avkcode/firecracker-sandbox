.PHONY: activate deactivate net-up net-down up down help

.DEFAULT_GOAL := help

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo "  activate    - Create and activate the Firecracker API socket"
	@echo "  deactivate  - Deactivate and clean up the Firecracker API socket"
	@echo "  net-up      - Set up networking for Firecracker MicroVM"
	@echo "  net-down    - Clean up networking resources"
	@echo "  up          - Start the Firecracker MicroVM"
	@echo "  down        - Stop all Firecracker instances and clean up"
	@echo "  help        - Show this help message"

activate:
	@echo "Creating and activating the Firecracker API socket..."
	@rm -f /tmp/firecracker.socket
	@mkfifo /tmp/firecracker.socket
	@chmod 660 /tmp/firecracker.socket
	@echo "Firecracker API socket activated at /tmp/firecracker.socket"

deactivate:
	@echo "Deactivating and cleaning up the Firecracker API socket..."
	@rm -f /tmp/firecracker.socket
	@echo "Firecracker API socket deactivated and cleaned up."

net-up:
	@echo "Setting up networking for Firecracker MicroVM..."
	# Step 1: Create a tap device on the host system
	@echo "Creating tap0 device..."
	@sudo ip tuntap add tap0 mode tap || true
	@sudo ip link set tap0 up
	# Step 2: Assign an IP address to the tap0 device
	@echo "Assigning IP address to tap0..."
	@sudo ip addr add 192.168.1.1/24 dev tap0 || true
	# Step 3: Enable IP forwarding on the host system
	@echo "Enabling IP forwarding..."
	@sudo sysctl -w net.ipv4.ip_forward=1
	# Step 4: Set up NAT using iptables
	@echo "Setting up NAT with iptables..."
	@sudo iptables -t nat -A POSTROUTING -o $(shell ip route | grep default | awk '{print $$5}') -j MASQUERADE
	@sudo iptables -A FORWARD -i tap0 -j ACCEPT
	@sudo iptables -A FORWARD -o tap0 -j ACCEPT
	@echo "Networking setup complete. Firecracker is ready to use the tap0 device."

net-down:
	@echo "Cleaning up networking..."
	@sudo ip link delete tap0 || true
	@sudo iptables -t nat -F
	@sudo iptables -F
	@echo "Networking cleanup complete."

up:
	@echo "Starting Firecracker MicroVM..."
	# Step 1: Start Firecracker in the background
	@echo "Launching Firecracker..."
	@firecracker --api-sock /tmp/firecracker.socket --config-file vm-config.json

down:
	@echo "Stopping all Firecracker instances..."
	@ps aux | grep '[f]irecracker' | awk '{print $$2}' | xargs -r kill -9 || true
	@echo "Cleaning up socket files..."
	@rm -f /tmp/firecracker.socket
	@echo "Firecracker cleanup complete."
