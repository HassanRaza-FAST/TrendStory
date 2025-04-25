# TrendStory
Extract current trends (for the past 24hrs, from Youtube or Google) and generate a story script in a particular theme of your choice.

## Overview
TrendStory is a Python-based gRPC service that fetches trending topics from Google and YouTube, then leverages the Gemini API to generate creative story scripts based on these trends. It's designed to be run in a Docker container and accessed via gRPC client calls.

## Prerequisites
- Docker installed on your system
- A valid `YOUTUBE_API_KEY` for accessing YouTube's trending data
- A properly formatted `config/themes.yaml` file that lists all allowed themes

## Project Structure
```
.
├── Dockerfile
├── requirements.txt
├── proto/
│   └── story_service.proto
├── trendstory/
│   ├── logic.py
│   ├── server.py
│   ├── story_service_pb2.py
│   └── story_service_pb2_grpc.py
├── config/
│   └── themes.yaml
└── app.py  # optional Streamlit client
```

## Setup and Deployment

### 1. Build the Docker image
```bash
docker build -t trendstory-server .
```

### 2. Run the container
```bash
docker run -d \
  -p 50051:50051 \
  -e YOUTUBE_API_KEY=your_key_here \
  --name trendstory \
  trendstory-server
```

### 3. Test with grpcurl
Install grpcurl first, then test the service:
```bash
grpcurl -plaintext \
  -d '{
        "theme":"comedy",
        "region_code":"US",
        "top_n":5,
        "temperature":0.8,
        "source":"google"
      }' \
  localhost:50051 \
  trendstory.StoryService/GenerateStory
```

You should receive a response similar to:
```json
{
  "script": "INT. ... your generated screenplay here ..."
}
```

## API Parameters
- **theme**: The creative theme for your story (must be defined in themes.yaml)
- **region_code**: Two-letter country code for localized trends (e.g., "US")
- **top_n**: Number of top trending topics to consider
- **temperature**: Controls creativity level (0.0-1.0)
- **source**: Data source - either "google" or "youtube"

## Configuration
Ensure your `config/themes.yaml` contains a list of themes that the service will accept. This helps prevent inappropriate content generation.
