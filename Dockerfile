FROM python:3.12-slim

WORKDIR /app

RUN pip install uv --quiet

COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev

ENV FLASK_APP=src/good_start_habits/app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 5000

# dashboard.db and .env are expected to be bind-mounted at runtime:
#   docker run -v $(pwd)/dashboard.db:/app/dashboard.db --env-file .env ...
CMD ["sh", "-c", "flask run --port ${PORT:-8080}"]