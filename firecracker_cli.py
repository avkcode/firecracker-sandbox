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

import click


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
        
        print_color(f"Running: {cmd if isinstance(cmd, str) else ' '.join(cmd)}", Colors.BLUE)
        
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
    socket_path = "/tmp/firecracker.socket"
    
    # Remove existing socket if it exists
    if os.path.exists(socket_path):
        os.remove(socket_path)
    
    # Create a new socket
    run_command(["mkfifo", socket_path])
    run_command(["chmod", "660", socket_path])
    
    print_color(f"Firecracker API socket activated at {socket_path}", Colors.GREEN)


def deactivate_socket():
    """Deactivate and clean up the Firecracker API socket."""
    print_color("Deactivating and cleaning up the Firecracker API socket...", Colors.GREEN)
    socket_path = "/tmp/firecracker.socket"
    
    if os.path.exists(socket_path):
        os.remove(socket_path)
    
    print_color("Firecracker API socket deactivated and cleaned up.", Colors.GREEN)


def setup_networking():
    """Set up networking for Firecracker MicroVM."""
    check_root()
    print_color("Setting up networking for Firecracker MicroVM...", Colors.GREEN)
    
    # Create tap0 device
    print_color("Creating tap0 device...", Colors.BLUE)
    run_command(["ip", "tuntap", "add", "tap0", "mode", "tap"], check=False)
    run_command(["ip", "link", "set", "tap0", "up"])
    
    # Assign IP address
    print_color("Assigning IP address to tap0...", Colors.BLUE)
    run_command(["ip", "addr", "add", "192.168.1.1/24", "dev", "tap0"], check=False)
    
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
    run_command(["iptables", "-A", "FIRECRACKER-FORWARD", "-i", "tap0", "-j", "ACCEPT"])
    run_command(["iptables", "-A", "FIRECRACKER-FORWARD", "-o", "tap0", "-j", "ACCEPT"])
    run_command(["iptables", "-A", "FORWARD", "-j", "FIRECRACKER-FORWARD"])
    
    print_color("Networking setup complete. Firecracker is ready to use the tap0 device.", Colors.GREEN)


def cleanup_networking():
    """Clean up networking resources."""
    check_root()
    print_color("Cleaning up networking...", Colors.GREEN)
    
    # Remove the tap0 device
    run_command(["ip", "link", "delete", "tap0"], check=False)
    
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
            json.load(f)
    except json.JSONDecodeError:
        print_color(f"Invalid JSON in config file {config_file}", Colors.RED)
        sys.exit(1)
    
    # Launch Firecracker
    print_color("Launching Firecracker...", Colors.BLUE)
    firecracker_process = subprocess.Popen(
        ["firecracker", "--api-sock", "/tmp/firecracker.socket", "--config-file", config_file],
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
        if "firecracker" in line and "/tmp/firecracker.socket" in line:
            parts = line.split()
            pid = parts[1]
            print_color(f"Killing Firecracker process with PID {pid}", Colors.BLUE)
            run_command(["kill", "-9", pid], check=False)
    
    # Clean up socket files
    print_color("Cleaning up socket files...", Colors.BLUE)
    if os.path.exists("/tmp/firecracker.socket"):
        os.remove("/tmp/firecracker.socket")
    
    print_color("Firecracker cleanup complete.", Colors.GREEN)


def login_to_microvm():
    """Attempt to log into the running MicroVM via serial console."""
    print_color("Attempting to log into the running MicroVM...", Colors.GREEN)
    
    # Check if Firecracker is running
    result = run_command(["ps", "aux"], capture_output=True)
    firecracker_running = False
    for line in result.stdout.splitlines():
        if "firecracker" in line and "/tmp/firecracker.socket" in line:
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
@click.pass_context
def cli(ctx):
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
    """
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


if __name__ == "__main__":
    cli()
