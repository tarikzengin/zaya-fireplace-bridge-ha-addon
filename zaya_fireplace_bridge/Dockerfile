ARG BUILD_FROM
FROM ${BUILD_FROM}

# Alpine tabanlı Home Assistant imajında paketler APK ile kuruluyor
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-virtualenv \
    bluez \
    bluez-deprecated \
    bluez-libs \
    bluez-btmgmt \
    jq \
    bash

# Virtualenv oluştur ve içine bağımlılıkları kur
RUN python3 -m venv /venv \
    && . /venv/bin/activate \
    # PyBluez klasik paket yeni setuptools ile patlıyor,
    # bu yüzden fork olan pybluez2'yi kullanıyoruz.
    && pip install --no-cache-dir pybluez2 paho-mqtt

ENV PATH="/venv/bin:$PATH"

WORKDIR /usr/src/app
COPY run.sh /run.sh
COPY zaya_bridge.py /usr/src/app/zaya_bridge.py

RUN chmod a+x /run.sh

CMD ["/run.sh"]
