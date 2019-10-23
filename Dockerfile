FROM python:3.7-alpine3.10

WORKDIR /app

COPY *.py *.txt /app/

RUN apk upgrade --no-cache \
	&& apk add --no-cache --virtual .build-deps build-base \
	gcc gfortran libpng-dev openblas-dev jpeg-dev \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps \
    && apk add --no-cache libjpeg-turbo \
    && mkdir /data

VOLUME ["/data"]

ENV IG_USERNAME='' IG_PASSWORD=''

ENTRYPOINT ["python",  "/app/instagram_routine_bot.py", "-d", "-c", "/data/cache.json"]

# docker run --name=instagram-bot -d -v ~/Documents/IG_DATA:/data -e IG_USERNAME='' -e IG_PASSWORD='' <img_id>


# apk add build-base python-dev py-pip  zlib-dev
# apk --no-cache --update-cache add 
# pip install 