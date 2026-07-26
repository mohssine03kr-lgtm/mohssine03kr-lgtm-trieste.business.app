FROM python:3.11-slim

WORKDIR /app

# Installa dipendenze di sistema
RUN apt-get update && apt-get install -y --no-install-recommends     gcc     libsqlite3-dev     && rm -rf /var/lib/apt/lists/*

# Copia requirements e installa
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il progetto
COPY . .

# Crea directory per il database
RUN mkdir -p /app/data

# Inizializza database
RUN python database.py

# Espone porta
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Avvia il bot
CMD ["python", "bot.py"]
