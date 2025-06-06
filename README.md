# Firecracker MicroVM Setup

This project provides a Python CLI tool to simplify the setup, management, and cleanup of Firecracker MicroVMs. It includes networking configuration, API socket management, and VM lifecycle commands.

## Features

- **Networking Setup**: Configures `tap0` device, NAT, and IP forwarding for Firecracker.
- **API Socket Management**: Creates and cleans up the Firecracker API socket.
- **MicroVM Lifecycle**: Start and stop Firecracker instances with ease.
- **Cleanup**: Automatically removes all resources (networking, sockets, etc.) when done.
- **Command-line Interface**: Simple and intuitive CLI similar to firectl.

## Prerequisites

- **Firecracker**: Install Firecracker from [https://github.com/firecracker-microvm/firecracker](https://github.com/firecracker-microvm/firecracker).
- **Python 3.6+**: The CLI tool is written in Python.
- **Dependencies**:
  - `iptables`
  - `iproute2`
  - `mkfifo`
  - `screen` (for serial console access)
  - `sudo` privileges
- **Configuration File**: Ensure you have a valid `vm-config.json` file for Firecracker.

## Usage

Firecracker requires bootable rootfs image and Linux Kernel. To create rootfs and download prebuilt Kernel execute `create-debian-rootfs.sh` script:
```bash
bash tools/create-debian-rootfs.sh
```
It should produce `firecracker-rootfs.ext4` and `vmlinux` files.
`vm-config.json` is used for VM boot options.

If you want to compile custom Kernel use tools/download-and-build-kernel.sh script.

### Basic Commands

#### 1. Set Up Networking
```bash
sudo python3 firecracker_cli.py --net-up
```
This creates a `tap0` device, assigns an IP address, enables IP forwarding, and sets up NAT.

#### 2. Activate the Firecracker API Socket
```bash
sudo python3 firecracker_cli.py --activate
```
This creates the Firecracker API socket at `/tmp/firecracker.socket`.

#### 3. Start the MicroVM
```bash
sudo python3 firecracker_cli.py --start
```
Starts the Firecracker MicroVM using the configuration in `vm-config.json`.

#### 4. Stop the MicroVM and Clean Up
```bash
sudo python3 firecracker_cli.py --stop
```
Stops all Firecracker instances and cleans up socket files.

#### 5. Clean Up Networking
```bash
sudo python3 firecracker_cli.py --net-down
```
Removes the tap0 device and clears Firecracker-specific iptables rules.

#### 6. View Help
```bash
python3 firecracker_cli.py --help
```
Displays available commands and their descriptions.

### Global Options

These options can be used with any command to customize the behavior:

| Option           | Description                                      | Default Value        |
|------------------|--------------------------------------------------|----------------------|
| `--socket-path`  | Path to the Firecracker API socket               | /tmp/firecracker.socket |
| `--tap-device`   | Name of the TAP device to use                    | tap0                 |
| `--tap-ip`       | IP address for the TAP device                    | 192.168.1.1          |
| `--tap-netmask`  | Netmask for the TAP device                       | 24                   |
| `--guest-ip`     | IP address for the guest VM                      | 192.168.1.2          |
| `--verbose`, `-v`| Enable verbose output                            | False                |
| `--dry-run`      | Print commands without executing them            | False                |

### Command-line Commands

| Command              | Description                                                  |
|----------------------|--------------------------------------------------------------|
| `activate`           | Create and activate the Firecracker API socket               |
| `deactivate`         | Deactivate and clean up the Firecracker API socket           |
| `net-up`             | Set up networking for Firecracker MicroVM                    |
| `net-down`           | Clean up networking resources                                |
| `start`              | Start the Firecracker MicroVM                                |
| `stop`               | Stop all Firecracker instances and clean up resources        |
| `login`              | Attempt to log into the running MicroVM via serial console   |
| `setup`              | Set up everything and start the MicroVM                      |
| `teardown`           | Stop the MicroVM and clean up all resources                  |
| `generate-guest-config` | Generate a network configuration script for the guest VM  |
| `show-config`        | Show the current configuration                               |

#### Command-specific Options

| Command    | Option          | Description                                                 |
|------------|-----------------|-------------------------------------------------------------|
| `start`    | `--config-file` | Path to the VM configuration file (default: vm-config.json) |
| `setup`    | `--config-file` | Path to the VM configuration file (default: vm-config.json) |
| `generate-guest-config` | `--output`, `-o` | Output file for the guest network configuration script (default: guest-network-setup.sh) |

## Example Workflows

### Complete Setup and Start
```bash
sudo python3 firecracker_cli.py setup
```

### Stop and Clean Up Everything
```bash
sudo python3 firecracker_cli.py teardown
```

### Individual Commands
```bash
# Set up networking
sudo python3 firecracker_cli.py net-up

# Activate the socket
sudo python3 firecracker_cli.py activate

# Start with custom configuration
sudo python3 firecracker_cli.py start --config-file my-custom-config.json
```

### Using Custom Network Configuration
```bash
# Use a different TAP device and IP range
sudo python3 firecracker_cli.py --tap-device tap1 --tap-ip 192.168.2.1 --guest-ip 192.168.2.2 setup

# Generate a network configuration script for the guest VM
sudo python3 firecracker_cli.py --guest-ip 192.168.2.2 --tap-ip 192.168.2.1 generate-guest-config

# Show current configuration
sudo python3 firecracker_cli.py show-config
```

### Dry Run Mode
```bash
# See what commands would be executed without actually running them
sudo python3 firecracker_cli.py --dry-run setup
```

## Ensuring Network Functionality in the VM
After starting the Firecracker MicroVM, you need to configure networking inside the VM to ensure it has internet access and proper DNS resolution. Follow these steps:

### Configure Networking Inside the VM
Once the VM starts, log in via the serial console (using `--login` option) and run the following commands:
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

- Ensure that `vm-config.json` is properly configured for your Firecracker MicroVM.
- The `--net-up` and `--net-down` options modify system-wide networking settings. Use them with caution.
- You need `sudo` privileges for most operations (networking, socket creation, etc.).
- The tool automatically handles dependencies between operations (e.g., activating the socket before starting the VM).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
