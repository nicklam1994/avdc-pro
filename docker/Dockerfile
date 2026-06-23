FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY pyproject.toml .
RUN pip install -e .

VOLUME ["/data"]
WORKDIR /data

ENTRYPOINT ["avdc"]
CMD ["."]
