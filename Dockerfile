# Dockerfile
# --------------
# 1. Base image
FROM python:3.10-slim

# 2. Set working directory
WORKDIR /app

# 3. Install system deps (if you need protoc or other tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy and install Python dependencies
#    (you can also COPY requirements.txt and pip install that)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy your code
COPY proto ./proto
COPY trendstory ./trendstory
COPY config ./config
COPY app.py .
COPY server.py .

# 6. (Re)generate the gRPC stubs in‐image
RUN python -m grpc_tools.protoc \
      -I=proto \
      --python_out=trendstory \
      --grpc_python_out=trendstory \
      proto/story_service.proto

# 7. Expose the gRPC port
EXPOSE 50051

# 8. Launch the server by default
CMD ["python", "-m", "trendstory.server"]
