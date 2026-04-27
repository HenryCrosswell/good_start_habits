FROM python:3.12-slim

WORKDIR /app

RUN pip install 'uv>=0.5.0' --quiet

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --frozen --no-dev

ENV FLASK_APP=src/good_start_habits/app.py
ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 5000

# Railway provides $PORT dynamically; default to 5000 for local development
CMD ["sh", "-c", "uv run flask run --host=0.0.0.0 --port=${PORT:-5000}"]
