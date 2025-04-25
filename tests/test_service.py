# tests/test_service.py

import pytest
import grpc
from trendstory.server import StoryServiceServicer, VALID_REGIONS, VALID_THEMES
from trendstory.story_service_pb2 import GenerateRequest

# A small exception type to simulate context.abort() behavior
class DummyRpcError(Exception):
    def __init__(self, code, details):
        super().__init__(details)
        self._code = code
        self._details = details
    def code(self):
        return self._code
    def details(self):
        return self._details

# A fake ServicerContext that just throws our DummyRpcError
class DummyContext:
    def abort(self, code, details):
        raise DummyRpcError(code, details)

@pytest.fixture(autouse=True)
def patch_allowlists(monkeypatch):
    """
    Override VALID_REGIONS/THEMES so we have a predictable, tiny allow-list:
      REGIONS = {"US", "GB"}
      THEMES  = {"comedy", "drama"}
    """
    import trendstory.server as server_mod
    monkeypatch.setattr(server_mod, "VALID_REGIONS", {"US", "GB"})
    monkeypatch.setattr(server_mod, "VALID_THEMES", {"comedy", "drama"})
    yield

@pytest.mark.asyncio
async def test_generate_success(monkeypatch):
    # Stub out the external logic so it can't fail
    monkeypatch.setattr(
        "trendstory.logic.get_google_trends_api",
        lambda region, top_n: ["one", "two"]
    )
    monkeypatch.setattr(
        "trendstory.logic.get_youtube_trending",
        lambda api_key, region, max_results: ["yt1"]
    )
    monkeypatch.setattr(
        "trendstory.logic.generate_story_gemini",
        lambda theme, topics, temp: "SCRIPT"
    )

    servicer = StoryServiceServicer()
    req = GenerateRequest(
        theme="comedy",
        region_code="US",
        top_n=2,
        temperature=0.5,
        source="google"  # or "youtube"
    )
    resp = await servicer.GenerateStory(req, DummyContext())
    assert resp.script == "SCRIPT"

@pytest.mark.asyncio
async def test_generate_invalid_top_n():
    servicer = StoryServiceServicer()
    req = GenerateRequest(
        theme="comedy",
        region_code="US",
        top_n=0,                  # invalid
        temperature=0.5,
        source="google"          # or "youtube"
    )
    with pytest.raises(DummyRpcError) as exc:
        await servicer.GenerateStory(req, DummyContext())
    assert exc.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert "top_n must be > 0" in exc.value.details()

@pytest.mark.asyncio
async def test_generate_missing_theme():
    servicer = StoryServiceServicer()
    req = GenerateRequest(
        theme="",                # missing
        region_code="US",
        top_n=3,
        temperature=0.5,
        source="google"         # or "youtube"
    )
    with pytest.raises(DummyRpcError) as exc:
        await servicer.GenerateStory(req, DummyContext())
    assert exc.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert "Theme must be provided" in exc.value.details()

@pytest.mark.asyncio
async def test_generate_bad_temperature():
    servicer = StoryServiceServicer()
    # below 0.0
    req1 = GenerateRequest(theme="comedy", region_code="US", top_n=3, temperature=-0.1, source="google")
    with pytest.raises(DummyRpcError) as exc1:
        await servicer.GenerateStory(req1, DummyContext())
    assert exc1.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert "temperature must be between 0.0 and 1.0" in exc1.value.details()

    # above 1.0
    req2 = GenerateRequest(theme="comedy", region_code="US", top_n=3, temperature=1.2)
    with pytest.raises(DummyRpcError) as exc2:
        await servicer.GenerateStory(req2, DummyContext())
    assert exc2.value.code() == grpc.StatusCode.INVALID_ARGUMENT

@pytest.mark.asyncio
async def test_generate_invalid_region():
    servicer = StoryServiceServicer()
    req = GenerateRequest(
        theme="comedy",
        region_code="ZZ",         # not in {"US","GB"}
        top_n=3,
        temperature=0.5,
        source="google"         # or "youtube"
    )
    with pytest.raises(DummyRpcError) as exc:
        await servicer.GenerateStory(req, DummyContext())
    assert exc.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert "region_code must be one of" in exc.value.details()

@pytest.mark.asyncio
async def test_generate_invalid_theme():
    servicer = StoryServiceServicer()
    req = GenerateRequest(
        theme="tragedy",          # not in {"comedy","drama"}
        region_code="US",
        top_n=3,
        temperature=0.5,
        source="google"         # or "youtube"
    )
    with pytest.raises(DummyRpcError) as exc:
        await servicer.GenerateStory(req, DummyContext())
    assert exc.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert "theme must be one of" in exc.value.details()

@pytest.mark.asyncio
async def test_generate_internal_error(monkeypatch):
    # Simulate an exception deep in your logic
    monkeypatch.setattr(
        "trendstory.logic.get_google_trends_api",
        lambda region, top_n: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    servicer = StoryServiceServicer()
    req = GenerateRequest(
        theme="comedy",
        region_code="US",
        top_n=2,
        temperature=0.5,
        source="google"  # or "youtube"
    )
    with pytest.raises(DummyRpcError) as exc:
        await servicer.GenerateStory(req, DummyContext())
    assert exc.value.code() == grpc.StatusCode.INTERNAL
    assert "Internal server error" in exc.value.details()


@pytest.mark.asyncio
async def test_generate_invalid_source():
    servicer = StoryServiceServicer()
    req = GenerateRequest(
        theme="comedy",
        region_code="US",
        top_n=3,
        temperature=0.5,
        source="invalid"  # Invalid source
    )
    with pytest.raises(DummyRpcError) as exc:
        await servicer.GenerateStory(req, DummyContext())
    assert exc.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert "source must be one of" in exc.value.details()