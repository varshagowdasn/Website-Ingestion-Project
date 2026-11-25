FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libcairo2 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install --with-deps chromium
COPY . .
RUN mkdir -p data/site
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
