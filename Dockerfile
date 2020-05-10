FROM python:3.7-alpine AS builder

ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1

# Turns off writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Run from virtualenv
ENV PATH="/venv/bin:$PATH"

ADD ./requirements.txt /requirements.txt

RUN apk upgrade --no-cache \
	&& apk add --no-cache --virtual .build-deps build-base \
	gcc gfortran libpng-dev openblas-dev jpeg-dev \
    && pip install --upgrade pip

RUN python -m venv /venv

RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.7-alpine

# Extra python env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/venv/bin:$PATH"

RUN apk upgrade --no-cache \
	&& apk add --no-cache libjpeg-turbo \
    && pip install --upgrade pip \
    && mkdir /data

COPY --from=builder /venv /venv

VOLUME ["/data"]

ENV CACHE_FILE=/data/cache.json \
    DATA_DIR=/data \
    LOG_LEVEL=info \
    ENABLE_ANALYTICS=true \
    ENABLE_DEBUG=false \
    ENABLE_UPLOAD=true \
    IG_USER= \
    IG_USERNAME= \
    IG_PASSWORD=

ADD ./app /app

CMD ["python",  "/app/instagram_routine_bot.py"]
