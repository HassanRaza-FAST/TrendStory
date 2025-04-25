import asyncio
import grpc
import logging
import os
import yaml

from trendstory import story_service_pb2, story_service_pb2_grpc, logic
from trendstory.logic import fetch_youtube_regions

# — Load valid region codes —
YT_API_KEY = os.getenv("YOUTUBE_API_KEY")
try:
    _region_map = fetch_youtube_regions(YT_API_KEY)
except Exception:
    logging.warning("YouTube regions fetch failed, assigning empty")
    _region_map = {}
VALID_REGIONS = set(_region_map.keys())

# — Load valid themes from your YAML file —
with open("config/themes.yaml", "r") as f:
    config = yaml.safe_load(f)
_VALID_THEMES = config.get("themes", [])
VALID_THEMES = set(_VALID_THEMES)


class StoryServiceServicer(story_service_pb2_grpc.StoryServiceServicer):
    async def GenerateStory(self, request, context):

        
        # 1) Validate inputs
        if request.top_n <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "top_n must be > 0")
        if not request.theme:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Theme must be provided")
        if not request.region_code:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Region code must be provided")
        if not request.top_n:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "top_n must be provided")
        if not request.temperature:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "temperature must be provided")
        if not request.source:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "source must be provided")

            

        if request.source not in {"google", "youtube"}:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "source must be one of: 'google', 'youtube'"
            )
        
      
        if request.top_n > 20:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "top_n must be <= 20")

        if request.temperature < 0.0 or request.temperature > 1.0:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "temperature must be between 0.0 and 1.0"
            )

    
        # region_code must be in our allow‑list
        if request.region_code not in VALID_REGIONS:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"region_code must be one of: {sorted(VALID_REGIONS)}"
            )

        # theme must be in our allow‑list
        if request.theme not in VALID_THEMES:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"theme must be one of: {VALID_THEMES}"
            )

        # 2) Fetch topics & generate
        try:
            topics = []
            if request.source in {"google"}:
                gt = logic.get_google_trends_api(request.region_code, request.top_n)
                logging.info(f"Google Trends: {gt}")
                topics.extend(gt)
            if request.source in {"youtube"}:
                yt = logic.get_youtube_trending(os.getenv("YOUTUBE_API_KEY"), request.region_code, request.top_n)
                logging.info(f"YouTube Trending: {yt}")
                topics.extend(yt)

            # Generate the story
            script = logic.generate_story_gemini(request.theme, topics, temp=request.temperature)
            logging.info(f"Generated script: {script}")
            return story_service_pb2.GenerateResponse(script=script)
        except Exception as e:
            logging.exception("Error in GenerateStory")
            context.abort(grpc.StatusCode.INTERNAL, "Internal server error")

async def serve():
    server = grpc.aio.server()
    story_service_pb2_grpc.add_StoryServiceServicer_to_server(StoryServiceServicer(), server)
    server.add_insecure_port("[::]:50051")
    await server.start()
    logging.info("gRPC server listening on 50051")
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())

#TODO:
# 3. Docker
# 4. Documentation(readme)
# 5. Uninstall C:\Users\Wajeeha Raza\AppData\Local\ms-playwright\