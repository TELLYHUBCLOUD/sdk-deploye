FROM tellyhubcloud/telly-wzml:latest

WORKDIR /usr/src/app

COPY requirements.txt .

# Use a writable virtual environment path inside the application directory.
# The upstream base image may run as a non-root user, so /opt is not reliable.
ENV VIRTUAL_ENV=/usr/src/app/.venv
ENV PATH="/usr/src/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN uv venv --clear /usr/src/app/.venv \
    && uv pip install --python /usr/src/app/.venv/bin/python -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
