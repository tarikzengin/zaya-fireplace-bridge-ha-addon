import os
import time
import threading
import binascii
import serial
import paho.mqtt.client as mqtt

FIREPLACE_PORT = "/dev/rfcomm0"
BAUDRATE = 9600

MQTT_HOST = os.getenv("MQTT_HOST", "core-mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_COMMAND_TOPIC = os.getenv("MQTT_COMMAND_TOPIC", "zaya/fireplace/command")
MQTT_STATE_TOPIC = os.getenv("MQTT_STATE_TOPIC", "zaya/fireplace/state")

class ZayaFireplaceBridge:
    def __init__(self):
        self.serial = None

        self.mqtt = mqtt.Client()
        if MQTT_USERNAME:
            self.mqtt.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message

    def connect_serial(self):
        if self.serial and self.serial.is_open:
            return

        print("[SERIAL] Opening RFCOMM port...")
        self.serial = serial.Serial(FIREPLACE_PORT, BAUDRATE, timeout=1)
        print("[SERIAL] Connected")

    def send_hex(self, hex_string):
        try:
            self.connect_serial()
            data = binascii.unhexlify(hex_string.replace(" ", ""))
            print("[SERIAL] Sending:", data)
            self.serial.write(data)
        except Exception as e:
            print("[SERIAL] Error:", e)

    def on_connect(self, client, userdata, flags, rc):
        print(f"[MQTT] Connected {rc}")
        client.subscribe(MQTT_COMMAND_TOPIC)

    def on_message(self, client, userdata, msg):
        raw = msg.payload.decode().strip()
        print("[MQTT] Got command:", raw)
        if raw.startswith("RAW:"):
            self.send_hex(raw[4:])

    def run(self):
        print("[SYS] Starting...")
        self.mqtt.connect(MQTT_HOST, MQTT_PORT, 60)
        threading.Thread(target=self.mqtt.loop_forever, daemon=True).start()

        while True:
            time.sleep(1)

if __name__ == "__main__":
    ZayaFireplaceBridge().run()
