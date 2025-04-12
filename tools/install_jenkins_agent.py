#!/usr/bin/env python3
import os
import sys
import subprocess
import platform
import argparse
import shutil
import requests
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_color(message: str, color: str) -> None:
    """Print colored message to terminal."""
    print(f"{color}{message}{Colors.ENDC}")

def check_linux() -> bool:
    """Check if the system is Linux."""
    if platform.system().lower() != 'linux':
        print_color("Error: This script is only for Linux systems.", Colors.FAIL)
        return False
    return True

def check_dependencies() -> Tuple[bool, List[str]]:
    """Check for required dependencies."""
    missing = []
    required = ['curl', 'wget', 'java']

    for dep in required:
        if not shutil.which(dep):
            missing.append(dep)

    return (len(missing) == 0, missing)

def get_system_info() -> Tuple[str, str]:
    """Get Linux distribution and architecture."""
    try:
        # Get distribution
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release') as f:
                distro_info = f.read()
            if 'debian' in distro_info.lower() or 'ubuntu' in distro_info.lower():
                distro = 'deb'
            elif 'rhel' in distro_info.lower() or 'centos' in distro_info.lower() or 'fedora' in distro_info.lower():
                distro = 'rpm'
            else:
                distro = 'deb'  # default to deb
        else:
            distro = 'deb'  # default to deb

        # Get architecture
        arch = platform.machine().lower()
        if arch in ['x86_64', 'amd64']:
            arch = 'amd64'
        elif arch.startswith('arm'):
            arch = 'arm'
        elif arch.startswith('aarch64'):
            arch = 'arm64'
        else:
            arch = 'amd64'  # default to amd64

        return (distro, arch)
    except Exception as e:
        print_color(f"Error detecting system info: {e}", Colors.WARNING)
        return ('deb', 'amd64')  # defaults

def download_with_progress(url: str, dest: str) -> bool:
    """Download file with progress display."""
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            start_time = time.time()

            with open(dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        elapsed = time.time() - start_time
                        speed = downloaded / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                        percent = (downloaded / total_size) * 100 if total_size > 0 else 0
                        sys.stdout.write(
                            f"\rDownloading... {percent:.1f}% "
                            f"({downloaded/(1024*1024):.1f}MB/{total_size/(1024*1024):.1f}MB) "
                            f"at {speed:.1f}MB/s"
                        )
                        sys.stdout.flush()
            print()
            return True
    except Exception as e:
        print_color(f"\nDownload failed: {e}", Colors.FAIL)
        return False

def install_java() -> bool:
    """Install Java if not already installed."""
    try:
        if shutil.which('java'):
            java_version = subprocess.check_output(['java', '-version'], stderr=subprocess.STDOUT)
            print_color(f"Java is already installed:\n{java_version.decode()}", Colors.OKGREEN)
            return True

        print_color("\nInstalling Java (OpenJDK 11)...", Colors.HEADER)
        
        distro, _ = get_system_info()
        if distro == 'deb':
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'openjdk-11-jdk'], check=True)
        else:
            subprocess.run(['sudo', 'yum', 'install', '-y', 'java-11-openjdk-devel'], check=True)
        
        print_color("Java installed successfully!", Colors.OKGREEN)
        return True
    except subprocess.CalledProcessError as e:
        print_color(f"Error installing Java: {e}", Colors.FAIL)
        return False

def create_agent_directory(agent_dir: str = '/opt/jenkins-agent') -> bool:
    """Create directory for Jenkins agent."""
    try:
        print_color(f"\nCreating Jenkins agent directory at {agent_dir}...", Colors.HEADER)
        os.makedirs(agent_dir, exist_ok=True)
        subprocess.run(['sudo', 'chmod', '755', agent_dir], check=True)
        return True
    except Exception as e:
        print_color(f"Error creating agent directory: {e}", Colors.FAIL)
        return False

def download_agent_jar(
    jenkins_url: str,
    agent_dir: str = '/opt/jenkins-agent',
    force: bool = False
) -> bool:
    """Download the agent JAR file from Jenkins controller."""
    try:
        agent_jar_path = os.path.join(agent_dir, 'agent.jar')
        
        if os.path.exists(agent_jar_path) and not force:
            print_color("Agent JAR already exists. Use --force to redownload.", Colors.WARNING)
            return True

        print_color("\nDownloading agent JAR from Jenkins controller...", Colors.HEADER)
        
        agent_url = f"{jenkins_url.rstrip('/')}/jnlpJars/agent.jar"
        if not download_with_progress(agent_url, agent_jar_path):
            return False
            
        subprocess.run(['sudo', 'chmod', '755', agent_jar_path], check=True)
        return True
    except Exception as e:
        print_color(f"Error downloading agent JAR: {e}", Colors.FAIL)
        return False

