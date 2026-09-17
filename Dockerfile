FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY config ./config
COPY Makefile ./

ENV PYTHONPATH=/app/src
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "risk_lakehouse.pipeline", "--input", "data/raw", "--output", "data/processed", "--config", "config/project.json"]

