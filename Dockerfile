FROM tellyhubcloud/mltbsdk:latest

WORKDIR /app
RUN chmod 777 /app

COPY requirements.txt .
RUN uv venv --clear /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache-dir -r requirements.txt
COPY . .

RUN find . -maxdepth 1 -type f -name "*.sh" -exec sed -i 's/\r$//' {} +

# Start application
CMD ["bash", "start.sh"]
