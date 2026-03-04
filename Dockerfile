FROM python:3.12-slim

WORKDIR /usr/src/app

RUN echo "precedence ::ffff:0:0/96  100" >> /etc/gai.conf
RUN pip install --no-cache-dir uv
ENV PATH="/usr/src/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

COPY . .

CMD ["sh", "-c", "gunicorn src:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-2} --error-logfile -"]
