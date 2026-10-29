FROM tellyhubcloud/telly-wzml:latest

WORKDIR /usr/src/app

COPY requirements.txt .

# Keep the base-image uv executable path before the venv changes PATH resolution.
ENV VIRTUAL_ENV=/usr/src/app/.venv
ENV PATH="/usr/src/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN UV_BIN="$(command -v uv)" \
    && test -x "$UV_BIN" \
    && "$UV_BIN" venv --clear /usr/src/app/.venv \
    && "$UV_BIN" pip install --python /usr/src/app/.venv/bin/python -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
