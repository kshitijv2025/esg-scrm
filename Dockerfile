FROM python:3.11-slim

# libpq-dev needed for psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
RUN uv pip install --system fastapi uvicorn pydantic fpdf2 python-dotenv psycopg2-binary

COPY src/ src/
COPY data/ data/

ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
