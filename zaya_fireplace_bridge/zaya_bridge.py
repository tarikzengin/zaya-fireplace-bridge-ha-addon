import os
import time
import threading
import binascii
import serial
import paho.mqtt.client as mqtt


# --------------------------------------------------------------------
#  ENVIRONMENT VARIABLES (run.sh içinden gelir)
# --------------------------------------------------------------------
FIREPLACE_MAC = os.getenv("FIREPLACE_MAC")
MQTT_HOST = os.getenv("MQTT_HOST", "core-mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_COMMAND_TOPIC = os.getenv("MQTT_COMMAND_TOPIC", "zaya/fireplace/command")
MQTT_STATE_TOPIC = os.getenv("MQTT_STATE_TOPIC", "zaya/fireplace/state")

# RFCOMM cihazı (run.sh içinde rfcomm bind ile oluşturacağız)
RFCOMM_DEVICE = os.getenv("RFCOMM_DEVICE", "/dev/rfcomm0")


# --------------------------------------------------------------------
#  ZAYA HEX COMMAND TABLE
#  (APK / logcat'ten çıkardığın hex komutları buraya doldurabilirsin)
# --------------------------------------------------------------------
COMMANDS = {
    "POWER_ON":  "5519...",
    "POWER_OFF": "5519...",
    # Örnek:
    # "FLAME_UP": "...",
    # "FLAME_DOWN": "...",
}


class ZayaFireplaceBridge:
    def __init__(self):
        self.ser = None

        # MQTT client
        self.mqtt = mqtt.Client()
        if MQTT_USERNAME:
            self.mqtt.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        self.mqtt.on_connect = self.mqtt_on_connect
        self.mqtt.on_message = self.mqtt_on_message
        self.mqtt.on_disconnect = self.mqtt_on_disconnect

    # ------------------------------------------------------------
    #  MQTT CALLBACKS
    # ------------------------------------------------------------
    def mqtt_on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"[MQTT] Connected with result {rc}")
        client.subscribe(MQTT_COMMAND_TOPIC)
        print(f"[MQTT] Subscribed to {MQTT_COMMAND_TOPIC}")

    def mqtt_on_message(self, client, userdata, msg):
        payload = msg.payload.decode().strip().upper()
        print(f"[MQTT] Command received: {payload}")
        self.handle_command(payload)

    def mqtt_on_disconnect(self, client, userdata, rc, properties=None):
        print(f"[MQTT] MQTT disconnected: {rc}")

    # ------------------------------------------------------------
    #  RFCOMM / SERIAL BAĞLANTI
    # ------------------------------------------------------------
    def open_serial(self):
        if self.ser and self.ser.is_open:
            return

        try:
            print(f"[SERIAL] Opening {RFCOMM_DEVICE} ...")
            # Baudrate burada aslında sanaldır, ama pyserial bir değer ister
            self.ser = serial.Serial(
                RFCOMM_DEVICE,
                baudrate=115200,
                timeout=2,
                write_timeout=2,
            )
            print("[SERIAL] Opened.")
        except Exception as e:
            print(f"[SERIAL] Failed to open {RFCOMM_DEVICE}: {e}")
            self.ser = None

    def close_serial(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        print("[SERIAL] Closed.")

    # ------------------------------------------------------------
    #  SEND HEX COMMAND
    # ------------------------------------------------------------
    def send_hex(self, hex_string: str):
        if not self.ser or not self.ser.is_open:
            self.open_serial()

        if not self.ser or not self.ser.is_open:
            print("[SERIAL] Not open — command cancelled")
            return

        try:
            cleaned = hex_string.replace(" ", "")
            data = binascii.unhexlify(cleaned)

            print(f"[SERIAL] Sending HEX: {cleaned}")
            self.ser.write(data)
            self.ser.flush()
        except Exception as e:
            print(f"[SERIAL] Send failed: {e}")
            self.close_serial()

    # ------------------------------------------------------------
    #  COMMAND HANDLER
    # ------------------------------------------------------------
    def handle_command(self, cmd: str):
        if cmd == "ON":
            hex_cmd = COMMANDS.get("POWER_ON")
        elif cmd == "OFF":
            hex_cmd = COMMANDS.get("POWER_OFF")
        elif cmd.startswith("RAW:"):
            hex_cmd = cmd[4:]
        else:
            hex_cmd = COMMANDS.get(cmd)

        if not hex_cmd:
            print(f"[CMD] Invalid or undefined command: {cmd}")
            return

        self.send_hex(hex_cmd)

        # Basit/iyimser state publish
        if cmd in ("ON", "POWER_ON"):
            self.publish_state("ON")
        if cmd in ("OFF", "POWER_OFF"):
            self.publish_state("OFF")

    # ------------------------------------------------------------
    #  STATE PUBLISH
    # ------------------------------------------------------------
    def publish_state(self, state: str):
        try:
            self.mqtt.publish(MQTT_STATE_TOPIC, state, retain=True)
            print(f"[MQTT] State published: {state}")
        except Exception as e:
            print(f"[MQTT] Failed to publish state: {e}")

    # ------------------------------------------------------------
    #  MAIN LOOP
    # ------------------------------------------------------------
    def run(self):
        print("[SYS] ZAYA Fireplace Bridge Starting")
        print(f"[SYS] MQTT host: {MQTT_HOST}:{MQTT_PORT}")
        print(f"[SYS] Fireplace MAC: {FIREPLACE_MAC}")
        print(f"[SYS] RFCOMM device: {RFCOMM_DEVICE}")

        # MQTT connect
        self.mqtt.connect(MQTT_HOST, MQTT_PORT, 60)

        t = threading.Thread(target=self.mqtt.loop_forever)
        t.daemon = True
        t.start()

        # Ana thread sadece hayatta kalsın
        while True:
            time.sleep(10)


# --------------------------------------------------------------------
#  ENTRYPOINT
# --------------------------------------------------------------------
if __name__ == "__main__":
    bridge = ZayaFireplaceBridge()
    bridge.run()
