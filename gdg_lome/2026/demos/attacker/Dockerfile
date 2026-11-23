FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends mosquitto-clients nmap \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir paho-mqtt==2.1.0 requests==2.32.3
COPY attack.py .
CMD ["python", "-u", "attack.py", "chain"]
