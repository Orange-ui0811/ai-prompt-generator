"""FastAPI entrypoint for Vercel and optional API-based deployments.

The existing Streamlit application remains available at ``src/webui.py``.
Vercel automatically discovers the top-level ``app`` object in this file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from src.engine import PromptGenerator
from src.models import LLMConfig, ProjectProfile


PROJECT_ROOT = Path(__file__).resolve().parent
PUBLIC_INDEX = PROJECT_ROOT / "public" / "index.html"

app = FastAPI(
    title="AI Project Prompt Generator",
    description="Generate project prompts with the shared OrangeVC prompt engine.",
    version="1.0.0",
)


class GenerateRequest(BaseModel):
    """Request shared by the single, all, and master generation endpoints."""

    profile: ProjectProfile = Field(default_factory=ProjectProfile)
    mode: Literal["standalone", "pure"] = "standalone"
    use_llm: bool = False


class SingleGenerateRequest(GenerateRequest):
    stage_id: int = Field(default=0, ge=0, le=13)


@lru_cache(maxsize=1)
def get_generator() -> PromptGenerator:
    return PromptGenerator(
        templates_dir=PROJECT_ROOT / "templates",
        config_dir=PROJECT_ROOT / "config",
    )


def get_llm_client(enabled: bool):
    """Create an LLM client from environment variables when explicitly requested."""

    if not enabled:
        return None

    config = LLMConfig.from_env()
    if not config.is_ready():
        raise HTTPException(
            status_code=400,
            detail=(
                "AI enhancement is enabled, but LLM_API_KEY, LLM_BASE_URL, "
                "or LLM_MODEL is missing."
            ),
        )

    from src.llm.client import LLMClient

    return LLMClient(config)


def run_generation(callback):
    """Convert expected generator errors into browser-friendly API responses."""

    try:
        return callback()
    except HTTPException:
        raise
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc


@app.get("/", include_in_schema=False)
def home():
    # Vercel serves public/** through its CDN. The redirect also keeps the API
    # entrypoint independent from Vercel's read-only function filesystem.
    return RedirectResponse(url="/index.html", status_code=307)


@app.get("/index.html", include_in_schema=False)
def local_index():
    """Serve the same frontend when running locally with uvicorn."""

    if not PUBLIC_INDEX.exists():
        raise HTTPException(status_code=404, detail="Frontend file not found")
    return FileResponse(PUBLIC_INDEX)


@app.get("/health", include_in_schema=False)
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ai-prompt-generator"}


@app.get("/api/stages")
def stages():
    generator = get_generator()
    return [
        {
            "id": stage.id,
            "name": stage.name,
            "description": stage.description,
            "key_points": stage.key_points,
        }
        for stage in generator.stages.values()
    ]


@app.post("/api/generate/single")
def generate_single(request: SingleGenerateRequest):
    def generate():
        result = get_generator().generate_single(
            profile=request.profile,
            stage_id=request.stage_id,
            mode=request.mode,
            llm_client=get_llm_client(request.use_llm),
        )
        return result.model_dump()

    return run_generation(generate)


@app.post("/api/generate/all")
def generate_all(request: GenerateRequest):
    def generate():
        result = get_generator().generate_all(
            profile=request.profile,
            mode=request.mode,
            llm_client=get_llm_client(request.use_llm),
        )
        return result.model_dump()

    return run_generation(generate)


@app.post("/api/generate/master")
def generate_master(request: GenerateRequest):
    def generate():
        result = get_generator().generate_master(
            profile=request.profile,
            mode=request.mode,
            llm_client=get_llm_client(request.use_llm),
        )
        return result.model_dump()

    return run_generation(generate)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
