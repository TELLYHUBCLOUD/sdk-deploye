FROM tellyhubcloud/telly-wzml:latest
WORKDIR /usr/src/app

COPY requirements.txt .

# Create venv inside the owned working directory
RUN uv venv --clear .venv
ENV PATH="/usr/src/app/.venv/bin:$PATH"
RUN uv pip install -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
