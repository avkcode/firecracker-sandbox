#!/usr/bin/env python3

import subprocess
import sys

def run_command(command):
    """Helper function to run shell commands."""
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.strip()}")
        sys.exit(1)

def setup_git_config():
    """Set up Git configuration options and variables."""
    print("Starting Git configuration setup...")

    # Prompt user for required information
    username = input("Enter your Git username: ").strip()
    email = input("Enter your Git email: ").strip()

    # Optional configurations
    editor = input("Enter your preferred text editor (leave blank for default 'nano'): ").strip() or "nano"
    default_branch = input("Enter your default branch name (leave blank for 'main'): ").strip() or "main"

    # Set global Git configurations
    print("\nSetting up Git configurations...")
    run_command(f"git config --global user.name \"{username}\"")
    run_command(f"git config --global user.email \"{email}\"")
    run_command(f"git config --global core.editor \"{editor}\"")
    run_command(f"git config --global init.defaultBranch \"{default_branch}\"")

    # Enable color output in Git
    run_command("git config --global color.ui auto")

    # Set pull behavior to rebase by default
    run_command("git config --global pull.rebase true")

    # Enable automatic correction for mistyped Git commands
    run_command("git config --global help.autocorrect 10")

    # Configure pager to handle long outputs better
    run_command("git config --global core.pager 'less -FRSX'")

    # Optionally, set credential helper for caching passwords
    cache_duration = input("How long should Git cache your credentials (in seconds, leave blank for 3600): ").strip() or "3600"
    run_command(f"git config --global credential.helper 'cache --timeout={cache_duration}'")

    # Display current Git configuration
    print("\nCurrent Git configuration:")
    run_command("git config --list")

    print("\nGit configuration setup complete!")

if __name__ == "__main__":
    # Check if Git is installed
    try:
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("Error: Git is not installed. Please install Git before running this script.")
        sys.exit(1)

    # Run the setup
    setup_git_config()