def create_agent_service(
    agent_name: str,
    jenkins_url: str,
    secret: str,
    agent_dir: str = '/opt/jenkins-agent',
    user: str = 'jenkins-agent',
    java_opts: str = ''
) -> bool:
    """Create a systemd service for the Jenkins agent."""
    try:
        print_color("\nCreating systemd service for Jenkins agent...", Colors.HEADER)
        
        # Create user if not exists
        if not subprocess.run(['id', user], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            subprocess.run(['sudo', 'useradd', '-m', '-d', agent_dir, '-s', '/bin/bash', user], check=True)
        
        # Set ownership
        subprocess.run(['sudo', 'chown', '-R', f'{user}:{user}', agent_dir], check=True)
        
        # Create service file
        service_content = f"""
[Unit]
Description=Jenkins Agent
After=network.target

[Service]
User={user}
WorkingDirectory={agent_dir}
Environment="JAVA_OPTS={java_opts}"
ExecStart=/usr/bin/java {java_opts} -jar agent.jar -jnlpUrl {jenkins_url}/computer/{agent_name}/slave-agent.jnlp -secret {secret} -workDir "{agent_dir}/work"
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
"""
        
        service_path = f'/etc/systemd/system/jenkins-agent.service'
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(service_content)
            temp_path = temp_file.name
        
        subprocess.run(['sudo', 'mv', temp_path, service_path], check=True)
        subprocess.run(['sudo', 'chmod', '644', service_path], check=True)
        
        # Reload and enable service
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', 'jenkins-agent'], check=True)
        
        print_color("Jenkins agent service created successfully!", Colors.OKGREEN)
        return True
    except Exception as e:
        print_color(f"Error creating agent service: {e}", Colors.FAIL)
        return False

def install_jenkins_agent(
    agent_name: str,
    jenkins_url: str,
    secret: str,
    agent_dir: str = '/opt/jenkins-agent',
    user: str = 'jenkins-agent',
    java_opts: str = '',
    force: bool = False
) -> bool:
    """
    Install and configure Jenkins agent on Linux.
    
    Args:
        agent_name: Name of the agent (must match name on Jenkins controller)
        jenkins_url: URL of Jenkins controller (e.g., https://jenkins.example.com)
        secret: Agent secret from Jenkins controller
        agent_dir: Directory to install agent files
        user: User to run agent as
        java_opts: Additional Java options
        force: Force reinstall even if already installed
    Returns:
        bool: True if installation succeeded
    """
    try:
        # Check if already installed
        if os.path.exists(f'/etc/systemd/system/jenkins-agent.service') and not force:
            print_color("Jenkins agent is already installed. Use --force to reinstall.", Colors.WARNING)
            return True

        # Install Java
        if not install_java():
            return False

        # Create agent directory
        if not create_agent_directory(agent_dir):
            return False

        # Download agent JAR
        if not download_agent_jar(jenkins_url, agent_dir, force):
            return False

        # Create systemd service
        if not create_agent_service(agent_name, jenkins_url, secret, agent_dir, user, java_opts):
            return False

        print_color("\nJenkins Agent installation complete!", Colors.OKGREEN)
        print("\nNext steps:")
        print("1. On your Jenkins controller, make sure you have an agent/node configured with the same name")
        print("2. Start the agent with:")
        print("   sudo systemctl start jenkins-agent")
        print("3. Check status with:")
        print("   sudo systemctl status jenkins-agent")
        print("4. View logs with:")
        print("   journalctl -u jenkins-agent -f")

        return True
    except Exception as e:
        print_color(f"An unexpected error occurred: {e}", Colors.FAIL)
        return False

def main():
    if not check_linux():
        sys.exit(1)

    deps_ok, missing_deps = check_dependencies()
    if not deps_ok:
        print_color(
            f"Missing dependencies: {', '.join(missing_deps)}\n"
            "Please install them first (e.g., 'sudo apt install curl wget openjdk-11-jdk')",
            Colors.FAIL
        )
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Install Jenkins Agent on Linux",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "agent_name",
        help="Name of the agent (must match name on Jenkins controller)"
    )
    parser.add_argument(
        "jenkins_url",
        help="URL of Jenkins controller (e.g., https://jenkins.example.com)"
    )
    parser.add_argument(
        "secret",
        help="Agent secret from Jenkins controller"
    )
    parser.add_argument(
        "--agent-dir",
        default="/opt/jenkins-agent",
        help="Directory to install agent files"
    )
    parser.add_argument(
        "--user",
        default="jenkins-agent",
        help="User to run agent as"
    )
    parser.add_argument(
        "--java-opts",
        default="",
        help="Additional Java options (e.g., -Xmx2g -Xms512m)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstall even if already installed"
    )

    args = parser.parse_args()

    success = install_jenkins_agent(
        agent_name=args.agent_name,
        jenkins_url=args.jenkins_url,
        secret=args.secret,
        agent_dir=args.agent_dir,
        user=args.user,
        java_opts=args.java_opts,
        force=args.force
    )

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
