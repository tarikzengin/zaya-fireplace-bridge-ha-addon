ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        bluetooth \
        bluez \
        bluez-tools \
        jq \
        bash && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /venv \
    && . /venv/bin/activate \
    && pip install --no-cache-dir pybluez paho-mqtt

ENV PATH="/venv/bin:$PATH"

WORKDIR /usr/src/app
COPY run.sh /run.sh
COPY zaya_bridge.py /usr/src/app/zaya_bridge.py

RUN chmod a+x /run.sh

CMD ["/run.sh"]
