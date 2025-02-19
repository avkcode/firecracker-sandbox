#!/bin/bash

# Script to install the latest version of Firecracker
# Firecracker GitHub Repository: https://github.com/firecracker-microvm/firecracker

set -e  # Exit immediately if a command exits with a non-zero status

# Variables
GITHUB_REPO="firecracker-microvm/firecracker"
INSTALL_DIR="/usr/local/bin"
TEMP_DIR=$(mktemp -d)

# Function to get the latest Firecracker release version
get_latest_release() {
    curl --silent "https://api.github.com/repos/$GITHUB_REPO/releases/latest" | \
    grep '"tag_name":' | \
    sed -E 's/.*"([^"]+)".*/\1/'
}

# Step 1: Get the latest Firecracker release version
echo "Fetching the latest Firecracker release..."
LATEST_VERSION=$(get_latest_release)
if [[ -z "$LATEST_VERSION" ]]; then
    echo "Error: Failed to fetch the latest Firecracker release."
    exit 1
fi
echo "Latest Firecracker version: $LATEST_VERSION"

# Step 2: Download the Firecracker release assets
echo "Downloading Firecracker binaries for version $LATEST_VERSION..."
DOWNLOAD_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_VERSION/firecracker-$LATEST_VERSION-x86_64.tgz"
curl -L "$DOWNLOAD_URL" -o "$TEMP_DIR/firecracker.tgz"

# Step 3: Extract the binaries
echo "Extracting Firecracker binaries..."
tar -xzf "$TEMP_DIR/firecracker.tgz" -C "$TEMP_DIR"

# Step 4: Install the binaries
echo "Installing Firecracker binaries to $INSTALL_DIR..."
sudo mv "$TEMP_DIR/release-$LATEST_VERSION-x86_64/firecracker-$LATEST_VERSION-x86_64" "$INSTALL_DIR/firecracker"

# Step 5: Clean up temporary files
echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

# Step 6: Verify installation
echo "Verifying installation..."
if command -v firecracker >/dev/null 2>&1; then
    echo "Firecracker installed successfully!"
    echo "Version: $(firecracker --version)"
else
    echo "Error: Firecracker installation failed."
    exit 1
fi

echo "Firecracker is ready to use. Run 'firecracker --help' for usage instructions."
