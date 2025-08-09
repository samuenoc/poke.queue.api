FROM python:3.13-slim

WORKDIR /app

# Instala dependencias necesarias y agrega el repo de Microsoft para Debian 12 (bookworm)
RUN apt-get update && \
    apt-get install -y curl gnupg2 software-properties-common apt-transport-https && \
    curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg && \
    install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/ && \
    echo "deb [arch=amd64] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev gcc g++ && \
    apt-get clean && rm -rf /var/lib/apt/lists/* microsoft.gpg

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la app
COPY . .

# Elimina archivos sensibles (opcional, puedes manejar esto mejor con .dockerignore)
RUN rm -f .env

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
