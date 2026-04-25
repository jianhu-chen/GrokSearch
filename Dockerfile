FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

ENV MCP_TRANSPORT=http

EXPOSE 8000

CMD ["grok-search"]
