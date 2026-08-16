# Herkenbaar API - AGPL-3.0
FROM python:3.12-slim
WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# modelgewichten in de image bakken, zodat de container zonder internet kan starten
RUN python -c "from ultralytics import YOLO; YOLO('yolo26n-pose.pt')"

COPY app.py .
COPY assets/ assets/

EXPOSE 4050
CMD ["python", "app.py"]
