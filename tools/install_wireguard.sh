#!/bin/bash

# Update and install required packages
sudo apt update
sudo apt install -y wireguard resolvconf qrencode

# Enable IP forwarding
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Generate private and public keys
umask 077
wg genkey | tee /etc/wireguard/privatekey | wg pubkey | tee /etc/wireguard/publickey

# Create WireGuard configuration file
PRIVATE_KEY=$(cat /etc/wireguard/privatekey)
PUBLIC_KEY=$(cat /etc/wireguard/publickey)
INTERFACE_NAME="wg0"
SERVER_IP="10.0.0.1/24"
SERVER_PORT="51820"

cat <<EOF | sudo tee /etc/wireguard/$INTERFACE_NAME.conf
[Interface]
Address = $SERVER_IP
SaveConfig = true
ListenPort = $SERVER_PORT
PrivateKey = $PRIVATE_KEY
PostUp = iptables -A FORWARD -i $INTERFACE_NAME -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i $INTERFACE_NAME -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Add peers here
# [Peer]
# PublicKey = <CLIENT_PUBLIC_KEY>
# AllowedIPs = 10.0.0.2/32
EOF

# Start and enable WireGuard
sudo systemctl enable wg-quick@$INTERFACE_NAME
sudo systemctl start wg-quick@$INTERFACE_NAME

# Display the public key for adding peers
echo "WireGuard installed and configured!"
echo "Your server public key is: $PUBLIC_KEY"
echo "Add this key to your client configuration."
