FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ ./services

ENTRYPOINT [ "python", "-m", "services.coordinator.app" ]