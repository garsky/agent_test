from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from platforms.manager import PlatformManager
from agent.core import CameraDriverAgent
from config.llm_config import LLMConfig


app: Optional[FastAPI] = None
platform_manager: Optional[PlatformManager] = None
agents: dict[str, CameraDriverAgent] = {}

CHAT_PAGE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Camera Driver Agent</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #1a1a2e; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }
.header { background: #16213e; padding: 12px 20px; border-bottom: 1px solid #0f3460; display: flex; align-items: center; gap: 16px; }
.header h1 { font-size: 18px; color: #e94560; }
.header .platform-info { font-size: 13px; color: #a0a0a0; }
.main { display: flex; flex: 1; overflow: hidden; }
.sidebar { width: 260px; background: #16213e; border-right: 1px solid #0f3460; padding: 16px; overflow-y: auto; }
.sidebar h3 { color: #e94560; margin-bottom: 10px; font-size: 14px; }
.sidebar select, .sidebar button { width: 100%; padding: 8px; margin-bottom: 8px; border-radius: 6px; border: 1px solid #0f3460; background: #1a1a2e; color: #e0e0e0; font-size: 13px; }
.sidebar button { background: #e94560; border: none; cursor: pointer; font-weight: bold; margin-top: 8px; }
.sidebar button:hover { background: #c73652; }
.sidebar .hint { font-size: 11px; color: #666; margin-top: 12px; line-height: 1.6; }
.chat-area { flex: 1; display: flex; flex-direction: column; }
.messages { flex: 1; overflow-y: auto; padding: 20px; }
.msg { margin-bottom: 16px; max-width: 80%; }
.msg.user { margin-left: auto; }
.msg .bubble { padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
.msg .bubble pre { background: #0f0f23; padding: 10px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }
.msg .bubble code { background: #0f0f23; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
.msg .bubble pre code { background: none; padding: 0; }
.msg.user .bubble { background: #e94560; color: white; border-bottom-right-radius: 4px; }
.msg.agent .bubble { background: #16213e; border: 1px solid #0f3460; border-bottom-left-radius: 4px; }
.msg .label { font-size: 11px; color: #666; margin-bottom: 4px; }
.input-area { padding: 16px; background: #16213e; border-top: 1px solid #0f3460; display: flex; gap: 10px; }
.input-area textarea { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #0f3460; background: #1a1a2e; color: #e0e0e0; font-size: 14px; resize: none; height: 44px; font-family: inherit; }
.input-area button { padding: 10px 20px; border-radius: 8px; border: none; background: #e94560; color: white; font-weight: bold; cursor: pointer; }
.input-area button:hover { background: #c73652; }
.input-area button:disabled { background: #555; cursor: not-allowed; }
</style>
</head>
<body>
<div class="header">
  <h1>Camera Driver Agent</h1>
  <span class="platform-info" id="platformInfo">请先选择平台</span>
</div>
<div class="main">
  <div class="sidebar">
    <h3>平台选择</h3>
    <select id="vendor" onchange="loadSubPlatforms()"><option value="">选择平台厂商</option></select>
    <select id="subPlatform" disabled><option value="">选择子平台</option></select>
    <button onclick="createSession()">连接</button>
    <div class="hint">
      提问技巧:<br>
      1. 附上平台信息<br>
      2. 粘贴关键日志<br>
      3. 指定问题类型<br>
      <br>
      知识库管理 (CLI):<br>
      kb add &lt;文件&gt; 添加文档<br>
      kb list 查看文件列表<br>
      kb build 重建索引<br>
      kb search &lt;词&gt; 搜索<br>
      <br>
      文件格式: .md / .txt<br>
      添加后需 kb build 生效
    </div>
  </div>
  <div class="chat-area">
    <div class="messages" id="messages"></div>
    <div class="input-area">
      <textarea id="input" placeholder="输入问题..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage()}"></textarea>
      <button id="sendBtn" onclick="sendMessage()" disabled>发送</button>
    </div>
  </div>
</div>
<script>
let sessionId = null;
const API = '';
async function loadVendors() {
  const r = await fetch(API+'/api/v1/platforms/vendors');
  const vendors = await r.json();
  const sel = document.getElementById('vendor');
  vendors.forEach(v => { const o = document.createElement('option'); o.value = v.id; o.textContent = v.display_name; sel.appendChild(o); });
}
async function loadSubPlatforms() {
  const vid = document.getElementById('vendor').value;
  if (!vid) return;
  const r = await fetch(API+'/api/v1/platforms/vendors/'+vid+'/sub-platforms');
  const sps = await r.json();
  const sel = document.getElementById('subPlatform');
  sel.innerHTML = '<option value="">选择子平台</option>';
  sel.disabled = false;
  sps.forEach(sp => { const o = document.createElement('option'); o.value = sp.id; o.textContent = sp.display_name; sel.appendChild(o); });
}
async function createSession() {
  const vid = document.getElementById('vendor').value;
  const spid = document.getElementById('subPlatform').value;
  if (!vid || !spid) { alert('请选择平台和子平台'); return; }
  const pid = '1';
  const r = await fetch(API+'/api/v1/sessions', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({vendor_id:vid, sub_platform_id:spid, project_id:pid})});
  const data = await r.json();
  if (r.ok) {
    sessionId = data.session_id;
    document.getElementById('platformInfo').textContent = data.platform;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('messages').innerHTML = '';
    addMsg('agent', '已连接到 '+data.platform+'，可以开始提问了！');
  } else { alert('连接失败: '+(data.detail||'未知错误')); }
}
async function sendMessage() {
  if (!sessionId) { alert('请先选择平台并连接'); return; }
  const input = document.getElementById('input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  addMsg('user', msg);
  document.getElementById('sendBtn').disabled = true;
  const loadingId = addMsg('agent', '思考中...');
  try {
    const r = await fetch(API+'/api/v1/sessions/'+sessionId+'/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:msg})});
    const data = await r.json();
    removeMsg(loadingId);
    addMsg('agent', cleanResponse(data.response || '无响应'));
  } catch(e) { removeMsg(loadingId); addMsg('agent', '错误: '+e.message); }
  document.getElementById('sendBtn').disabled = false;
}
function cleanResponse(text) {
  text = text.replace(/<think[\s\S]*?<\/think>/gi, '');
  text = text.replace(/```(\w*)\n/g, '<pre><code>');
  text = text.replace(/```/g, '</code></pre>');
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/\n/g, '<br>');
  return text.trim() || '无响应';
}
let msgCounter = 0;
function addMsg(role, text) {
  const id = 'msg_' + (++msgCounter);
  const div = document.createElement('div');
  div.className = 'msg '+role;
  div.id = id;
  if (role === 'agent' && text.includes('<')) {
    div.innerHTML = '<div class="label">'+(role==='user'?'你':'Agent')+'</div><div class="bubble">'+text+'</div>';
  } else {
    div.innerHTML = '<div class="label">'+(role==='user'?'你':'Agent')+'</div><div class="bubble">'+text.replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>')+'</div>';
  }
  document.getElementById('messages').appendChild(div);
  document.getElementById('messages').scrollTop = 99999;
  return id;
}
function removeMsg(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}
loadVendors();
</script>
</body>
</html>"""


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
        version="0.4.0",
        description="AI Agent for Android Camera driver issue diagnosis",
    )
    platform_manager = PlatformManager()

    @app.get("/", response_class=HTMLResponse)
    async def chat_page():
        return CHAT_PAGE_HTML

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
    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
