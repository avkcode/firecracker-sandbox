#!/usr/bin/env python3
"""
Firecracker CLI - A command-line tool for managing Firecracker MicroVMs.

This tool provides a simple interface for setting up, starting, and stopping
Firecracker MicroVMs, including networking configuration and API socket management.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

import click


class Config:
    """Configuration class to store global settings."""
    def __init__(self):
        self.socket_path = "/tmp/firecracker.socket"
        self.tap_device = "tap0"
        self.tap_ip = "192.168.1.1"
        self.tap_netmask = "24"
        self.guest_ip = "192.168.1.2"
        self.verbose = False
        self.dry_run = False
        
    def __str__(self) -> str:
        """Return string representation of config."""
        return (f"Config(socket_path={self.socket_path}, "
                f"tap_device={self.tap_device}, "
                f"tap_ip={self.tap_ip}/{self.tap_netmask}, "
                f"guest_ip={self.guest_ip}, "
                f"verbose={self.verbose}, "
                f"dry_run={self.dry_run})")


# Global configuration object
config = Config()


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_color(message, color):
    """Print a message with the specified color."""
    print(f"{color}{message}{Colors.ENDC}")


def run_command(cmd, check=True, shell=False, capture_output=False):
    """
    Run a shell command and handle errors.
    
    Args:
        cmd: Command to run (list or string)
        check: Whether to raise an exception on failure
        shell: Whether to run the command in a shell
        capture_output: Whether to capture and return stdout/stderr
        
    Returns:
        CompletedProcess object
    """
    try:
        if isinstance(cmd, list) and shell:
            cmd = " ".join(cmd)
        
        cmd_str = cmd if isinstance(cmd, str) else ' '.join(cmd)
        
        if config.verbose:
            print_color(f"Running: {cmd_str}", Colors.BLUE)
        
        if config.dry_run:
            print_color(f"[DRY RUN] Would execute: {cmd_str}", Colors.YELLOW)
            # Return a mock result for dry runs
            class MockResult:
                def __init__(self):
                    self.returncode = 0
                    self.stdout = ""
                    self.stderr = ""
            return MockResult()
        
        result = subprocess.run(
            cmd,
            check=check,
            shell=shell,
            capture_output=capture_output,
            text=True if capture_output else False
        )
        return result
    except subprocess.CalledProcessError as e:
        print_color(f"Command failed with exit code {e.returncode}", Colors.RED)
        if capture_output:
            print_color(f"Error output: {e.stderr}", Colors.RED)
        if check:
            sys.exit(1)
        return e


def check_root():
    """Check if the script is running with root privileges."""
    if os.geteuid() != 0:
        print_color("This script requires root privileges. Please run with sudo.", Colors.RED)
        sys.exit(1)


def activate_socket():
    """Create and activate the Firecracker API socket."""
    print_color("Creating and activating the Firecracker API socket...", Colors.GREEN)
    
    # Remove existing socket if it exists
    if os.path.exists(config.socket_path):
        os.remove(config.socket_path)
    
    # Create a new socket
    run_command(["mkfifo", config.socket_path])
    run_command(["chmod", "660", config.socket_path])
    
    print_color(f"Firecracker API socket activated at {config.socket_path}", Colors.GREEN)


def deactivate_socket():
    """Deactivate and clean up the Firecracker API socket."""
    print_color("Deactivating and cleaning up the Firecracker API socket...", Colors.GREEN)
    
    if os.path.exists(config.socket_path):
        os.remove(config.socket_path)
    
    print_color("Firecracker API socket deactivated and cleaned up.", Colors.GREEN)


def setup_networking():
    """Set up networking for Firecracker MicroVM."""
    check_root()
    print_color("Setting up networking for Firecracker MicroVM...", Colors.GREEN)
    
    # Create tap device
    print_color(f"Creating {config.tap_device} device...", Colors.BLUE)
    run_command(["ip", "tuntap", "add", config.tap_device, "mode", "tap"], check=False)
    run_command(["ip", "link", "set", config.tap_device, "up"])
    
    # Assign IP address
    print_color(f"Assigning IP address to {config.tap_device}...", Colors.BLUE)
    run_command(["ip", "addr", "add", f"{config.tap_ip}/{config.tap_netmask}", "dev", config.tap_device], check=False)
    
    # Enable IP forwarding
    print_color("Enabling IP forwarding...", Colors.BLUE)
    run_command(["sysctl", "-w", "net.ipv4.ip_forward=1"])
    
    # Set up NAT with iptables
    print_color("Setting up NAT with iptables...", Colors.BLUE)
    
    # Get default interface
    result = run_command(["ip", "route"], capture_output=True)
    default_iface = None
    for line in result.stdout.splitlines():
        if "default" in line:
            parts = line.split()
            default_iface = parts[parts.index("dev") + 1]
            break
    
    if not default_iface:
        print_color("Could not determine default interface", Colors.RED)
        sys.exit(1)
    
    # Create and configure FIRECRACKER-NAT chain
    run_command(["iptables", "-t", "nat", "-N", "FIRECRACKER-NAT"], check=False)
    run_command(["iptables", "-t", "nat", "-A", "FIRECRACKER-NAT", "-o", default_iface, "-j", "MASQUERADE"])
    run_command(["iptables", "-t", "nat", "-A", "POSTROUTING", "-j", "FIRECRACKER-NAT"])
    
    # Create and configure FIRECRACKER-FORWARD chain
    run_command(["iptables", "-N", "FIRECRACKER-FORWARD"], check=False)
    run_command(["iptables", "-A", "FIRECRACKER-FORWARD", "-i", config.tap_device, "-j", "ACCEPT"])
    run_command(["iptables", "-A", "FIRECRACKER-FORWARD", "-o", config.tap_device, "-j", "ACCEPT"])
    run_command(["iptables", "-A", "FORWARD", "-j", "FIRECRACKER-FORWARD"])
    
    print_color(f"Networking setup complete. Firecracker is ready to use the {config.tap_device} device.", Colors.GREEN)


def cleanup_networking():
    """Clean up networking resources."""
    check_root()
    print_color("Cleaning up networking...", Colors.GREEN)
    
    # Remove the tap device
    run_command(["ip", "link", "delete", config.tap_device], check=False)
    
    # Remove Firecracker-specific iptables rules
    print_color("Removing Firecracker-specific iptables rules...", Colors.BLUE)
    run_command(["iptables", "-t", "nat", "-D", "POSTROUTING", "-j", "FIRECRACKER-NAT"], check=False)
    run_command(["iptables", "-t", "nat", "-F", "FIRECRACKER-NAT"], check=False)
    run_command(["iptables", "-t", "nat", "-X", "FIRECRACKER-NAT"], check=False)
    run_command(["iptables", "-D", "FORWARD", "-j", "FIRECRACKER-FORWARD"], check=False)
    run_command(["iptables", "-F", "FIRECRACKER-FORWARD"], check=False)
    run_command(["iptables", "-X", "FIRECRACKER-FORWARD"], check=False)
    
    print_color("Networking cleanup complete.", Colors.GREEN)


def start_microvm(config_file="vm-config.json"):
    """Start the Firecracker MicroVM."""
    print_color("Starting Firecracker MicroVM...", Colors.GREEN)
    
    # Check if config file exists
    if not os.path.exists(config_file):
        print_color(f"Config file {config_file} not found", Colors.RED)
        sys.exit(1)
    
    # Validate JSON config
    try:
        with open(config_file, 'r') as f:
            vm_config = json.load(f)
            
        # Optionally update network configuration in the VM config
        if "network-interfaces" in vm_config:
            for iface in vm_config["network-interfaces"]:
                if iface.get("host_dev_name") == "tap0" and config.tap_device != "tap0":
                    iface["host_dev_name"] = config.tap_device
                    print_color(f"Updated network interface to use {config.tap_device}", Colors.BLUE)
    except json.JSONDecodeError:
        print_color(f"Invalid JSON in config file {config_file}", Colors.RED)
        sys.exit(1)
    
    # Launch Firecracker
    print_color("Launching Firecracker...", Colors.BLUE)
    firecracker_process = subprocess.Popen(
        ["firecracker", "--api-sock", config.socket_path, "--config-file", config_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait a moment to see if it starts successfully
    time.sleep(1)
    if firecracker_process.poll() is not None:
        print_color("Firecracker failed to start", Colors.RED)
        stdout, stderr = firecracker_process.communicate()
        print_color(f"Stdout: {stdout.decode()}", Colors.RED)
        print_color(f"Stderr: {stderr.decode()}", Colors.RED)
        sys.exit(1)
    
    print_color("Firecracker MicroVM started successfully", Colors.GREEN)
    
    try:
        # Keep the process running until interrupted
        firecracker_process.wait()
    except KeyboardInterrupt:
        print_color("\nReceived interrupt, shutting down...", Colors.YELLOW)
        firecracker_process.send_signal(signal.SIGTERM)
        try:
            firecracker_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print_color("Firecracker didn't terminate gracefully, forcing shutdown...", Colors.RED)
            firecracker_process.kill()


def stop_microvm():
    """Stop all Firecracker instances and clean up resources."""
    print_color("Stopping all Firecracker instances...", Colors.GREEN)
    
    # Find and kill all Firecracker processes
    result = run_command(["ps", "aux"], capture_output=True)
    for line in result.stdout.splitlines():
        if "firecracker" in line and config.socket_path in line:
            parts = line.split()
            pid = parts[1]
            print_color(f"Killing Firecracker process with PID {pid}", Colors.BLUE)
            run_command(["kill", "-9", pid], check=False)
    
    # Clean up socket files
    print_color("Cleaning up socket files...", Colors.BLUE)
    if os.path.exists(config.socket_path):
        os.remove(config.socket_path)
    
    print_color("Firecracker cleanup complete.", Colors.GREEN)


def login_to_microvm():
    """Attempt to log into the running MicroVM via serial console."""
    print_color("Attempting to log into the running MicroVM...", Colors.GREEN)
    
    # Check if Firecracker is running
    result = run_command(["ps", "aux"], capture_output=True)
    firecracker_running = False
    for line in result.stdout.splitlines():
        if "firecracker" in line and config.socket_path in line:
            firecracker_running = True
            break
    
    if not firecracker_running:
        print_color("Firecracker is not running. Start the VM first.", Colors.RED)
        sys.exit(1)
    
    print_color("Connecting to the MicroVM via serial console...", Colors.BLUE)
    try:
        subprocess.run(["screen", "/dev/ttyS0", "115200"])
    except FileNotFoundError:
        print_color("'screen' command not found. Please install it with 'sudo apt-get install screen'", Colors.RED)
        sys.exit(1)
    except subprocess.CalledProcessError:
        print_color("Failed to connect to serial console", Colors.RED)
    
    print_color("Login attempt complete.", Colors.GREEN)


@click.group(invoke_without_command=True, context_settings=dict(help_option_names=['-h', '--help']))
@click.option('--socket-path', help='Path to the Firecracker API socket', default="/tmp/firecracker.socket")
@click.option('--tap-device', help='Name of the TAP device to use', default="tap0")
@click.option('--tap-ip', help='IP address for the TAP device', default="192.168.1.1")
@click.option('--tap-netmask', help='Netmask for the TAP device', default="24")
@click.option('--guest-ip', help='IP address for the guest VM', default="192.168.1.2")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Print commands without executing them')
@click.pass_context
def cli(ctx, socket_path, tap_device, tap_ip, tap_netmask, guest_ip, verbose, dry_run):
    """Firecracker CLI - A tool for managing Firecracker MicroVMs.
    
    This tool provides a simple interface for setting up, starting, and stopping
    Firecracker MicroVMs, including networking configuration and API socket management.
    
    Examples:
    
      # Set up networking and start a MicroVM
      sudo firecracker_cli.py net-up activate start
      
      # Stop a running MicroVM and clean up
      sudo firecracker_cli.py stop net-down deactivate
      
      # Start a MicroVM with a custom config file
      sudo firecracker_cli.py start --config-file my-config.json
      
      # Use a different TAP device and IP configuration
      sudo firecracker_cli.py --tap-device tap1 --tap-ip 192.168.2.1 setup
    """
    # Update global configuration
    config.socket_path = socket_path
    config.tap_device = tap_device
    config.tap_ip = tap_ip
    config.tap_netmask = tap_netmask
    config.guest_ip = guest_ip
    config.verbose = verbose
    config.dry_run = dry_run
    
    if verbose:
        print_color(f"Configuration: {config}", Colors.BLUE)
    
    # If no command is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command('activate')
def cmd_activate():
    """Create and activate the Firecracker API socket."""
    activate_socket()


@cli.command('deactivate')
def cmd_deactivate():
    """Deactivate and clean up the Firecracker API socket."""
    deactivate_socket()


@cli.command('net-up')
def cmd_net_up():
    """Set up networking for Firecracker MicroVM."""
    setup_networking()


@cli.command('net-down')
def cmd_net_down():
    """Clean up networking resources."""
    cleanup_networking()


@cli.command('start')
@click.option('--config-file', default="vm-config.json", help="Path to the VM configuration file")
def cmd_start(config_file):
    """Start the Firecracker MicroVM."""
    # Make sure socket is activated before starting
    if not os.path.exists("/tmp/firecracker.socket"):
        print_color("Firecracker API socket not found. Activating...", Colors.YELLOW)
        activate_socket()
    
    start_microvm(config_file)


@cli.command('stop')
def cmd_stop():
    """Stop all Firecracker instances and clean up resources."""
    stop_microvm()


@cli.command('login')
def cmd_login():
    """Attempt to log into the running MicroVM via serial console."""
    login_to_microvm()


@cli.command('setup')
@click.option('--config-file', default="vm-config.json", help="Path to the VM configuration file")
def cmd_setup(config_file):
    """Set up everything and start the MicroVM (net-up + activate + start)."""
    setup_networking()
    activate_socket()
    start_microvm(config_file)


@cli.command('teardown')
def cmd_teardown():
    """Stop the MicroVM and clean up all resources (stop + net-down + deactivate)."""
    stop_microvm()
    cleanup_networking()
    deactivate_socket()


@cli.command('generate-guest-config')
@click.option('--output', '-o', default="guest-network-setup.sh", help="Output file for the guest network configuration script")
def cmd_generate_guest_config(output):
    """Generate a network configuration script for the guest VM."""
    print_color(f"Generating guest network configuration script: {output}", Colors.GREEN)
    
    script_content = f"""#!/bin/bash
