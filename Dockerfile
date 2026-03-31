FROM python:3.12-slim

WORKDIR /app

# System deps (needed for asyncpg compilation if switching to Postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir setuptools wheel && \
    pip install --no-cache-dir --no-build-isolation salsa20 && \
    pip install --no-cache-dir -r requirements.txt && \
    python -c "\
import pathlib; \
f = pathlib.Path('/usr/local/lib/python3.12/site-packages/salsa20.py'); \
c = f.read_text(); \
c = c.replace('import imp', 'import importlib.util'); \
c = c.replace(\"imp.find_module('_salsa20')[1]\", \"importlib.util.find_spec('_salsa20').origin\"); \
f.write_text(c)"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
