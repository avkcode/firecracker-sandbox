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

### Command-line Options

| Option          | Description                                                  |
|-----------------|--------------------------------------------------------------|
| `--activate`    | Create and activate the Firecracker API socket               |
| `--deactivate`  | Deactivate and clean up the Firecracker API socket           |
| `--net-up`      | Set up networking for Firecracker MicroVM                    |
| `--net-down`    | Clean up networking resources                                |
| `--start`       | Start the Firecracker MicroVM                                |
| `--stop`        | Stop all Firecracker instances and clean up resources        |
| `--login`       | Attempt to log into the running MicroVM via serial console   |
| `--config-file` | Path to the VM configuration file (default: vm-config.json)  |

## Example Workflows

### Complete Setup and Start
```bash
sudo python3 firecracker_cli.py --net-up --activate --start
```

### Stop and Clean Up Everything
```bash
sudo python3 firecracker_cli.py --stop --net-down --deactivate
```

### Start with Custom Configuration
```bash
sudo python3 firecracker_cli.py --start --config-file my-custom-config.json
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
