FROM python:3.8-slim-bullseye

RUN apt-get update && apt-get install -y libpq-dev

RUN mkdir -p /code
WORKDIR /code

COPY requirements.txt /tmp/requirements.txt
RUN set -ex && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/

COPY yt_transcription /code/yt_transcription

WORKDIR /code/yt_transcription

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "--bind", ":8000", "--workers", "2", "yt_transcription.wsgi"]