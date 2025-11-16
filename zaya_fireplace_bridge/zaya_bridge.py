import os
import time
import threading
import binascii
import json

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
MQTT_STATUS_TOPIC = os.getenv("MQTT_STATUS_TOPIC", MQTT_STATE_TOPIC + "/status")

RFCOMM_DEVICE = os.getenv("RFCOMM_DEVICE", "/dev/rfcomm0")

# --------------------------------------------------------------------
#  PROTOKOL SABİTLERİ
# --------------------------------------------------------------------
CRC1 = 3
CRC2 = 100

# Android APK'deki varsayılan değerler
DEFAULT_STATE = {
    "heater": 0,
    "wood": 0,
    "backlight": 0,
    "effects": 0,
    "cRed": 255,
    "cGreen": 50,
    "cBlue": 0,
    "pmusic": 0,
    "sleeph": 0,
    "sleepm": 0,
    "atemp": 20,
    "heaterauto": 0,
    "screenbrightness": 10,
    "screensleeptime": 5,
    "heaterset": 0,
    "pvolume": 0,
    "lock": 0,
    "power": 0,
    "blestatus": 1,
    "oduneffect": 0,
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

        # Cihaz state'i
        self.state = DEFAULT_STATE.copy()
        self.state_lock = threading.Lock()

    # ------------------------------------------------------------
    #  MQTT CALLBACK'LERİ
    # ------------------------------------------------------------
    def mqtt_on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"[MQTT] Connected with result {rc}")
        client.subscribe(MQTT_COMMAND_TOPIC)
        print(f"[MQTT] Subscribed to {MQTT_COMMAND_TOPIC}")
        # MQTT bağlanınca statüyü yayınla
        self.publish_status("connected_mqtt")

    def mqtt_on_message(self, client, userdata, msg):
        payload = msg.payload.decode().strip()
        print(f"[MQTT] Command received: {payload}")
        self.handle_command(payload)

    def mqtt_on_disconnect(self, client, userdata, rc, properties=None):
        print(f"[MQTT] MQTT disconnected: {rc}")
        self.publish_status("mqtt_disconnected", "MQTT disconnected")

    # ------------------------------------------------------------
    #  STATUS PUBLISH
    # ------------------------------------------------------------
    def publish_status(self, status, error=None):
        """Bağlantı/statü bilgisini ayrı bir topic'e gönder."""
        payload = {"status": status}
        if error:
            payload["error"] = str(error)
        try:
            self.mqtt.publish(MQTT_STATUS_TOPIC, json.dumps(payload), retain=True)
            print(f"[MQTT] Status published: {payload}")
        except Exception as e:
            print(f"[MQTT] Failed to publish status: {e}")

    # ------------------------------------------------------------
    #  RFCOMM / SERIAL BAĞLANTI
    # ------------------------------------------------------------
    def open_serial(self):
        if self.ser and self.ser.is_open:
            return

        try:
            print(f"[SERIAL] Opening {RFCOMM_DEVICE} ...")
            self.ser = serial.Serial(
                RFCOMM_DEVICE,
                baudrate=115200,  # Sembolik, cihaz için önemli değil
                timeout=2,
                write_timeout=2,
            )
            print("[SERIAL] Opened.")
            self.publish_status("connected_serial")
        except Exception as e:
            print(f"[SERIAL] Failed to open {RFCOMM_DEVICE}: {e}")
            self.ser = None
            self.publish_status("serial_error", e)

    def close_serial(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        print("[SERIAL] Closed.")
        self.publish_status("serial_closed")

    # ------------------------------------------------------------
    #  RAW HEX GÖNDERME (RAW:xxxx için)
    # ------------------------------------------------------------
    def send_hex(self, hex_string: str):
        if not self.ser or not self.ser.is_open:
            self.open_serial()

        if not self.ser or not self.ser.is_open:
            print("[SERIAL] Not open — command cancelled")
            self.publish_status("serial_error", "Not open for RAW send")
            return

        try:
            cleaned = hex_string.replace(" ", "")
            data = binascii.unhexlify(cleaned)

            print(f"[SERIAL] Sending HEX: {cleaned}")
            self.ser.write(data)
            self.ser.flush()
        except Exception as e:
            print(f"[SERIAL] Send failed: {e}")
            self.publish_status("serial_error", e)
            self.close_serial()

    # ------------------------------------------------------------
    #  FRAME OLUŞTURMA (state -> 25 byte)
    # ------------------------------------------------------------
    def build_frame(self, state: dict) -> bytes:
        frame = bytearray(25)
        frame[0] = 0x55
        frame[1] = 0x19

        power = int(state.get("power", 0)) & 0xFF

        if power == 0:
            # Android APK'deki power=0 özel case
            frame[2] = 0   # heater
            frame[3] = 0
            frame[4] = 0   # wood
            frame[5] = 0   # backlight
            frame[6] = 0   # effects
            frame[7] = 0   # cRed
            frame[8] = 0   # cGreen
            frame[9] = 0   # cBlue
            frame[10] = 0  # pmusic
            frame[11] = int(state["sleeph"]) & 0xFF
            frame[12] = int(state["sleepm"]) & 0xFF
            frame[13] = int(state["atemp"]) & 0xFF
            frame[14] = 0   # heaterauto
            frame[15] = int(state["screenbrightness"]) & 0xFF
            frame[16] = int(state["screensleeptime"]) & 0xFF
            frame[17] = 0   # heaterset
            frame[18] = 0   # pvolume
            frame[19] = 0   # lock
            frame[20] = 0   # power
            frame[21] = 1   # blestatus
            frame[22] = 0   # oduneffect
        else:
            frame[2] = int(state["heater"]) & 0xFF
            frame[3] = 0
            frame[4] = int(state["wood"]) & 0xFF
            frame[5] = int(state["backlight"]) & 0xFF
            frame[6] = int(state["effects"]) & 0xFF
            frame[7] = int(state["cRed"]) & 0xFF
            frame[8] = int(state["cGreen"]) & 0xFF
            frame[9] = int(state["cBlue"]) & 0xFF
            frame[10] = int(state["pmusic"]) & 0xFF
            frame[11] = int(state["sleeph"]) & 0xFF
            frame[12] = int(state["sleepm"]) & 0xFF
            frame[13] = int(state["atemp"]) & 0xFF
            frame[14] = int(state["heaterauto"]) & 0xFF
            frame[15] = int(state["screenbrightness"]) & 0xFF
            frame[16] = int(state["screensleeptime"]) & 0xFF
            frame[17] = int(state["heaterset"]) & 0xFF
            frame[18] = int(state["pvolume"]) & 0xFF
            frame[19] = int(state["lock"]) & 0xFF
            frame[20] = power
            frame[21] = int(state["blestatus"]) & 0xFF
            frame[22] = int(state["oduneffect"]) & 0xFF

        frame[23] = CRC1
        frame[24] = CRC2
        return bytes(frame)

    def send_frame(self, frame: bytes):
        if not self.ser or not self.ser.is_open:
            self.open_serial()

        if not self.ser or not self.ser.is_open:
            print("[SERIAL] Not open — frame cancelled")
            self.publish_status("serial_error", "Not open for frame send")
            return

        try:
            print(f"[SERIAL] Sending FRAME: {binascii.hexlify(frame).decode().upper()}")
            self.ser.write(frame)
            self.ser.flush()
        except Exception as e:
            print(f"[SERIAL] Send failed: {e}")
            self.publish_status("serial_error", e)
            self.close_serial()

    # ------------------------------------------------------------
    #  FRAME DECODE (25 byte -> state dict)
    # ------------------------------------------------------------
    def decode_frame(self, frame: bytes):
        if len(frame) != 25:
            print(f"[SERIAL] Ignoring frame length {len(frame)}")
            return None

        if frame[0] != 0x55 or frame[1] != 0x19:
            print(f"[SERIAL] Invalid header: {binascii.hexlify(frame).decode().upper()}")
            return None

        s = {}
        s["heater"] = frame[2]
        s["wood"] = frame[4]
        s["backlight"] = frame[5]
        s["effects"] = frame[6]

        r = frame[7]
        g = frame[8]
        b = frame[9]
        s["cRed"] = 255 if r == 0xFF else r
        s["cGreen"] = 50 if g == 0xFF else g
        s["cBlue"] = 0 if b == 0xFF else b

        s["pmusic"] = frame[10]
        s["sleeph"] = frame[11]
        s["sleepm"] = frame[12]
        s["atemp"] = frame[13]
        s["heaterauto"] = frame[14]
        s["screenbrightness"] = frame[15]
        s["screensleeptime"] = frame[16]
        s["heaterset"] = frame[17]
        s["pvolume"] = frame[18]
        s["lock"] = frame[19]
        s["power"] = frame[20]
        s["blestatus"] = frame[21]
        s["oduneffect"] = frame[22]
        # [23], [24] = CRC'ler (şimdilik kontrol etmiyoruz)

        return s

    # ------------------------------------------------------------
    #  SERİ OKUMA LOOP'U
    # ------------------------------------------------------------
    def serial_reader_loop(self):
        while True:
            try:
                if not self.ser or not self.ser.is_open:
                    self.open_serial()
                    time.sleep(2)
                    continue

                frame = self.ser.read(25)
                if not frame:
                    continue

                if len(frame) != 25:
                    print(
                        f"[SERIAL] Partial frame ({len(frame)}): "
                        f"{binascii.hexlify(frame).decode().upper()}"
                    )
                    continue

                decoded = self.decode_frame(frame)
                if decoded:
                    with self.state_lock:
                        self.state.update(decoded)
                    self.publish_full_state()
                    # Cihazdan valid frame aldık, bağlantı iyi
                    self.publish_status("device_ok")
            except Exception as e:
                print(f"[SERIAL] Read error: {e}")
                self.publish_status("serial_error", e)
                self.close_serial()
                time.sleep(2)

    # ------------------------------------------------------------
    #  STATE PUBLISH (JSON)
    # ------------------------------------------------------------
    def publish_full_state(self):
        try:
            with self.state_lock:
                payload = json.dumps(self.state)
            self.mqtt.publish(MQTT_STATE_TOPIC, payload, retain=True)
            print(f"[MQTT] Full state published: {payload}")
        except Exception as e:
            print(f"[MQTT] Failed to publish full state: {e}")

    # ------------------------------------------------------------
    #  STATE UPDATE & KOMUT İŞLEME
    # ------------------------------------------------------------
    def apply_state_update(self, update: dict):
        with self.state_lock:
            new_state = dict(self.state)
            for key, value in update.items():
                if key not in new_state:
                    print(f"[STATE] Unknown key in update: {key}")
                    continue
                try:
                    v = int(value)
                except (ValueError, TypeError):
                    print(f"[STATE] Non-integer value for {key}: {value}")
                    continue

                if v < 0:
                    v = 0
                if v > 255:
                    v = 255

                new_state[key] = v

            frame = self.build_frame(new_state)
            self.state = new_state

        self.send_frame(frame)
        self.publish_full_state()

    def handle_command(self, cmd: str):
        if not cmd:
            return

        cmd_stripped = cmd.strip()

        # JSON (kısmi veya tam state)
        if cmd_stripped.startswith("{"):
            try:
                data = json.loads(cmd_stripped)
            except Exception as e:
                print(f"[CMD] Invalid JSON payload: {e} -> {cmd_stripped}")
                self.publish_status("command_error", e)
                return

            if isinstance(data, dict):
                self.apply_state_update(data)
            else:
                print("[CMD] JSON payload must be an object")
                self.publish_status("command_error", "JSON not an object")
            return

        upper = cmd_stripped.upper()

        # Basit alias komutlar
        if upper in ("ON", "POWER_ON"):
            self.apply_state_update({"power": 1})
            return

        if upper in ("OFF", "POWER_OFF"):
            self.apply_state_update({"power": 0})
            return

        # RAW:xxxxxx -> direkt hex gönder
        if upper.startswith("RAW:"):
            hex_cmd = cmd_stripped[4:]
            self.send_hex(hex_cmd)
            return

        print(f"[CMD] Invalid or undefined command: {cmd_stripped}")
        self.publish_status("command_error", "Unknown command")

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

        t_mqtt = threading.Thread(target=self.mqtt.loop_forever)
        t_mqtt.daemon = True
        t_mqtt.start()

        t_serial = threading.Thread(target=self.serial_reader_loop)
        t_serial.daemon = True
        t_serial.start()

        # İlk default state'i ve başlangıç statüsünü publish et
        self.publish_full_state()
        self.publish_status("starting")

        # Ana thread sadece hayatta kalsın
        while True:
            time.sleep(10)


if __name__ == "__main__":
    bridge = ZayaFireplaceBridge()
    bridge.run()
