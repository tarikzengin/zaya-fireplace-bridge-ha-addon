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

RUN pip3 install --no-cache-dir \
    pybluez \
    paho-mqtt

WORKDIR /usr/src/app
COPY run.sh /run.sh
COPY zaya_bridge.py /usr/src/app/zaya_bridge.py

RUN chmod a+x /run.sh

CMD ["/run.sh"]
