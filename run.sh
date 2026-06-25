#!/bin/sh
# WebRemote - Quick Start
# Build and run with Docker

set -e

echo "=== WebRemote - Remote Server Management Console ==="
echo ""
echo "Building Docker images..."
docker compose build

echo ""
echo "Starting services..."
docker compose up -d

echo ""
echo "WebRemote is now running!"
echo "  Access: http://localhost:8090"
echo "  Stop:   docker compose down"
echo ""
