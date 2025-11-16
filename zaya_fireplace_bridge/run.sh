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

echo "[Zaya Bridge] Fireplace MAC: ${FIREPLACE_MAC}"

# RFCOMM binding (BlueZ rfcomm aracı ile)
if [ -n "${FIREPLACE_MAC}" ] && [ "${FIREPLACE_MAC}" != "null" ]; then
  echo "[Zaya Bridge] Binding /dev/rfcomm0 to ${FIREPLACE_MAC}..."
  # Eski bağlantı varsa serbest bırak
  rfcomm release 0 || true
  # Kanalı 1 varsayıyoruz; cihaz farklı kanal kullanıyorsa burayı değiştireceğiz
  if rfcomm bind 0 "${FIREPLACE_MAC}" 1; then
    echo "[Zaya Bridge] rfcomm0 bound."
  else
    echo "[Zaya Bridge] WARNING: rfcomm bind failed, Python yine de başlayacak."
  fi
else
  echo "[Zaya Bridge] No FIREPLACE_MAC configured, skipping rfcomm bind."
fi

# Python bridge'i çalıştır
exec python3 /usr/src/app/zaya_bridge.py
