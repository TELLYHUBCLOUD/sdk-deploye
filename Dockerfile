FROM tellyhubcloud/telly-wzml:latest

WORKDIR /usr/src/app

# The DOCKERSDK base image already provides Python 3.14.9, uv, and a
# pre-created /usr/src/app/.venv with system-site-packages. Keep that venv:
# recreating it here breaks ownership and its base-interpreter relationship.
COPY requirements.txt /tmp/sdk-requirements.txt

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_LINK_MODE=copy

# Install the app's pinned dependencies into the base image's existing venv.
RUN uv pip install --python /usr/src/app/.venv/bin/python --no-cache-dir -r /tmp/sdk-requirements.txt \
    && rm -f /tmp/sdk-requirements.txt \
    && /usr/src/app/.venv/bin/python -c "import aiohttp, motor, pymongo; print('SDK Python dependencies OK')"

# Copy the deployment wrapper and bot entrypoint after installing dependencies.
COPY . .

# DOCKERSDK's app user owns /usr/src/app. Avoid switching back to root.
# Run the wrapper explicitly with the image's virtualenv interpreter.
CMD ["/usr/src/app/.venv/bin/python", "update.py"]
