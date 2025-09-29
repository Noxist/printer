FROM python:3.11-slim
# Fonts installieren (für korrekte Schriftgrössen)
RUN apt-get update && apt-get install -y fonts-dejavu-core
WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
