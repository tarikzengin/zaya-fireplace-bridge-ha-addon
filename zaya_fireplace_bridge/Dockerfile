ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip bluez bluez-deprecated bluez-libs bluez-btmgmt bash jq

RUN pip install pyserial paho-mqtt

WORKDIR /usr/src/app
COPY run.sh /run.sh
COPY zaya_bridge.py /usr/src/app/zaya_bridge.py

RUN chmod a+x /run.sh

CMD ["/run.sh"]

