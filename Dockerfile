FROM tellyhubcloud/telly-wzml:latest

WORKDIR /usr/src/app

COPY requirements.txt .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Keep the base image's uv executable on PATH until dependency installation finishes.
RUN uv venv --clear /usr/src/app/.venv \
    && uv pip install --python /usr/src/app/.venv/bin/python -r requirements.txt

# Activate the project environment for subsequent commands and runtime.
ENV VIRTUAL_ENV=/usr/src/app/.venv
ENV PATH="/usr/src/app/.venv/bin:$PATH"

COPY . .

CMD ["bash", "start.sh"]
