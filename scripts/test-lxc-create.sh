#!/bin/bash
# BIND LXC Installer - Debug/Test Version
# This version shows all output for debugging

set -e

echo "=== BIND LXC Installer Debug Mode ==="
echo ""

# Check if running on Proxmox
if ! command -v pct &> /dev/null; then
    echo "ERROR: pct command not found. Are you running this on a Proxmox host?"
    exit 1
fi

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root"
    exit 1
fi

echo "✓ Running on Proxmox as root"
echo ""

# Get container ID
echo "Enter Container ID [100]: "
read -r CTID
CTID=${CTID:-100}

# Check if ID is already in use
if pct status "$CTID" &>/dev/null; then
    echo "ERROR: Container $CTID already exists!"
    echo "Current containers:"
    pct list
    exit 1
fi

echo "✓ Container ID $CTID is available"
echo ""

# Check for template
echo "Checking for Ubuntu template..."
TEMPLATE=$(pveam list local 2>/dev/null | grep -E "ubuntu-22.04.*standard" | awk '{print $1}' | head -1)

if [ -z "$TEMPLATE" ]; then
    echo "Ubuntu template not found. Downloading..."
    pveam update
    pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
    TEMPLATE=$(pveam list local 2>/dev/null | grep -E "ubuntu-22.04.*standard" | awk '{print $1}' | head -1)
fi

echo "✓ Using template: $TEMPLATE"
echo ""

# Create container with verbose output
echo "Creating LXC container..."
echo "Command: pct create $CTID local:vztmpl/$TEMPLATE --hostname bind --memory 512 --cores 1 --rootfs local-lvm:4 --net0 name=eth0,bridge=vmbr0,ip=dhcp --onboot 1 --unprivileged 1"
echo ""

pct create "$CTID" "local:vztmpl/$TEMPLATE" \
    --hostname bind \
    --memory 512 \
    --cores 1 \
    --rootfs local-lvm:4 \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp \
    --onboot 1 \
    --unprivileged 1 \
    --features nesting=1

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Container created successfully!"
    echo ""
    
    # Verify it exists
    echo "Container list:"
    pct list | grep "$CTID"
    echo ""
    
    # Start it
    echo "Starting container..."
    pct start "$CTID"
    sleep 3
    
    # Check status
    echo "Container status:"
    pct status "$CTID"
    
    echo ""
    echo "SUCCESS: Container $CTID is created and running!"
    echo "To enter: pct enter $CTID"
else
    echo ""
    echo "FAILED: Container creation failed"
    exit 1
fi