# Network configuration script for Firecracker MicroVM
# Generated by firecracker_cli.py

# Assign an IP address to the eth0 interface
ip addr add {config.guest_ip}/{config.tap_netmask} dev eth0

# Bring up the eth0 interface
ip link set eth0 up

# Add a default route via the gateway (host's tap IP)
ip route add default via {config.tap_ip}

# Configure DNS servers
cat > /etc/resolv.conf <<EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF

echo "Network configuration complete."
"""
    
    with open(output, 'w') as f:
        f.write(script_content)
    
    # Make the script executable
    os.chmod(output, 0o755)
    
    print_color(f"Guest network configuration script generated: {output}", Colors.GREEN)
    print_color(f"Copy this script to your VM and run it to configure networking.", Colors.YELLOW)


@cli.command('show-config')
def cmd_show_config():
    """Show the current configuration."""
    print_color("Current Configuration:", Colors.GREEN)
    print_color(f"Socket Path: {config.socket_path}", Colors.BLUE)
    print_color(f"TAP Device: {config.tap_device}", Colors.BLUE)
    print_color(f"TAP IP: {config.tap_ip}/{config.tap_netmask}", Colors.BLUE)
    print_color(f"Guest IP: {config.guest_ip}", Colors.BLUE)
    print_color(f"Verbose Mode: {'Enabled' if config.verbose else 'Disabled'}", Colors.BLUE)
    print_color(f"Dry Run Mode: {'Enabled' if config.dry_run else 'Disabled'}", Colors.BLUE)


if __name__ == "__main__":
    cli()
