from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from platform.manager import PlatformManager
from agent.core import CameraDriverAgent
from config.llm_config import LLMConfig


app: Optional[FastAPI] = None
platform_manager: Optional[PlatformManager] = None
agents: dict[str, CameraDriverAgent] = {}


class SessionCreateRequest(BaseModel):
    vendor_id: str
    sub_platform_id: str
    project_id: str


class ChatRequest(BaseModel):
    message: str


class ProjectCreateRequest(BaseModel):
    name: str


class LLMConfigRequest(BaseModel):
    provider: str = "minimax"
    api_key: str = ""
    model: str = ""
    base_url: str = ""


def create_app() -> FastAPI:
    global app, platform_manager

    app = FastAPI(
        title="Camera Driver Agent API",
        version="0.2.1",
        description="AI Agent for Android Camera driver issue diagnosis",
    )
    platform_manager = PlatformManager()

    @app.get("/api/v1/platforms/vendors")
    async def get_vendors():
        return platform_manager.get_vendors()

    @app.get("/api/v1/platforms/vendors/{vendor_id}/sub-platforms")
    async def get_sub_platforms(vendor_id: str):
        return platform_manager.get_sub_platforms(vendor_id)

    @app.get("/api/v1/platforms/sub-platforms/{sub_platform_id}/projects")
    async def get_projects(vendor_id: str, sub_platform_id: str):
        return platform_manager.get_projects(vendor_id, sub_platform_id)

    @app.post("/api/v1/platforms/sub-platforms/{sub_platform_id}/projects")
    async def create_project(vendor_id: str, sub_platform_id: str, req: ProjectCreateRequest):
        return platform_manager.create_project(vendor_id, sub_platform_id, req.name)

    @app.post("/api/v1/sessions")
    async def create_session(req: SessionCreateRequest):
        try:
            context = platform_manager.set_context(req.vendor_id, req.sub_platform_id, req.project_id)
            agent = CameraDriverAgent(context)
            session_id = f"{req.vendor_id}_{req.sub_platform_id}_{req.project_id}"
            agents[session_id] = agent
            return {"session_id": session_id, "platform": context.display_string}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/sessions/{session_id}/chat")
    async def chat(session_id: str, req: ChatRequest):
        agent = agents.get(session_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Session not found")
        response = await agent.chat(req.message)
        return {"response": response, "session_id": session_id}

    @app.delete("/api/v1/sessions/{session_id}")
    async def delete_session(session_id: str):
        if session_id in agents:
            del agents[session_id]
        return {"status": "ok"}

    @app.get("/api/v1/config/llm")
    async def get_llm_config():
        config = LLMConfig.from_settings()
        return {"provider": config.provider, "model": config.model, "base_url": config.base_url}

    @app.put("/api/v1/config/llm")
    async def update_llm_config(req: LLMConfigRequest):
        return {"status": "ok", "message": "LLM配置已更新，新会话将使用新配置"}

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
