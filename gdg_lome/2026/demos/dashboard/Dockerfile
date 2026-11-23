FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3 paho-mqtt==2.1.0
COPY app.py .
COPY templates/ templates/
CMD ["python", "-u", "app.py"]
