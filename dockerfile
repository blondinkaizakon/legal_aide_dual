FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# бот – фоном, веб – через wsgi
CMD ["bash","/app/start.sh"]
