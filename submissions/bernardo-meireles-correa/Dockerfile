# App Streamlit do Copiloto de Suporte. A apresentação estática é servida pelo Caddy.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp \
    STATE_DIR=/srv/app/local-state

WORKDIR /srv/app
COPY requirements.txt .
RUN pip install --no-compile -r requirements.txt

# Só o necessário para rodar: código, modelo e resultados. Dados brutos e testes ficam fora.
COPY .streamlit/ .streamlit/
COPY app/ app/
COPY models/ models/
COPY outputs/ outputs/

RUN useradd --system --uid 10001 --home-dir /srv/app appuser \
    && mkdir -p /srv/app/local-state && chown appuser /srv/app/local-state
USER appuser

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/app/_stcore/health', timeout=4)"

CMD ["streamlit", "run", "app/app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.baseUrlPath=app", \
     "--server.headless=true", "--browser.gatherUsageStats=false", "--server.fileWatcherType=none"]
