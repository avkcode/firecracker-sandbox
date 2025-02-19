.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo "  activate    - Create and activate the Firecracker API socket at /tmp/firecracker.socket."
	@echo "                This is required before starting the MicroVM."
	@echo "  deactivate  - Deactivate and clean up the Firecracker API socket."
	@echo "                Removes the socket file from /tmp."
	@echo "  net-up      - Set up networking for Firecracker MicroVM."
	@echo "                Creates a tap0 device, assigns an IP, enables IP forwarding, and sets up NAT."
	@echo "  net-down    - Clean up networking resources."
	@echo "                Removes the tap0 device and clears Firecracker-specific iptables rules."
	@echo "  up          - Start the Firecracker MicroVM using the configuration in config.json."
	@echo "  down        - Stop all Firecracker instances and clean up resources."
	@echo "                Includes stopping the VM, cleaning up networking, and deactivating the API socket."
	@echo "  help        - Show this help message."

.PHONY: activate
activate:
	@echo "Creating and activating the Firecracker API socket..."
	@rm -f /tmp/firecracker.socket
	@mkfifo /tmp/firecracker.socket
	@chmod 660 /tmp/firecracker.socket
	@echo "Firecracker API socket activated at /tmp/firecracker.socket"

.PHONY: deactivate
deactivate:
	@echo "Deactivating and cleaning up the Firecracker API socket..."
	@rm -f /tmp/firecracker.socket
	@echo "Firecracker API socket deactivated and cleaned up."

.PHONY: net-up
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
	# Step 4: Set up NAT using iptables with a dedicated chain
	@echo "Setting up NAT with iptables..."
	@sudo iptables -t nat -N FIRECRACKER-NAT || true
	@sudo iptables -t nat -A FIRECRACKER-NAT -o $(shell ip route | grep default | awk '{print $$5}') -j MASQUERADE
	@sudo iptables -t nat -A POSTROUTING -j FIRECRACKER-NAT
	@sudo iptables -N FIRECRACKER-FORWARD || true
	@sudo iptables -A FIRECRACKER-FORWARD -i tap0 -j ACCEPT
	@sudo iptables -A FIRECRACKER-FORWARD -o tap0 -j ACCEPT
	@sudo iptables -A FORWARD -j FIRECRACKER-FORWARD
	@echo "Networking setup complete. Firecracker is ready to use the tap0 device."

.PHONY: net-down
net-down:
	@echo "Cleaning up networking..."
	# Remove the tap0 device
	@sudo ip link delete tap0 || true
	# Remove Firecracker-specific iptables rules
	@echo "Removing Firecracker-specific iptables rules..."
	@sudo iptables -t nat -D POSTROUTING -j FIRECRACKER-NAT || true
	@sudo iptables -t nat -F FIRECRACKER-NAT || true
	@sudo iptables -t nat -X FIRECRACKER-NAT || true
	@sudo iptables -D FORWARD -j FIRECRACKER-FORWARD || true
	@sudo iptables -F FIRECRACKER-FORWARD || true
	@sudo iptables -X FIRECRACKER-FORWARD || true
	@echo "Networking cleanup complete."
	
.PHONY: up
up:
	@echo "Starting Firecracker MicroVM..."
	# Step 1: Start Firecracker in the background
	@echo "Launching Firecracker..."
	@firecracker --api-sock /tmp/firecracker.socket --config-file vm-config.json

.PHONY: down
down:
	@echo "Stopping all Firecracker instances..."
	@ps aux | grep '[f]irecracker' | awk '{print $$2}' | xargs -r kill -9 || true
	@echo "Cleaning up socket files..."
	@rm -f /tmp/firecracker.socket
	@echo "Firecracker cleanup complete."

.PHONY: login
login:
	@echo "Attempting to log into the running MicroVM..."
	# Step 1: Check if Firecracker is running
	@ps aux | grep '[f]irecracker' > /dev/null || (echo "Firecracker is not running. Start the VM first." && exit 1)
	# Step 2: Try connecting via serial console
	@echo "Connecting to the MicroVM via serial console..."
	@screen /dev/ttyS0 115200 || true
	@echo "Login attempt complete."
