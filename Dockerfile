FROM tellyhubcloud/mltbsdk:latest

WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/requirements.txt

# Keep an explicit virtual environment and make uv/python resolve to it.
RUN uv venv --clear /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PYTHONPATH=/usr/src/app \
    PATH="/opt/venv/bin:$PATH"

RUN uv pip install --python /opt/venv/bin/python --no-cache-dir -r /usr/src/app/requirements.txt

COPY . /usr/src/app

# Runtime updater resets /usr/src/app to a selected upstream branch. Keep the
# trusted entrypoint, updater, and policy patcher outside that mutable tree.
COPY start.sh /usr/local/bin/telly-entrypoint.sh
COPY update.py /usr/local/bin/telly-updater.py
COPY heroku_policy_patch.py /usr/local/bin/heroku_policy_patch.py

RUN chmod 0755 \
    /usr/local/bin/telly-entrypoint.sh \
    /usr/local/bin/telly-updater.py \
    /usr/local/bin/heroku_policy_patch.py

CMD ["bash", "/usr/local/bin/telly-entrypoint.sh"]
