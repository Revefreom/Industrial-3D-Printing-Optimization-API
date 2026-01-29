FROM python:3.11-slim

WORKDIR /app

# Non-root user oluştur
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Dosya sahipliğini ayarla
RUN chown -R appuser:appgroup /app

# Non-root user'a geç
USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]