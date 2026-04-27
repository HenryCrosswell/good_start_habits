FROM python:3.12-slim

WORKDIR /app

RUN pip install uv --quiet

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/

ENV FLASK_APP=src/good_start_habits/app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

EXPOSE 5000

# dashboard.db and .env are expected to be bind-mounted at runtime:
#   docker run -v $(pwd)/dashboard.db:/app/dashboard.db --env-file .env ...
CMD ["uv", "run", "flask", "run"]
