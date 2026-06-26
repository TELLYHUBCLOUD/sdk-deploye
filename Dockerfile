FROM irisxdr/neo-wzml:latest

WORKDIR /usr/src/app

COPY requirements.txt .

# Existing venv ko clear karke recreate karo
RUN uv venv --clear /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
