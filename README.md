# Firecracker MicroVM Sandbox

This project provides a set of `Makefile` targets to simplify the setup, management, and cleanup of Firecracker MicroVMs. It includes networking configuration, VM lifecycle commands, and console access.

## Features

- **Networking Setup**: Configures `tap0` device, NAT, and IP forwarding for Firecracker.
- **MicroVM Lifecycle**: Start and stop Firecracker instances with ease.
- **Console Access**: Connect to the running VM's console.
- **VM Monitoring**: List running VMs and their resource usage.
- **Snapshots**: Create and restore VM snapshots.
- **Cleanup**: Automatically removes all resources when done.

## Prerequisites

- **Firecracker**: Install Firecracker from [https://github.com/firecracker-microvm/firecracker](https://github.com/firecracker-microvm/firecracker).
- **Dependencies**:
  - `iptables`
  - `iproute2`
  - `screen`
  - `sudo` privileges
- **Configuration File**: Ensure you have a valid `vm-config.json` file for Firecracker. This is required before starting the MicroVM.

## Usage

Firecracker requires a bootable rootfs image and Linux Kernel. You have several options to create these:

### Option 1: Use the build scripts to create the kernel and rootfs
```bash
# Build the latest stable kernel
make build-kernel

# Create a simple rootfs (requires sudo)
make build-simple-rootfs

# Or build both at once
make build-all
```

These scripts will produce `firecracker-rootfs.ext4` and `vmlinux` files.
`vm-config.json` is used for VM boot options.

### Starting and Managing the VM

```bash
# Start the VM in detached mode
make up-detached

# Connect to the VM console (exit with Ctrl+a followed by d to detach)
make login

# List running VMs
make list-vms

# View network information
make net-info

# Check console logs
make console-log

# Stop the VM and clean up
make down
```

## Makefile Targets

| Target            | Description                                                           |
|-------------------|-----------------------------------------------------------------------|
| `net-up`          | Set up networking for Firecracker MicroVM.                            |
| `net-down`        | Clean up networking resources.                                        |
| `up`              | Start the Firecracker MicroVM in interactive mode.                    |
| `up-detached`     | Start the Firecracker MicroVM in the background.                      |
| `down`            | Stop all Firecracker instances and clean up resources.                |
| `login`           | Connect to the running MicroVM console.                               |
| `list-vms`        | List all running Firecracker MicroVMs with their details.             |
| `net-info`        | Display network information for running MicroVMs.                     |
| `console-log`     | Display the console log from the running VM.                          |
| `snapshot`        | Create a snapshot of the running MicroVM.                             |
| `restore`         | Restore a MicroVM from a snapshot (use with SNAPSHOT=name).           |
| `build-kernel`    | Build the latest stable Linux kernel for Firecracker.                 |
| `build-all`       | Build both kernel and rootfs for Firecracker.                         |
| `help`            | Show help message with available targets.                             |

## Example Workflow

```bash
# Start the MicroVM in detached mode
make up-detached

# Connect to the MicroVM console
make login

# Check running VMs
make list-vms

# Create a snapshot of the running VM
make snapshot

# Stop the MicroVM and clean up
make down

# Restore from a snapshot
make restore SNAPSHOT=20250609_123456
```

## Ensuring Network Functionality in the VM

The rootfs created with `tools/create-matching-rootfs.sh` is pre-configured with networking. If you're using a custom rootfs, configure networking inside the VM:

```
# Assign an IP address to the eth0 interface
ip addr add 192.168.1.2/24 dev eth0

# Bring up the eth0 interface
ip link set eth0 up

# Add a default route via the gateway
ip route add default via 192.168.1.1

# Configure DNS servers
echo "nameserver 8.8.8.8" > /etc/resolv.conf
```

## Exiting the VM Console

When connected to the VM console via `make login`, you can exit without shutting down the VM:

1. Press `Ctrl+a` followed by `d` to detach from the screen session
2. This returns you to your host shell while leaving the VM running
3. You can reconnect later with `make login`

## Monitoring Network Traffic

You can monitor network traffic within your Firecracker MicroVM using tools like `tcpdump` or `tshark`. This is useful for debugging network issues, analyzing protocols, or monitoring communication between services.

### Using tcpdump

1. First, install tcpdump inside the VM:
```
apt-get update
apt-get install -y tcpdump
```

2. Basic usage to capture traffic on the eth0 interface:
```
# Capture and display packets in real-time
tcpdump -i eth0

# Capture specific protocols (e.g., HTTP traffic)
tcpdump -i eth0 port 80

# Save captures to a file for later analysis
tcpdump -i eth0 -w capture.pcap

# Capture with verbose output and readable timestamps
tcpdump -i eth0 -v -tttt
```

### Using Wireshark/tshark

For more advanced analysis, you can use tshark (command-line version of Wireshark):

1. Install tshark inside the VM:
```
apt-get update
apt-get install -y tshark
```

2. Basic usage:
```
# Capture packets with detailed protocol information
tshark -i eth0

# Filter for specific protocols
tshark -i eth0 -f "port 443"

# Save capture to a file in Wireshark format
tshark -i eth0 -w capture.pcapng

# Analyze a previously saved capture file
tshark -r capture.pcapng
```

### Remote Analysis Workflow

For more detailed analysis with the Wireshark GUI:

1. Capture traffic inside the VM:
```
tcpdump -i eth0 -w /tmp/capture.pcap
```

2. Copy the capture file to your host:
```
# From your host machine
scp root@192.168.1.2:/tmp/capture.pcap ./
```

3. Open the capture file with Wireshark on your host system for detailed analysis.

### Monitoring Traffic from the Host Machine

You can also monitor the VM's network traffic directly from the host machine:

1. Install tcpdump on the host:
```
sudo apt-get update
sudo apt-get install -y tcpdump
```

2. Monitor traffic on the tap interface:
```
# Monitor all traffic on the tap0 interface
sudo tcpdump -i tap0

# Filter traffic to/from the VM's IP address
sudo tcpdump -i tap0 host 192.168.1.2

# Monitor specific ports
sudo tcpdump -i tap0 host 192.168.1.2 and port 80
```

3. For continuous monitoring with real-time statistics:
```
# Install iftop
sudo apt-get install -y iftop

# Monitor bandwidth usage on tap0
sudo iftop -i tap0
```

4. Using Wireshark on the host:
```
# Install Wireshark
sudo apt-get install -y wireshark

# Capture traffic (requires root)
sudo wireshark -i tap0 -k
```

This approach allows you to monitor VM traffic without installing additional tools inside the VM or interrupting its operation.

## Setting Up SSH Access

To enable SSH access to your Firecracker MicroVM:

### 1. Inside the VM

Install and configure SSH server in the VM:

```
# Install SSH server
apt-get update
apt-get install -y openssh-server

# Configure SSH to allow root login
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# Set a password for root (if not already set)
passwd root

# Restart SSH service
systemctl restart ssh
```

### 2. From the Host

Connect to the VM using SSH:

```
ssh root@192.168.1.2
```

### 3. Using SSH Keys (Recommended)

For more secure access, use SSH keys:

```
# On the host, generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096

# Copy your public key to the VM
ssh-copy-id root@192.168.1.2

# Or manually add the key to the VM
cat ~/.ssh/id_rsa.pub | ssh root@192.168.1.2 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 4. Port Forwarding (Optional)

If you want to access the VM from outside the host:

```
# On the host, set up port forwarding
sudo iptables -t nat -A PREROUTING -p tcp --dport 2222 -j DNAT --to-destination 192.168.1.2:22
sudo iptables -t nat -A POSTROUTING -j MASQUERADE

# Connect from another machine
ssh -p 2222 root@<host-ip-address>
```

## Notes

- Ensure that `vm-config.json` is properly configured for your Firecracker MicroVM.
- The `net-up` and `net-down` targets modify system-wide networking settings. Use them with caution.
- You may need `sudo` privileges for certain commands.
- Use `screen` to manage VM console sessions.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
