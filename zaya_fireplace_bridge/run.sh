#!/usr/bin/env bash
set -e

echo "[Zaya Bridge] Starting service..."

# Add-on config dosyasından ayarları oku
if [ -f /data/options.json ]; then
  export FIREPLACE_MAC=$(jq -r '.fireplace_mac' /data/options.json)
  export MQTT_HOST=$(jq -r '.mqtt_host' /data/options.json)
  export MQTT_PORT=$(jq -r '.mqtt_port' /data/options.json)
  export MQTT_USERNAME=$(jq -r '.mqtt_username' /data/options.json)
  export MQTT_PASSWORD=$(jq -r '.mqtt_password' /data/options.json)
  export MQTT_COMMAND_TOPIC=$(jq -r '.mqtt_command_topic' /data/options.json)
  export MQTT_STATE_TOPIC=$(jq -r '.mqtt_state_topic' /data/options.json)
fi

python3 /usr/src/app/zaya_bridge.py
