FROM python:3.12

WORKDIR /app

# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "yt_transcription.wsgi:application", "--bind", "0.0.0.0:8000"]