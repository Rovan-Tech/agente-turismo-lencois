FROM python:3.14-slim

WORKDIR /app

# O upgrade aplica as correções de segurança do Debian publicadas depois que a imagem base foi
# gerada (ex.: openssl); o Trivy do CI barra a imagem se ficar alguma HIGH/CRITICAL com correção.
# hadolint ignore=DL3005
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# A imagem base traz pip/setuptools/wheel com cópias embutidas de bibliotecas que já tiveram CVE
# (jaraco.context, wheel). Atualizar essas ferramentas antes de instalar o resto fecha esses alertas.
RUN pip install --no-cache-dir --upgrade "pip>=26" "setuptools>=80" "wheel>=0.46"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# O pip embute cópias de urllib3, msgpack e setuptools que não dá para atualizar à parte, e o
# runtime não instala nada: sem ele a imagem fica menor e sem esses alertas.
RUN pip uninstall -y pip wheel

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

RUN useradd --create-home --uid 10001 app
USER app

# Baixa o modelo do faster-whisper durante o build, não no primeiro request — Cloud
# Run hiberna sem tráfego, então um cold start não pode depender de rede externa
# pra baixar ~150MB do Hugging Face antes de conseguir transcrever um áudio.
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
