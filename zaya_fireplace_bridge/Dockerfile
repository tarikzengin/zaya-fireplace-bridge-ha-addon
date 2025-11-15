ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.19
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    bluez \
    bluez-deprecated \
    bluez-libs \
    bluez-btmgmt \
    bash

# Virtualenv oluştur ve pip paketlerini içine kur
RUN python3 -m venv /venv \
    && . /venv/bin/activate \
    && pip install --no-cache-dir pybluez paho-mqtt

ENV PATH="/venv/bin:$PATH"

WORKDIR /usr/src/app
COPY run.sh /run.sh
COPY zaya_bridge.py /usr/src/app/zaya_bridge.py

RUN chmod a+x /run.sh

CMD ["/run.sh"]
