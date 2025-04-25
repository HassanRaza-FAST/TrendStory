# trendstory/logic.py
import os, sys, logging, requests, json
from dotenv import load_dotenv
from googleapiclient.discovery import build
from pytrends.request import TrendReq
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

load_dotenv()
logging.basicConfig(level=logging.INFO)


# ——————————————————————————————————————————————————————————————————————————————
def make_requests_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/116.0.0.0 Safari/537.36"
        ),
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    })
    return s

def extract_json_from_response(text: str):
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            try:
                outer = json.loads(line)
                inner = json.loads(outer[0][2])
                return inner[1]
            except Exception as e:
                logging.warning(f"JSON parse error: {e}")
    logging.error("No valid JSON payload found in response")
    return None

def get_google_trends_api(region_code: str = "US", top_n: int = 20) -> list[str]:
    logging.info("Fetching Google Trends via batchExecute API…")
    session = make_requests_session()
    url = "https://trends.google.com/_/TrendsUi/data/batchexecute"
    geo = region_code.upper()
    payload = f'f.req=[[[i0OFE,"[null,null,\'{geo}\',0,null,48]"]]]'
    try:
        resp = session.post(url, data=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error fetching Google Trends: {e}")
        return []
    data = extract_json_from_response(resp.text) or []
    terms = [item[0].lower() for item in data if isinstance(item, list) and item]
    return list(dict.fromkeys(terms))[:top_n]

def get_youtube_trending(api_key: str, region_code: str = "US", max_results: int = 10) -> list[str]:
    yt = build("youtube", "v3", developerKey=api_key)
    req = yt.videos().list(
        part="snippet",
        chart="mostPopular",
        regionCode=region_code.upper(),
        maxResults=max_results,
    )
    res = req.execute()
    return [item["snippet"]["title"] for item in res.get("items", [])]

def generate_story_gemini(theme: str, topics: list[str], temp: float = 0.8) -> str:
    """
    Uses Gemini 2.0 Flash to write a highly creative, entertaining screenplay.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("Missing GEMINI_API_KEY env var")
        sys.exit(1)
    genai.configure(api_key=api_key)

    # 1) Build a GenerationConfig to control randomness
    generation_config = GenerationConfig(
        temperature=temp,    # 0.0 = deterministic, 1.0 = very creative :contentReference[oaicite:0]{index=0}
        top_p=0.9            # optional: nucleus sampling threshold :contentReference[oaicite:1]{index=1}
    )

    # 2) Instantiate model with your custom config
    model = genai.GenerativeModel(
        model_name="models/gemini-2.0-flash",
        generation_config=generation_config
    )

    # 3) A beefed‑up prompt that asks for true screenplay format
    prompt = (
        "You're an award-winning screenwriter. "
        "Write a wildly creative, entertaining, cinematic screenplay in **industry-standard** format with the theme '{theme}':\n"
        "- EXT./INT. scene headings\n"
        "- ACTION lines describing setting & mood\n"
        "- CHARACTER names, parentheticals, and dialogue\n\n"
        "Weave together these trending topics:\n"
        + "\n".join(f"- {t}" for t in topics)
    )

    # 4) Generate and return
    response = model.generate_content(prompt)
    return response.text.strip()

def fetch_youtube_regions(api_key: str) -> dict[str, str]:
    """
    Returns a mapping of ISO‑3166 alpha‑2 region codes → human‑readable names,
    using YouTube’s i18nRegions endpoint.
    """
    yt = build("youtube", "v3", developerKey=api_key)
    resp = yt.i18nRegions().list(part="snippet").execute()
    return {
        item["snippet"]["gl"]: item["snippet"]["name"]
        for item in resp.get("items", [])
    }