#!/bin/python3

import os
import shutil
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def generate_gitconfig(name, email):
    # Define paths
    gitconfig_path = os.path.expanduser("~/.gitconfig")
    backup_path = os.path.expanduser("~/.gitconfig.backup")

    # Check if the file already exists
    if os.path.exists(gitconfig_path):
        # Create a timestamped backup file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_backup_path = os.path.expanduser(f"~/.gitconfig.backup_{timestamp}")
        
        # Backup the existing .gitconfig file
        try:
            shutil.copyfile(gitconfig_path, timestamped_backup_path)
            logging.warning(".gitconfig file already exists. Backing up to %s", timestamped_backup_path)
        except Exception as e:
            logging.error("Failed to create backup: %s", str(e))
            exit(1)

    # Generate the content for the new .gitconfig file
    gitconfig_content = f"""
[user]
    name = {name}
    email = {email}
[core]
    editor = vim
    pager = less -FRSX
[pull]
    rebase = true
[push]
    default = simple
[branch]
    sort = -committerdate
[tag]
    sort = version:refname
[init]
    defaultBranch = main
[diff]
    algorithm = histogram
    colorMoved = plain
    mnemonicPrefix = true
    renames = true
[help]
    autocorrect = 10
[commit]
    verbose = true
[rerere]
    enabled = true
    autoupdate = true
[rebase]
    autoSquash = true
    autoStash = true
    updateRefs = true
[color]
    ui = auto
[credential]
    helper = cache --timeout=3600
"""

    # Write the new content to the .gitconfig file
    try:
        with open(gitconfig_path, "w") as file:
            file.write(gitconfig_content.strip())
        logging.info(".gitconfig file has been successfully created/updated at %s", gitconfig_path)
    except Exception as e:
        logging.error("Failed to write .gitconfig file: %s", str(e))
        exit(1)


if __name__ == "__main__":
    # Prompt user for input
    print("Please enter your details for the .gitconfig file:")
    name = input("Your full name: ").strip()
    email = input("Your email: ").strip()

    # Validate input
    if not name or not email:
        logging.error("Error: Name and email cannot be empty!")
        exit(1)

    # Generate the .gitconfig file
    generate_gitconfig(name=name, email=email)
