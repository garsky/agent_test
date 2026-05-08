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
    <hr style="border-color:#0f3460;margin:10px 0">
    <h3>添加平台</h3>
    <input id="newVendorId" placeholder="厂商ID (如 xiaomi)" style="width:100%;padding:6px;margin-bottom:4px;border-radius:4px;border:1px solid #0f3460;background:#1a1a2e;color:#e0e0e0;font-size:12px">
    <input id="newVendorName" placeholder="显示名 (如 小米)" style="width:100%;padding:6px;margin-bottom:4px;border-radius:4px;border:1px solid #0f3460;background:#1a1a2e;color:#e0e0e0;font-size:12px">
    <button onclick="addVendor()" style="background:#0f3460;font-size:12px">添加厂商</button>
    <div id="addSubSection" style="display:none;margin-top:8px">
      <input id="newSubId" placeholder="子平台ID (如 surya)" style="width:100%;padding:6px;margin-bottom:4px;border-radius:4px;border:1px solid #0f3460;background:#1a1a2e;color:#e0e0e0;font-size:12px">
      <input id="newSubName" placeholder="显示名 (如 Surya)" style="width:100%;padding:6px;margin-bottom:4px;border-radius:4px;border:1px solid #0f3460;background:#1a1a2e;color:#e0e0e0;font-size:12px">
      <button onclick="addSubPlatform()" style="background:#0f3460;font-size:12px">添加子平台</button>
    </div>
    <div class="hint">
      提问技巧:<br>
      1. 附上平台信息<br>
      2. 粘贴关键日志<br>
      3. 指定问题类型<br>
      <br>
      知识库管理 (CLI):<br>
      kb add &lt;文件&gt; 添加文档<br>
      支持: .md .txt .pdf .docx<br>
      .pptx .xlsx<br>
      kb update 增量更新索引<br>
      kb build 重建索引<br>
      kb search &lt;词&gt; 搜索<br>
      <br>
      文件格式: .md .txt .pdf<br>
      .docx .pptx .xlsx<br>
      自动转换并更新索引
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
const FALLBACK_VENDORS = [
  {id:'qualcomm', display_name:'高通 (Qualcomm)'},
  {id:'mtk', display_name:'MTK (MediaTek)'},
  {id:'unisoc', display_name:'展锐 (UNISOC)'}
];
const FALLBACK_SUB_PLATFORMS = {
  qualcomm: [{id:'sm8550',display_name:'SM8550'},{id:'sm8650',display_name:'SM8650'},{id:'qcm4490',display_name:'QCM4490'}],
  mtk: [{id:'mt6985',display_name:'MT6985 (24E)'},{id:'mt6989',display_name:'MT6989'},{id:'mt6897',display_name:'MT6897'}],
  unisoc: [{id:'t820',display_name:'T820'},{id:'t770',display_name:'T770'},{id:'t750',display_name:'T750'}]
};
async function loadVendors() {
  try {
    const r = await fetch(API+'/api/v1/platforms/vendors', {cache:'no-store'});
    if (!r.ok) throw new Error('HTTP '+r.status);
    const vendors = await r.json();
    const sel = document.getElementById('vendor');
    vendors.forEach(v => { const o = document.createElement('option'); o.value = v.id; o.textContent = v.display_name; sel.appendChild(o); });
    if (vendors.length > 0) { document.getElementById('platformInfo').textContent='请选择平台厂商'; return; }
  } catch(e) { console.warn('API failed, using fallback vendors:', e); }
  const sel = document.getElementById('vendor');
  FALLBACK_VENDORS.forEach(v => { const o = document.createElement('option'); o.value = v.id; o.textContent = v.display_name; sel.appendChild(o); });
  document.getElementById('platformInfo').textContent='请选择平台厂商 (离线模式)';
}
async function loadSubPlatforms() {
  const vid = document.getElementById('vendor').value;
  if (!vid) return;
  try {
    const r = await fetch(API+'/api/v1/platforms/vendors/'+vid+'/sub-platforms', {cache:'no-store'});
    if (!r.ok) throw new Error('HTTP '+r.status);
    const sps = await r.json();
    const sel = document.getElementById('subPlatform');
    sel.innerHTML = '<option value="">选择子平台</option>';
    sel.disabled = false;
    sps.forEach(sp => { const o = document.createElement('option'); o.value = sp.id; o.textContent = sp.display_name; sel.appendChild(o); });
    if (sps.length > 0) return;
  } catch(e) { console.warn('API failed, using fallback sub-platforms:', e); }
  const sel = document.getElementById('subPlatform');
  sel.innerHTML = '<option value="">选择子平台</option>';
  sel.disabled = false;
  (FALLBACK_SUB_PLATFORMS[vid]||[]).forEach(sp => { const o = document.createElement('option'); o.value = sp.id; o.textContent = sp.display_name; sel.appendChild(o); });
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
  text = text.replace(/<think[\\s\\S]*?<\\/think>/gi, '');
  text = text.replace(/```(\\w*)\\n/g, '<pre><code>');
  text = text.replace(/```/g, '</code></pre>');
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
  text = text.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
  text = text.replace(/\\n/g, '<br>');
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
async function addVendor() {
  const vid = document.getElementById('newVendorId').value.trim();
  const dname = document.getElementById('newVendorName').value.trim();
  if (!vid || !dname) { alert('请输入厂商ID和显示名'); return; }
  try {
    const r = await fetch(API+'/api/v1/platforms/vendors', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({vendor_id:vid, display_name:dname})});
    const data = await r.json();
    if (r.ok) { alert('添加成功'); document.getElementById('newVendorId').value=''; document.getElementById('newVendorName').value=''; loadVendors(); }
    else { alert('添加失败: '+data.detail); }
  } catch(e) { alert('网络错误: '+e.message); }
}
async function addSubPlatform() {
  const vid = document.getElementById('vendor').value;
  const spid = document.getElementById('newSubId').value.trim();
  const dname = document.getElementById('newSubName').value.trim();
  if (!vid) { alert('请先选择厂商'); return; }
  if (!spid || !dname) { alert('请输入子平台ID和显示名'); return; }
  try {
    const r = await fetch(API+'/api/v1/platforms/sub-platforms', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({vendor_id:vid, sub_platform_id:spid, display_name:dname})});
    const data = await r.json();
    if (r.ok) { alert('添加成功'); document.getElementById('newSubId').value=''; document.getElementById('newSubName').value=''; loadSubPlatforms(); }
    else { alert('添加失败: '+data.detail); }
  } catch(e) { alert('网络错误: '+e.message); }
}
document.getElementById('vendor').addEventListener('change', function() {
  document.getElementById('addSubSection').style.display = this.value ? 'block' : 'none';
});
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
        version="1.0.4",
        description="AI Agent for Android Camera driver issue diagnosis",
    )

    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

    class VendorAddRequest(BaseModel):
        vendor_id: str
        display_name: str

    class SubPlatformAddRequest(BaseModel):
        vendor_id: str
        sub_platform_id: str
        display_name: str

    @app.post("/api/v1/platforms/vendors")
    async def add_vendor(req: VendorAddRequest):
        from platforms.registry import _sanitize_id
        vid = _sanitize_id(req.vendor_id)
        result = platform_manager.add_vendor(vid, req.display_name)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result

    @app.post("/api/v1/platforms/sub-platforms")
    async def add_sub_platform(req: SubPlatformAddRequest):
        from platforms.registry import _sanitize_id
        spid = _sanitize_id(req.sub_platform_id)
        result = platform_manager.add_sub_platform(req.vendor_id, spid, req.display_name)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result

    @app.delete("/api/v1/platforms/vendors/{vendor_id}")
    async def remove_vendor(vendor_id: str):
        result = platform_manager.remove_vendor(vendor_id)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result

    @app.delete("/api/v1/platforms/vendors/{vendor_id}/sub-platforms/{sub_platform_id}")
    async def remove_sub_platform(vendor_id: str, sub_platform_id: str):
        result = platform_manager.remove_sub_platform(vendor_id, sub_platform_id)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result

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

            kb_status = None
            try:
                from knowledge.builder import update_knowledge_base
                result = update_knowledge_base(req.vendor_id, req.sub_platform_id)
                kb_status = result
            except Exception:
                pass

            return {
                "session_id": session_id,
                "platform": context.display_string,
                "kb_update": kb_status,
            }
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

    @app.post("/api/v1/kb/{vendor_id}/{sub_platform_id}/update")
    async def kb_update(vendor_id: str, sub_platform_id: str):
        try:
            from knowledge.builder import update_knowledge_base
            result = update_knowledge_base(vendor_id, sub_platform_id)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/kb/{vendor_id}/{sub_platform_id}/list")
    async def kb_list(vendor_id: str, sub_platform_id: str):
        from pathlib import Path
        from config.settings import settings
        docs_dir = Path(settings.KNOWLEDGE_BASE_DIR) / vendor_id / sub_platform_id / "platform_docs"
        if not docs_dir.exists():
            return {"files": [], "directory": str(docs_dir)}
        files = list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.txt"))
        return {
            "files": [{"name": f.name, "size": f.stat().st_size} for f in files],
            "directory": str(docs_dir),
        }

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
