#!/bin/bash

# Script to help transition from Makefile to Python CLI for Firecracker

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Transitioning from Makefile to Python CLI for Firecracker${NC}"

# Create and switch to the feature/python branch
echo -e "${YELLOW}Creating and switching to feature/python branch...${NC}"
git checkout -b feature/python || { echo -e "${RED}Failed to create branch${NC}"; exit 1; }

# Make the Python script executable
echo -e "${YELLOW}Making firecracker_cli.py executable...${NC}"
chmod +x firecracker_cli.py || { echo -e "${RED}Failed to make script executable${NC}"; exit 1; }

# Create a symbolic link to make it easier to run
echo -e "${YELLOW}Creating symbolic link 'fc' for easier access...${NC}"
sudo ln -sf "$(pwd)/firecracker_cli.py" /usr/local/bin/fc || { echo -e "${RED}Failed to create symbolic link${NC}"; exit 1; }

echo -e "${GREEN}Transition complete!${NC}"
echo -e "${YELLOW}You can now use the Python CLI with:${NC}"
echo -e "  sudo fc --help"
echo -e "  sudo fc --net-up --activate --start"
echo -e "  sudo fc --stop --net-down --deactivate"
echo ""
echo -e "${YELLOW}Or continue using the original script:${NC}"
echo -e "  sudo python3 firecracker_cli.py [options]"
