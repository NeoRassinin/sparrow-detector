FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
# ultralytics тянет opencv-python (нужен GUI), заменяем на headless-версию для сервера
RUN pip uninstall -y opencv-python opencv-python-headless || true
RUN pip install --no-cache-dir opencv-python-headless

COPY app ./app
COPY weights ./weights
RUN mkdir -p uploads results db

ENV PYTHONUNBUFFERED=1
ENV MODEL_PATH=/app/weights/best.pt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
