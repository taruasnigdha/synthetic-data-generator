FROM python:3.11-slim

WORKDIR /app

# Install dependencies using pyproject.toml
COPY pyproject.toml .
COPY mock_sap_server/ mock_sap_server/
COPY synthetic_data_agent/ synthetic_data_agent/
RUN pip install . gunicorn

ENV PORT=8080
# Use gunicorn to serve the mock server app
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 mock_sap_server.app:app
