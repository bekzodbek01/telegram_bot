FROM python:3.10-slim

WORKDIR /app

# System dependencies (pyside6 uchun kerak bo’lishi mumkin)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

CMD ["python", "main.py"]
