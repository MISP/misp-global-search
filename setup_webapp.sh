#!/bin/bash
set -e

checkRessourceExist() {
    local resource_type="$1"
    local resource_name="$2"

    case "$resource_type" in
        "container")
            lxc info "$resource_name" &>/dev/null
            ;;
        "image")
            lxc image list --format=json | jq -e --arg alias "$resource_name" '.[] | select(.aliases[].name == $alias) | .fingerprint' &>/dev/null
            ;;
        "project")
            lxc project list --format=json | jq -e --arg name "$resource_name" '.[] | select(.name == $name) | .name' &>/dev/null
            ;;
        "storage")
            lxc storage list --format=json | jq -e --arg name "$resource_name" '.[] | select(.name == $name) | .name' &>/dev/null
            ;;
        "network")
            lxc network list --format=json | jq -e --arg name "$resource_name" '.[] | select(.name == $name) | .name' &>/dev/null
            ;;
        "profile")
            lxc profile list --format=json | jq -e --arg name "$resource_name" '.[] | select(.name == $name) | .name' &>/dev/null
            ;;
    esac

    return $?
}

CONTAINER="mispGlobalSearch"
APP_DIR=/opt/misp-global-search

if checkRessourceExist "container" "$CONTAINER"; then
    echo "Container '$CONTAINER' already exists."
else
    lxc launch ubuntu:24.04 $CONTAINER
fi

lxc exec $CONTAINER -- apt update
lxc exec $CONTAINER -- apt install python3.12-venv -y
lxc exec $CONTAINER -- git clone https://github.com/MISP/misp-global-search.git ${APP_DIR}
lxc exec $CONTAINER -- bash -c "python3 -m venv ${APP_DIR}/venv && ${APP_DIR}/venv/bin/pip install --upgrade pip && ${APP_DIR}/venv/bin/pip install -r ${APP_DIR}/requirements.txt" 
cat <<EOF | lxc exec $CONTAINER -- tee /etc/systemd/system/mispglobalsearch.service
[Unit]
Description=MISP Gobal Search
After=network.target

[Service]
User=root
WorkingDirectory=${APP_DIR}/src
ExecStart=${APP_DIR}/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

lxc file push ./src/config.json $CONTAINER/${APP_DIR}/src/config.json

lxc exec $CONTAINER -- systemctl daemon-reload
lxc exec $CONTAINER -- systemctl enable mispglobalsearch
lxc exec $CONTAINER -- systemctl start mispglobalsearch

lxc config device add ${CONTAINER} myproxy proxy listen=tcp:0.0.0.0:8000 connect=tcp:127.0.0.1:8000
