FROM python:3.9-slim

WORKDIR /bot

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . . 
CMD ["python", "-m", "bot.main"]