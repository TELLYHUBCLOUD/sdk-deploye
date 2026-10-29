FROM tellyhubcloud/telly-wzml:latest

WORKDIR /usr/src/app

# DOCKERSDK already provides Python 3.14.9 and a prepared /usr/src/app/.venv.
# Install the deploy wrapper's dependency pins into that existing environment.
COPY requirements.txt /tmp/sdk-requirements.txt

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_LINK_MODE=copy

# Keep the requirements file in the image layer: the base image's non-root
# build user may not own /tmp/sdk-requirements.txt and cannot safely remove it.
RUN uv pip install --python /usr/src/app/.venv/bin/python --no-cache-dir -r /tmp/sdk-requirements.txt \
    && /usr/src/app/.venv/bin/python -c "import aiohttp, motor, pymongo; print('SDK Python dependencies OK')"

# Copy the deploy wrapper last so the app tree in this repo is available.
COPY . .

# Upstream self-update rewrites files under /usr/src/app; grant that runtime
# operation write access without reverting to root. Base image remains app UID.
USER root
RUN chown -R app:app /usr/src/app
USER app

CMD ["bash", "/usr/src/app/start.sh"]
