
FROM tellyhubcloud/telly-wzml:latest

WORKDIR /usr/src/app

COPY requirements.txt /tmp/sdk-requirements.txt

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_LINK_MODE=copy

RUN uv pip install \
    --python /usr/src/app/.venv/bin/python \
    --no-cache-dir \
    -r /tmp/sdk-requirements.txt \
    && /usr/src/app/.venv/bin/python -c \
    "import aiohttp, motor, pymongo; print('SDK Python dependencies OK')"

COPY . .

USER root

RUN chown -R app:app /usr/src/app \
    && chmod -R u+rwX /usr/src/app

USER app

CMD ["bash", "/usr/src/app/start.sh"]
