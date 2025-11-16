ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:latest
FROM ${BUILD_FROM}

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        bluetooth bluez bluez-tools \
        gcc make libc6-dev jq bash && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /venv \
    && . /venv/bin/activate \
    && pip install --no-cache-dir pybluez paho-mqtt

ENV PATH="/venv/bin:$PATH"

WORKDIR /usr/src/app

COPY run.sh /run.sh
COPY zaya_bridge.py /usr/src/app/zaya_bridge.py

RUN chmod +x /run.sh

CMD ["/run.sh"]

 