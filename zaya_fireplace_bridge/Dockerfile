ARG BUILD_FROM
FROM ${BUILD_FROM}

# Sistem bağımlılıkları: Python + BlueZ + jq + bash + venv
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-virtualenv \
    bluez \
    bluez-deprecated \
    bluez-libs \
    bluez-btmgmt \
    bash \
    jq

# Virtualenv oluştur ve içine Python bağımlılıklarını kur
RUN python3 -m venv /venv \
    && . /venv/bin/activate \
    && pip install --no-cache-dir pyserial paho-mqtt

ENV PATH="/venv/bin:$PATH"

WORKDIR /usr/src/app
COPY run.sh /run.sh
COPY zaya_bridge.py /usr/src/app/zaya_bridge.py

RUN chmod a+x /run.sh

CMD ["/run.sh"]
