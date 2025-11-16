import os
import time
import threading
import binascii
from bluetooth import *
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

# Bluetooth Classic SPP UUID
SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"


# --------------------------------------------------------------------
#  ZAYA HEX COMMAND TABLE — ŞİMDİLİK BOŞ
#  (Logcat'ten çıkardığın hex komutları buraya yazacağız)
# --------------------------------------------------------------------
COMMANDS = {
    "POWER_ON":  "5519...",
    "POWER_OFF": "5519...",
    # İleride:
    # "FLAME_UP": "...",
    # "FLAME_DOWN": "...",
    # Renk, efekt, ses vs hepsini buraya ekleyeceğiz.
}


# --------------------------------------------------------------------
#  MAIN BRIDGE CLASS
# --------------------------------------------------------------------
class ZayaFireplaceBridge:
    def __init__(self):
        self.sock = None
        self.connected = False

        # MQTT CLIENT
        self.mqtt = mqtt.Client()
        if MQTT_USERNAME:
            self.mqtt.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        self.mqtt.on_connect = self.mqtt_on_connect
        self.mqtt.on_message = self.mqtt_on_message
        self.mqtt.on_disconnect = self.mqtt_on_disconnect


    # ------------------------------------------------------------
    #  MQTT CALLBACKS
    # ------------------------------------------------------------
    def mqtt_on_connect(self, client, userdata, flags, rc):
        print(f"[MQTT] Connected with result {rc}")
        client.subscribe(MQTT_COMMAND_TOPIC)
        print(f"[MQTT] Subscribed to {MQTT_COMMAND_TOPIC}")


    def mqtt_on_message(self, client, userdata, msg):
        payload = msg.payload.decode().strip().upper()
        print(f"[MQTT] Command received: {payload}")
        self.handle_command(payload)


    def mqtt_on_disconnect(self, client, userdata, rc):
        print(f"[MQTT] MQTT disconnected: {rc}")


    # ------------------------------------------------------------
    #  BLUETOOTH CONNECTION
    # ------------------------------------------------------------
    def connect_bluetooth(self):
        if self.connected:
            return

        print(f"[BT] Discovering SPP service on {FIREPLACE_MAC}...")
        services = find_service(uuid=SPP_UUID, address=FIREPLACE_MAC)

        if not services:
            print("[BT] No SPP service found, retrying...")
            return

        service = services[0]
        host = service["host"]
        port = service["port"]

        print(f"[BT] Connecting to {host}:{port}...")
        sock = BluetoothSocket(RFCOMM)
        sock.connect((host, port))
        sock.settimeout(5.0)

        self.sock = sock
        self.connected = True
        print("[BT] Connected.")


    def disconnect_bluetooth(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass

        self.sock = None
        self.connected = False
        print("[BT] Disconnected.")


    # ------------------------------------------------------------
    #  SEND HEX COMMAND
    # ------------------------------------------------------------
    def send_hex(self, hex_string):
        if not self.connected:
            try:
                self.connect_bluetooth()
            except Exception as e:
                print(f"[BT] Connection error: {e}")
                self.connected = False
                return

        if not self.connected:
            print("[BT] Not connected — command cancelled")
            return

        try:
            cleaned = hex_string.replace(" ", "")
            data = binascii.unhexlify(cleaned)

            print(f"[BT] Sending HEX: {cleaned}")
            self.sock.send(data)

        except Exception as e:
            print(f"[BT] Send failed: {e}")
            self.disconnect_bluetooth()


    # ------------------------------------------------------------
    #  COMMAND HANDLER
    # ------------------------------------------------------------
    def handle_command(self, cmd):
        if cmd == "ON":
            hex_cmd = COMMANDS["POWER_ON"]
        elif cmd == "OFF":
            hex_cmd = COMMANDS["POWER_OFF"]
        elif cmd.startswith("RAW:"):
            hex_cmd = cmd[4:]
        else:
            hex_cmd = COMMANDS.get(cmd)

        if not hex_cmd:
            print(f"[CMD] Invalid or undefined command: {cmd}")
            return

        self.send_hex(hex_cmd)

        # Optimistic state push
        if cmd in ("ON", "POWER_ON"):
            self.publish_state("ON")
        if cmd in ("OFF", "POWER_OFF"):
            self.publish_state("OFF")


    # ------------------------------------------------------------
    #  STATE PUBLISH
    # ------------------------------------------------------------
    def publish_state(self, state):
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

        # MQTT bağlantısı
        self.mqtt.connect(MQTT_HOST, MQTT_PORT, 60)

        t = threading.Thread(target=self.mqtt.loop_forever)
        t.daemon = True
        t.start()

        while True:
            time.sleep(10)


# --------------------------------------------------------------------
#  ENTRYPOINT
# --------------------------------------------------------------------
if __name__ == "__main__":
    bridge = ZayaFireplaceBridge()
    bridge.run()
