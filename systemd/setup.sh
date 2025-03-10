#!/bin/bash

APP_DIR="/opt/misp-global-search"
# Get the absolute directory of the current script
CURRENT_DIR="$(dirname "$(readlink -f "$0")")"
# The repository directory is the parent of the script's directory
REPO_DIR="$(dirname "$CURRENT_DIR")"
SERVICE_FILE="mgsupdate.service"
SERVICE_PATH="/etc/systemd/system/"

log() {
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*"
}

if [[ $EUID -ne 0 ]]; then
    log "This script must be run as root or with sudo privileges"
    exit 1
fi

log "Computed repo directory: $REPO_DIR"

if [[ -d "$REPO_DIR" ]]; then
    cp -r "$REPO_DIR" "/opt/" || { log "Failed to copy repo directory"; exit 1; }
else
    log "Repo directory $REPO_DIR does not exist"
    exit 1
fi

# Create user if it doesn't exist
if ! id "mgsupdate" &>/dev/null; then
    useradd -r -s /bin/false mgsupdate || { log "Failed to create user mgsupdate"; exit 1; }
fi

# Set ownership and permissions
chown -R mgsupdate: "$APP_DIR" || { log "Failed to change ownership"; exit 1; }
chmod -R u+x "$APP_DIR/"*.py || { log "Failed to set execute permission on scripts"; exit 1; }
chmod -R u+x "$APP_DIR/"*.sh || { log "Failed to set execute permission on scripts"; exit 1; }

if [ -d "$APP_DIR/env" ]; then
    log "Existing virtual environment found. Removing outdated environment."
    rm -rf "$APP_DIR/env" || { log "Failed to remove existing virtual environment"; exit 1; }
fi

log "Creating Python virtual environment in $APP_DIR/env"
python3 -m venv "$APP_DIR/env" || { log "Failed to create virtual environment"; exit 1; }

if [ -f "$APP_DIR/requirements.txt" ]; then
    log "Installing Python dependencies from requirements.txt"
    "$APP_DIR/env/bin/pip" install -r "$APP_DIR/requirements.txt" || { log "Failed to install Python dependencies"; exit 1; }
else
    log "requirements.txt not found in $APP_DIR"
    exit 1
fi

# Copy service file
if [[ -f "$SERVICE_FILE" ]]; then
    cp "${SERVICE_FILE}" "${SERVICE_PATH}" || { log "Failed to copy service file"; exit 1; }
else
    log "Service file $SERVICE_FILE not found"
    exit 1
fi

# Reload systemd, enable and start the service
systemctl daemon-reload || { log "Failed to reload systemd daemon"; exit 1; }
systemctl enable "${SERVICE_FILE}" || { log "Failed to enable service"; exit 1; }
systemctl start "${SERVICE_FILE}" || { log "Failed to start service"; exit 1; }

log "Service setup completed successfully."

