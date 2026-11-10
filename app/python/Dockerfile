ARG MP_BASE_IMAGE=docker.io/library/python:3.12-slim-trixie
FROM ${MP_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/app/bin:${PATH}" \
    MP_REPO_PATH=/var/www/data \
    MP_CACHE_PATH=/tmp/mineprot

RUN apt-get update \
    && apt-get install -y --no-install-recommends libstdc++6 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/web
COPY web/requirements.txt /app/requirements.txt
RUN pip install --only-binary=:all: -r /app/requirements.txt

# app/bin is only the existing binary archive location; PHP is not installed.
COPY app/bin/usalign.tar.xz /tmp/tools/
COPY app/python/tools.sha256 /tmp/tools/tools.sha256
RUN mkdir -p /app/bin /var/www/data /var/cache/mineprot \
    && python -c "import hashlib, pathlib; root=pathlib.Path('/tmp/tools'); entries=[line.split() for line in (root/'tools.sha256').read_text().splitlines()]; mismatches=[name for digest,name in entries if hashlib.sha256((root/pathlib.Path(name).name).read_bytes()).hexdigest()!=digest]; mismatches and exit('Dependency checksum mismatch: '+str(mismatches))" \
    && python -c "import tarfile; tarfile.open('/tmp/tools/usalign.tar.xz').extractall('/app/bin', filter='data')" \
    && chmod 755 /app/bin/USalign \
    && rm -rf /tmp/tools \
    && chown -R 1000:1000 /var/www/data /var/cache/mineprot

COPY LICENSE /app/LICENSE
COPY web /app/web
USER 1000:1000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]
CMD ["uvicorn", "mineprot.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
