# Firecracker MicroVM Setup

This project provides a set of `Makefile` targets to simplify the setup, management, and cleanup of Firecracker MicroVMs. It includes networking configuration, API socket management, and VM lifecycle commands.

## Features

- **Networking Setup**: Configures `tap0` device, NAT, and IP forwarding for Firecracker.
- **API Socket Management**: Creates and cleans up the Firecracker API socket.
- **MicroVM Lifecycle**: Start and stop Firecracker instances with ease.
- **Cleanup**: Automatically removes all resources (networking, sockets, etc.) when done.

## Prerequisites

- **Firecracker**: Install Firecracker from [https://github.com/firecracker-microvm/firecracker](https://github.com/firecracker-microvm/firecracker).
- **Dependencies**:
  - `iptables`
  - `iproute2`
  - `mkfifo`
  - `sudo` privileges
- **Configuration File**: Ensure you have a valid `config.json` file for Firecracker.

## Usage

### 1. Set Up Networking
```bash
make net-up
```
This creates a `tap0` device, assigns an IP address, enables IP forwarding, and sets up NAT.

### 2. Activate the Firecracker API Socket
```bash
make activate
```
This creates the Firecracker API socket at `/tmp/firecracker.socket`.

### 3. Start the MicroVM
```bash
make up
```
Starts the Firecracker MicroVM using the configuration in `config.json`.

### 4. Stop the MicroVM and Clean Up
```bash
make down
```
Stops all Firecracker instances, cleans up networking resources, and deactivates the API socket.

### 5. View Help
```bash
make help
```
Displays available `Makefile` targets and their descriptions.

## Makefile Targets

| Target       | Description                                                                 |
|--------------|-----------------------------------------------------------------------------|
| `activate`   | Create and activate the Firecracker API socket at `/tmp/firecracker.socket`. |
| `deactivate` | Deactivate and clean up the Firecracker API socket.                         |
| `net-up`     | Set up networking for Firecracker MicroVM (tap0 device, NAT, IP forwarding). |
| `net-down`   | Clean up networking resources (remove tap0 device, clear iptables rules).    |
| `up`         | Start the Firecracker MicroVM.                                             |
| `down`       | Stop all Firecracker instances and clean up resources.                      |
| `help`       | Show this help message.                                                    |

## Example Workflow

```bash
# Step 1: Set up networking
make net-up

# Step 2: Activate the API socket
make activate

# Step 3: Start the MicroVM
make up

# Step 4: Stop the MicroVM and clean up
make down
```

## Ensuring Network Functionality in the VM
After starting the Firecracker MicroVM, you need to configure networking inside the VM to ensure it has internet access and proper DNS resolution. Follow these steps:

1. Configure Networking Inside the VM
Once the VM starts, log in via SSH or the serial console and run the following commands:
```
# Assign an IP address to the eth0 interface
ip addr add 192.168.1.2/24 dev eth0

# Bring up the eth0 interface
ip link set eth0 up

# Add a default route via the gateway (host's tap0 IP)
ip route add default via 192.168.1.1

# Configure DNS servers
tee /etc/resolv.conf <<EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF
```

## Notes

- Ensure that `config.json` is properly configured for your Firecracker MicroVM.
- The `net-up` and `net-down` targets modify system-wide networking settings. Use them with caution.
- You may need `sudo` privileges for certain commands (e.g., `iptables`, `ip`).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
