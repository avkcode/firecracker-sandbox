#!/bin/bash

# Variables
LINUXKIT_VERSION="v1.5.3"
PLATFORM="linux-amd64"  # Change to "darwin-amd64", "darwin-arm64", etc., as needed
BINARY_NAME="linuxkit-${PLATFORM}"
DOWNLOAD_URL="https://github.com/linuxkit/linuxkit/releases/download/${LINUXKIT_VERSION}/${BINARY_NAME}"

# Step 1: Download the binary
echo "Downloading LinuxKit ${LINUXKIT_VERSION} for ${PLATFORM}..."
wget $DOWNLOAD_URL

# Step 2: Install the binary
echo "Installing LinuxKit..."
chmod +x $BINARY_NAME
sudo mv $BINARY_NAME /usr/local/bin/linuxkit

# Step 3: Verify the installation
echo "Verifying installation..."
linuxkit version

echo "LinuxKit installation complete."
