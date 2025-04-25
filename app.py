import streamlit as st
import os, grpc, yaml
from trendstory import story_service_pb2, story_service_pb2_grpc
from trendstory.logic import fetch_youtube_regions

# 1) Connect to gRPC server
channel = grpc.insecure_channel("localhost:50051")
stub = story_service_pb2_grpc.StoryServiceStub(channel)

YT_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YT_API_KEY:
    st.error("Missing YOUTUBE_API_KEY environment variable")
    st.stop()


# ——— Load themes from YAML ———
with open("config/themes.yaml", "r") as f:
    config = yaml.safe_load(f)
THEMES = config.get("themes", [])

try:
    region_map = fetch_youtube_regions(YT_API_KEY)
except Exception as e:
    st.error(f"Error fetching regions: {e}")
    region_map = {}


st.title("🎬 TrendStory Generator")
theme = st.selectbox("Theme", options=THEMES)
region = st.selectbox(
     "Region",
     options=list(region_map.keys()),
     format_func=lambda code: f"{code} — {region_map[code]}"
)
top_n      = st.slider("Top N Trends", 1, 20, 5)
temperature= st.slider("Temperature", 0.0, 1.0, 0.8)
source = st.selectbox("Source", options=["google", "youtube"])


if st.button("Generate"):
    with st.spinner("Generating script…"):
        req = story_service_pb2.GenerateRequest(
            theme=theme,
            region_code=region,
            top_n=top_n,
            temperature=temperature,
            source=source
        )
        res = stub.GenerateStory(req)
        st.code(res.script)
