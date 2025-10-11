FROM python:3.11-slim

# Systemabhängigkeiten für Druck und Fonts
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fonts-dejavu-core libjpeg-dev libusb-1.0-0 libudev1 libffi-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Python-Abhängigkeiten installieren
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI starten
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core libjpeg-dev libusb-1.0-0 libudev1 libffi-dev && \
    rm -rf /var/lib/apt/lists/*
