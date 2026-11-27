FROM python:3.12-slim
# iputils-ping fournit la commande ping utilisée (et détournée) par l'outil de diagnostic.
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY app/ /app/
RUN chmod +x /app/entrypoint.sh
EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
