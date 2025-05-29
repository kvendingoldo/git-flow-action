FROM python:3.13-alpine

ENV PATH=/usr/local/bin:$PATH \
    LANG=C.UTF-8

RUN apk update \
 && apk -X https://dl-cdn.alpinelinux.org/alpine/edge/main --no-cache add git>2.35.2-r0 \
 && mkdir /app \
 && rm -rf /var/lib/apt/lists/*

COPY --chmod=750 src/main.py /app/main.py
COPY --chmod=750 requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages -r /tmp/requirements.txt \
 && rm /tmp/requirements.txt

ENTRYPOINT ["/app/main.py"]