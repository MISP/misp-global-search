#!/bin/bash
set -e

# =================== Helper Funcions ==================

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

random_string() {
    cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1
}


# =================== LXD Env Setup ==================

PROFILE="meilisearch"
MEILISEARCH_CONTAINER="meilisearch"
STORAGE="meilisearch"
MASTER_KEY="$(random_string)"

# Create Storage
if checkRessourceExist "storage" "$STORAGE"; then
    echo "Storage '$STORAGE' already exists."
else
    lxc storage create "$STORAGE" zfs
fi

if checkRessourceExist "profile" "$PROFILE"; then
    echo "Profile '$PROFILE' already exists."
else
    lxc profile create "$PROFILE"
    lxc profile device add "$PROFILE" root disk path=/ pool="$STORAGE"
    lxc profile device add "$PROFILE" eth0 nic nictype=bridged parent=lxdbr0 name=eth0
fi

if checkRessourceExist "container" "$MEILISEARCH_CONTAINER"; then
    echo "Container '$MEILISEARCH_CONTAINER' already exists."
else
    lxc launch ubuntu:24.04 $MEILISEARCH_CONTAINER --profile=$PROFILE
    sleep 1
fi

# =================== Install Meilisearch ==================

if [ "$(lxc exec "$MEILISEARCH_CONTAINER" systemctl is-active meilisearch)" = "inactive" ]; then
    echo "Setting up Meilisearch in container 'meilisearch'..."

    lxc exec $MEILISEARCH_CONTAINER -- apt update
    lxc exec $MEILISEARCH_CONTAINER -- curl -L https://install.meilisearch.com -o install.sh
    lxc exec $MEILISEARCH_CONTAINER -- bash install.sh
    lxc exec $MEILISEARCH_CONTAINER -- mv ./meilisearch /usr/local/bin/
    lxc exec $MEILISEARCH_CONTAINER -- useradd -d /var/lib/meilisearch -s /bin/false -m -r meilisearch
    lxc exec $MEILISEARCH_CONTAINER -- chown meilisearch:meilisearch /usr/local/bin/meilisearch
    lxc exec $MEILISEARCH_CONTAINER -- mkdir -p /var/lib/meilisearch/data /var/lib/meilisearch/dumps /var/lib/meilisearch/snapshots
    lxc exec $MEILISEARCH_CONTAINER -- chown -R meilisearch:meilisearch /var/lib/meilisearch
    lxc exec $MEILISEARCH_CONTAINER -- chmod 750 /var/lib/meilisearch
    lxc exec $MEILISEARCH_CONTAINER -- curl https://raw.githubusercontent.com/meilisearch/meilisearch/latest/config.toml -o /etc/meilisearch.toml

    lxc exec $MEILISEARCH_CONTAINER -- sed -i 's/http_addr = "localhost:7700"/http_addr = "0.0.0.0:7700"/' /etc/meilisearch.toml
    lxc exec $MEILISEARCH_CONTAINER -- sed -i 's/db_path = "\.\/data\.ms"/db_path = "\/var\/lib\/meilisearch\/data"/' /etc/meilisearch.toml
    lxc exec $MEILISEARCH_CONTAINER -- sed -i 's/dump_dir = "dumps\/"/dump_dir = "\/var\/lib\/meilisearch\/dumps"/' /etc/meilisearch.toml
    lxc exec $MEILISEARCH_CONTAINER -- sed -i 's/snapshot_dir = "snapshots\/"/snapshot_dir = "\/var\/lib\/meilisearch\/snapshots"/' /etc/meilisearch.toml
    lxc exec $MEILISEARCH_CONTAINER -- sed -i "s/# master_key = \"YOUR_MASTER_KEY_VALUE\"/master_key = \"${MASTER_KEY}\"/" /etc/meilisearch.toml

    cat <<EOF | lxc exec "$MEILISEARCH_CONTAINER" -- tee /etc/systemd/system/meilisearch.service
[Unit]
Description=Meilisearch
After=systemd-user-sessions.service

[Service]
Type=simple
WorkingDirectory=/var/lib/meilisearch
ExecStart=/usr/local/bin/meilisearch --config-file-path /etc/meilisearch.toml
User=meilisearch
Group=meilisearch
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

    lxc exec $MEILISEARCH_CONTAINER -- systemctl enable meilisearch
    lxc exec $MEILISEARCH_CONTAINER -- systemctl start meilisearch
    sleep 5

    lxc exec $MEILISEARCH_CONTAINER -- curl -X GET '127.0.0.1:7700/keys' -H "Authorization: Bearer ${MASTER_KEY}"
    
    API_KEY=$(lxc exec $MEILISEARCH_CONTAINER -- curl -s -X GET '127.0.0.1:7700/keys' \
      -H "Authorization: Bearer ${MASTER_KEY}" \
      | jq -r '.results[] | select(.name=="Default Search API Key") | .key')


    ADMIN_API_KEY=$(lxc exec $MEILISEARCH_CONTAINER -- curl -s -X GET '127.0.0.1:7700/keys' \
      -H "Authorization: Bearer ${MASTER_KEY}" \
      | jq -r '.results[] | select(.name=="Default Admin API Key") | .key')

    IP_ADDRESS=$(lxc list meilisearch --format json | jq -r '.[0].state.network.eth0.addresses[] | select(.family=="inet" and .scope=="global") | .address')


    cat <<EOF | tee ./src/config.json
{
    "MEILI_URL": "http://${IP_ADDRESS}:7700",
    "MEILI_API_KEY": "${API_KEY}",
    "MEILI_MASTER_API_KEY": "${MASTER_KEY}",
    "MEILI_ADMIN_API_KEY": "${ADMIN_API_KEY}"
}
EOF

fi

