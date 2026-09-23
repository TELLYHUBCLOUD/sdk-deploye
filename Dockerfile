FROM tellyhubcloud/mltbsdk:latest
WORKDIR /usr/src/app

COPY requirements.txt .

RUN uv venv --clear /usr/src/app/.venv
ENV PATH="/usr/src/app/.venv/bin:$PATH"
RUN uv pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
