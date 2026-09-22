import os
import json
import base64
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()
APP_NAME = "Phul"
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_BASE = "https://router.huggingface.co/v1"
DEFAULT_MODEL = "moonshotai/Kimi-K3:together"

FALLBACK_MODELS = [{
    "id": DEFAULT_MODEL, "base_id": "moonshotai/Kimi-K3", "name": "Kimi-K3",
    "provider": "together", "description": "Advanced reasoning & multimodal", "vision": True
}]
app = FastAPI(title="Phul V3 Multi-Model AI")
client = OpenAI(base_url=HF_BASE, api_key=HF_TOKEN)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=30000)
    model: str = Field(default=DEFAULT_MODEL, min_length=1, max_length=300)
    image_data: str | None = None
    file_text: str | None = None
    deep_think: bool = False
    history: list[dict[str, Any]] = Field(default_factory=list)


def model_display_name(model_id: str) -> str:
    return model_id.split(":", 1)[0].split("/")[-1].replace("-", " ")


def normalize_models(raw: Any) -> list[dict[str, Any]]:
    result=[]; seen=set()
    for item in (raw.get("data", []) if isinstance(raw, dict) else []):
        if not isinstance(item, dict): continue
        base_id=item.get("id")
        if not isinstance(base_id,str) or not base_id: continue
        providers=item.get("providers") or []
        names=[]; together=False
        for p in providers:
            if isinstance(p,dict) and isinstance(p.get("provider"),str):
                names.append(p["provider"])
                if p["provider"]=="together" and p.get("status") in (None,"live"):
                    together=True
        effective=f"{base_id}:together" if together else f"{base_id}:fastest"
        if effective in seen: continue
        seen.add(effective)
        modalities=((item.get("architecture") or {}).get("input_modalities") or [])
        result.append({"id":effective,"base_id":base_id,"name":model_display_name(base_id),
                       "provider":"together" if together else "auto",
                       "description":"Multimodal" if "image" in modalities else "Chat model",
                       "vision":"image" in modalities,"providers":names})
    return result

@app.get("/health")
def health():
    return {"ok":True,"app":APP_NAME,"version":"3.0","default_model":DEFAULT_MODEL,"token_configured":bool(HF_TOKEN)}

@app.get("/api/models")
async def models():
    if not HF_TOKEN: return {"models":FALLBACK_MODELS,"source":"fallback"}
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            r=await http.get(f"{HF_BASE}/models",headers={"Authorization":f"Bearer {HF_TOKEN}"})
            r.raise_for_status(); discovered=normalize_models(r.json())
        ids={m["id"] for m in discovered}
        merged=[m for m in FALLBACK_MODELS if m["id"] not in ids]+discovered
        return {"models":merged[:100],"source":"huggingface-router"}
    except Exception:
        return {"models":FALLBACK_MODELS,"source":"fallback"}


def build_messages(req: ChatRequest):
    msgs=[]
    for h in req.history[-20:]:
        if not isinstance(h,dict): continue
        role=h.get("role"); content=h.get("content")
        if role in ("user","assistant") and isinstance(content,str) and content:
            msgs.append({"role":role,"content":content[:12000]})
    system="You are Phul, a helpful multi-model AI assistant. Answer clearly and accurately."
    if req.deep_think:
        system += " For this request, reason carefully, check assumptions, and give a well-structured answer. Do not reveal private chain-of-thought; provide concise conclusions and useful reasoning summaries."
    msgs.insert(0,{"role":"system","content":system})
    content: Any=req.message
    if req.file_text:
        content += "\n\n[Attached file text]\n" + req.file_text[:50000]
    if req.image_data:
        content=[{"type":"text","text":content},{"type":"image_url","image_url":{"url":req.image_data}}]
    msgs.append({"role":"user","content":content})
    return msgs

@app.post("/api/chat")
def chat(req: ChatRequest):
    if not HF_TOKEN: raise HTTPException(500,"HF_TOKEN is not configured on the server.")
    try:
        completion=client.chat.completions.create(model=req.model,messages=build_messages(req))
        return {"reply":completion.choices[0].message.content or "","model":req.model}
    except Exception as exc:
        raise HTTPException(502,str(exc))

@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    if not HF_TOKEN: raise HTTPException(500,"HF_TOKEN is not configured on the server.")
    def generate():
        try:
            stream=client.chat.completions.create(model=req.model,messages=build_messages(req),stream=True)
            for chunk in stream:
                if not chunk.choices: continue
                delta=chunk.choices[0].delta.content
                if delta:
                    yield "data: "+json.dumps({"type":"delta","text":delta},ensure_ascii=False)+"\n\n"
            yield "data: "+json.dumps({"type":"done","model":req.model})+"\n\n"
        except Exception as exc:
            yield "data: "+json.dumps({"type":"error","message":str(exc)})+"\n\n"
    return StreamingResponse(generate(),media_type="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.get("/manifest.json")
def manifest():
    return Response(json.dumps({"name":"Phul — Multi-Model AI","short_name":"Phul","start_url":"/","display":"standalone","background_color":"#070b14","theme_color":"#101a35","description":"Phul multi-model AI assistant","icons":[]}),media_type="application/manifest+json")

@app.get("/service-worker.js")
def service_worker():
    js="""const CACHE='phul-v3';self.addEventListener('install',e=>{self.skipWaiting()});self.addEventListener('activate',e=>{e.waitUntil(self.clients.claim())});self.addEventListener('fetch',e=>{if(e.request.method==='GET' && new URL(e.request.url).origin===location.origin){e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)))}});"""
    return Response(js,media_type="application/javascript")

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#070b14"><link rel="manifest" href="/manifest.json"><title>Phul — Multi-Model AI</title><style>
:root{--bg:#070b14;--panel:#0c1320;--panel2:#101a2b;--border:#263650;--text:#edf3ff;--muted:#8d9bb3;--accent:#5b6cff;--accent2:#7c3aed;--user:#2458e6}*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:var(--bg);color:var(--text);font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}body.light{--bg:#f7f9fc;--panel:#fff;--panel2:#f0f3f8;--border:#d8deea;--text:#111827;--muted:#637087;--user:#4169e1}button,textarea{font:inherit}.app{min-height:100vh;display:flex}.sidebar{width:282px;flex:0 0 282px;border-right:1px solid var(--border);background:var(--panel);padding:15px;display:flex;flex-direction:column;gap:10px}.brand{display:flex;align-items:center;gap:10px;padding:8px}.logo{width:42px;height:42px;border-radius:14px;display:grid;place-items:center;background:linear-gradient(135deg,#28a6ff,#7c3aed);font-size:23px}.brand b{font-size:23px}.brand small{display:block;color:var(--muted);margin-top:2px}.new{border:0;border-radius:13px;padding:13px 15px;background:linear-gradient(100deg,#267cff,#7546ff);color:#fff;font-size:15px;font-weight:700}.nav{display:grid;gap:2px}.nav button,.bottom button{background:transparent;border:0;color:var(--muted);text-align:left;padding:11px;border-radius:10px;font-size:14px}.nav button:hover,.bottom button:hover{background:var(--panel2);color:var(--text)}.recent-title{font-size:12px;color:var(--muted);padding:12px 8px 3px}.chat-list{overflow:auto;max-height:38vh}.chat-item{padding:10px;border-radius:10px;color:var(--text);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer}.chat-item.active,.chat-item:hover{background:var(--panel2)}.bottom{margin-top:auto;border-top:1px solid var(--border);padding-top:7px}.profile{display:flex;gap:10px;align-items:center;padding:10px}.avatar{width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#5b6cff,#1cc8a0);display:grid;place-items:center}.profile small{color:var(--muted)}.main{min-width:0;flex:1;display:flex;flex-direction:column;min-height:100vh}.top{height:68px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 18px;position:sticky;top:0;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(14px);z-index:5}.top-left{display:flex;align-items:center;gap:12px}.mobile-menu{display:none;background:transparent;border:0;color:var(--text);font-size:23px}.title{font-size:20px;font-weight:800}.online{font-size:12px;color:#48dfa0;margin-left:6px}.model-wrap{position:relative}.model-btn{border:1px solid var(--border);background:var(--panel2);color:var(--text);border-radius:13px;padding:10px 13px;min-width:175px;text-align:left;font-weight:650}.model-btn span{float:right;color:var(--muted)}.dropdown{position:absolute;right:0;top:52px;width:min(370px,calc(100vw - 24px));max-height:70vh;overflow:auto;background:var(--panel);border:1px solid var(--border);border-radius:16px;box-shadow:0 18px 50px #0009;padding:8px;display:none;z-index:20}.dropdown.open{display:block}.drop-head{padding:10px;color:var(--muted);font-size:12px;display:flex;justify-content:space-between}.search-model{width:100%;padding:9px;border:1px solid var(--border);background:var(--panel2);color:var(--text);border-radius:9px;margin-bottom:6px}.model-option{display:flex;gap:10px;align-items:center;padding:10px;border-radius:11px;cursor:pointer}.model-option:hover,.model-option.active{background:#182a54}.mi{width:34px;height:34px;border-radius:10px;background:#17285a;display:grid;place-items:center}.mn{font-size:14px;font-weight:650}.md{font-size:11px;color:var(--muted);margin-top:2px}.check{margin-left:auto;color:#61a5ff}.messages{width:min(940px,100%);margin:0 auto;padding:26px 20px 190px;flex:1}.welcome{text-align:center;padding-top:15vh;color:var(--muted)}.welcome .biglogo{width:72px;height:72px;margin:auto;border-radius:22px;display:grid;place-items:center;background:linear-gradient(135deg,#267cff,#7c3aed);font-size:34px}.welcome h1{color:var(--text);margin:14px 0 5px}.msg{display:flex;gap:10px;margin:23px 0}.msg.user{justify-content:flex-end}.bubble{max-width:86%;border-radius:18px;padding:13px 15px;line-height:1.58;overflow-wrap:anywhere}.user .bubble{background:var(--user);color:#fff}.assistant .bubble{background:var(--panel);border:1px solid var(--border)}.mlabel{font-size:11px;color:var(--muted);margin-bottom:7px}.assistant .mlabel{color:#aebbd0}.markdown h1,.markdown h2,.markdown h3{margin:14px 0 7px}.markdown p{margin:8px 0}.markdown ul,.markdown ol{padding-left:22px}.markdown blockquote{border-left:3px solid #6375ff;padding-left:12px;color:var(--muted)}.codewrap{margin:10px 0;border:1px solid var(--border);border-radius:11px;overflow:hidden;background:#050912}.codehead{display:flex;justify-content:space-between;padding:7px 10px;color:var(--muted);font-size:11px;border-bottom:1px solid var(--border)}pre{margin:0;padding:12px;overflow:auto;color:#dce7ff;font-size:12px;line-height:1.55}code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.inline-code{padding:2px 5px;border-radius:5px;background:var(--panel2);font-family:monospace;font-size:.92em}.actions{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}.action{border:1px solid var(--border);background:var(--panel2);color:var(--muted);border-radius:9px;padding:6px 9px;font-size:11px}.thinking{display:inline-flex;gap:4px;align-items:center;color:#9aabd0;background:var(--panel2);border:1px solid var(--border);padding:7px 10px;border-radius:10px;font-size:12px}.thinking i{width:5px;height:5px;border-radius:50%;background:#7ca4ff;animation:p .8s infinite alternate}.thinking i:nth-child(2){animation-delay:.2s}.thinking i:nth-child(3){animation-delay:.4s}@keyframes p{to{opacity:.25;transform:translateY(-2px)}}.attachment{display:flex;gap:10px;align-items:center;border:1px solid var(--border);background:var(--panel2);padding:9px;border-radius:11px;margin-bottom:7px}.attachment img{width:70px;height:52px;object-fit:cover;border-radius:7px}.attachment .remove{margin-left:auto}.composer{position:fixed;left:calc(50% + 141px);transform:translateX(-50%);bottom:0;width:min(940px,calc(100% - 282px));padding:10px 18px 15px;background:linear-gradient(transparent,var(--bg) 20%);z-index:10}.compose-box{background:var(--panel);border:1px solid var(--border);border-radius:17px;padding:7px;display:flex;align-items:flex-end;gap:7px}.attach{width:42px;height:42px;border:0;border-radius:12px;background:var(--panel2);color:var(--text);font-size:19px}.compose-box textarea{flex:1;min-width:0;background:transparent;color:var(--text);border:0;outline:0;resize:none;padding:11px 6px;font-size:15px;max-height:140px}.send{width:44px;height:44px;border:0;border-radius:13px;background:linear-gradient(135deg,#4b6cff,#7c3aed);color:#fff;font-size:19px}.send:disabled{opacity:.5}.tools{display:flex;gap:7px;overflow:auto;padding:8px 3px 0}.tool{white-space:nowrap;border:1px solid var(--border);background:var(--panel2);color:var(--muted);border-radius:10px;padding:7px 10px;font-size:12px}.file-input{display:none}.install-banner{position:fixed;bottom:112px;right:18px;z-index:15;background:var(--panel);border:1px solid var(--border);padding:12px;border-radius:14px;box-shadow:0 15px 40px #0008;display:none}.install-banner button{border:0;border-radius:9px;padding:7px 10px;background:var(--accent);color:#fff}.toast{position:fixed;left:50%;bottom:100px;transform:translateX(-50%);background:#111a2b;color:#fff;border:1px solid var(--border);padding:9px 13px;border-radius:10px;display:none;z-index:50}.error{color:#ff9a9a}@media(max-width:800px){.sidebar{position:fixed;inset:0 auto 0 0;transform:translateX(-102%);transition:.2s;z-index:30;box-shadow:15px 0 45px #0009}.sidebar.open{transform:translateX(0)}.mobile-menu{display:block}.composer{left:50%;width:100%;transform:translateX(-50%)}.messages{padding-bottom:185px}.bubble{max-width:92%}.top{padding:0 12px}.model-btn{min-width:145px}.chat-list{max-height:30vh}}
</style></head><body><div class="app">
<aside class="sidebar" id="sidebar"><div class="brand"><div class="logo">✦</div><div><b>Phul</b><small>Think Deeper, Create More</small></div></div><button class="new" id="newChat">＋ New Chat</button><div class="nav"><button id="searchChats">⌕ &nbsp; Search chats</button><button>▣ &nbsp; My Library</button><button>◈ &nbsp; Explore AI</button><button>▦ &nbsp; Tools</button></div><div class="recent-title">Chats</div><input class="search-model hide" id="chatSearch" placeholder="Search chats..."><div class="chat-list" id="chatList"></div><div class="bottom"><button id="themeBtn">☾ &nbsp; Dark / Light</button><button id="installBtn">⇩ &nbsp; Install PWA</button><button>⚙ &nbsp; Settings</button><button>?</button></div><div class="profile"><div class="avatar">A</div><div><b>Phul User</b><br><small>Free Plan</small></div></div></aside>
<main class="main"><header class="top"><div class="top-left"><button class="mobile-menu" id="menu">☰</button><div><div class="title">Phul <span class="online">● Online</span></div><small style="color:var(--muted)">Multi-Model AI Assistant</small></div></div><div class="model-wrap"><button class="model-btn" id="modelBtn">Kimi-K3 <span>⌄</span></button><div class="dropdown" id="dropdown"><div class="drop-head"><span>AI Models</span><span id="modelCount">Loading...</span></div><input class="search-model" id="modelSearch" placeholder="Search models..."><div id="modelList"></div></div></div></header>
<section class="messages" id="messages"><div class="welcome" id="welcome"><div class="biglogo">✦</div><h1>How can Phul help?</h1><p>Choose a model, upload a file or image, and start chatting.</p></div></section>
<div class="composer"><div id="attachmentPreview"></div><div class="compose-box"><button class="attach" id="attachBtn">＋</button><textarea id="input" rows="1" placeholder="Message Phul..."></textarea><button class="send" id="send">➤</button></div><div class="tools"><button class="tool" id="imageBtn">🖼 Image</button><button class="tool" id="fileBtn">📎 File</button><button class="tool" id="deepBtn">💡 Deep Think</button><button class="tool" id="regenBtn">🔄 Regenerate</button><button class="tool" id="clearBtn">🧹 Clear</button></div><input class="file-input" id="imageInput" type="file" accept="image/*"><input class="file-input" id="fileInput" type="file" accept=".txt,.md,.json,.csv,.js,.ts,.py,.html,.css,.xml,.yaml,.yml,.log,.java,.c,.cpp,.h,.sql,image/*"><div style="text-align:center;color:var(--muted);font-size:10px;margin-top:6px">Phul can make mistakes. Please verify important information.</div></div>
</main></div><div class="install-banner" id="installBanner">Install Phul on Android? <button id="installNow">Install</button></div><div class="toast" id="toast"></div>
<script>
const DEFAULT='moonshotai/Kimi-K3:together';let selectedModel=localStorage.getItem('phul_model')||DEFAULT,models=[],currentId=localStorage.getItem('phul_current')||crypto.randomUUID(),deepThink=false,pendingImage=null,pendingFile=null,lastPrompt='';
const $=id=>document.getElementById(id),messages=$('messages'),input=$('input');
function esc(s){return String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function name(m){return m?.name||m?.id?.split(':')[0].split('/').pop().replaceAll('-',' ')||'Kimi-K3'}
function markdown(s){let safe=esc(s);const blocks=[];safe=safe.replace(/```([\w+-]*)\n?([\s\S]*?)```/g,(_,lang,code)=>{const i=blocks.length;blocks.push(`<div class="codewrap"><div class="codehead"><span>${esc(lang||'code')}</span><button class="action copycode" data-code="${encodeURIComponent(code)}">📋 Copy</button></div><pre><code>${code}</code></pre></div>`);return `@@CODE${i}@@`});safe=safe.replace(/`([^`]+)`/g,'<span class="inline-code">$1</span>');safe=safe.replace(/^### (.*)$/gm,'<h3>$1</h3>').replace(/^## (.*)$/gm,'<h2>$1</h2>').replace(/^# (.*)$/gm,'<h1>$1</h1>');safe=safe.replace(/^[-*] (.*)$/gm,'<li>$1</li>').replace(/(<li>.*<\/li>)/gs,'<ul>$1</ul>');safe=safe.replace(/^\d+\. (.*)$/gm,'<li>$1</li>');safe=safe.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\*(.*?)\*/g,'<em>$1</em>');safe=safe.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');safe=safe.split(/\n\n+/).map(p=>p.match(/^<h[1-3]|^<ul>|^@@CODE/) ? p : `<p>${p.replace(/\n/g,'<br>')}</p>`).join('');blocks.forEach((b,i)=>safe=safe.replace(`@@CODE${i}@@`,b));return safe}
function toast(t){const x=$('toast');x.textContent=t;x.style.display='block';clearTimeout(window._toast);window._toast=setTimeout(()=>x.style.display='none',1800)}
function chats(){return JSON.parse(localStorage.getItem('phul_chats')||'[]')}
function saveChats(c){localStorage.setItem('phul_chats',JSON.stringify(c.slice(-50)))}
function current(){return chats().find(c=>c.id===currentId)}
function ensure(){let c=current();if(!c){c={id:currentId,title:'New chat',messages:[],updated:Date.now()};const a=chats();a.push(c);saveChats(a)}return c}
function renderChatList(filter=''){const list=$('chatList');list.innerHTML='';chats().sort((a,b)=>b.updated-a.updated).filter(c=>c.title.toLowerCase().includes(filter.toLowerCase())).forEach(c=>{const d=document.createElement('div');d.className='chat-item '+(c.id===currentId?'active':'');d.textContent=c.title;d.onclick=()=>{currentId=c.id;localStorage.setItem('phul_current',currentId);renderConversation();renderChatList($('chatSearch').value);$('sidebar').classList.remove('open')};list.append(d)})}
function renderConversation(){messages.innerHTML='';const c=current();if(!c||!c.messages.length){messages.innerHTML='<div class="welcome"><div class="biglogo">✦</div><h1>How can Phul help?</h1><p>Choose a model, upload a file or image, and start chatting.</p></div>';return}c.messages.forEach(m=>addMessage(m.role,m.content,false,m.model));window.scrollTo(0,document.body.scrollHeight)}
function addMessage(role,text,save=true,model){$('welcome')?.remove();const wrap=document.createElement('div');wrap.className='msg '+role;const bubble=document.createElement('div');bubble.className='bubble';const label=document.createElement('div');label.className='mlabel';label.textContent=role==='user'?'You':(model||name(models.find(m=>m.id===selectedModel)));bubble.append(label);const body=document.createElement('div');body.className='markdown';body.innerHTML=role==='assistant'?markdown(text):esc(text).replace(/\n/g,'<br>');bubble.append(body);if(role==='assistant'){const acts=document.createElement('div');acts.className='actions';acts.innerHTML='<button class="action copymsg">📋 Copy</button><button class="action regenmsg">🔄 Regenerate</button>';acts.querySelector('.copymsg').onclick=()=>{navigator.clipboard.writeText(text);toast('Copied')};acts.querySelector('.regenmsg').onclick=()=>regenerate(text);bubble.append(acts)}wrap.append(bubble);messages.append(wrap);if(save){const c=ensure();c.messages.push({role,content:text,model});c.updated=Date.now();if(role==='user'&&c.title==='New chat')c.title=text.slice(0,45);saveChats(chats());renderChatList()}return body}
async function loadModels(){try{const r=await fetch('/api/models');const d=await r.json();models=d.models||[];if(!models.some(m=>m.id===selectedModel))selectedModel=models[0]?.id||DEFAULT}catch(e){models=[{id:DEFAULT,name:'Kimi-K3',provider:'together',description:'Advanced reasoning & multimodal',vision:true}]}localStorage.setItem('phul_model',selectedModel);setModelButton();renderModels()}
function setModelButton(){const m=models.find(x=>x.id===selectedModel);$('modelBtn').firstChild.textContent=name(m)+' '}
function renderModels(){const q=$('modelSearch').value.toLowerCase();const list=$('modelList');list.innerHTML='';const filtered=models.filter(m=>name(m).toLowerCase().includes(q)||m.id.toLowerCase().includes(q));$('modelCount').textContent=models.length+' models';filtered.forEach(m=>{const d=document.createElement('div');d.className='model-option '+(m.id===selectedModel?'active':'');d.innerHTML=`<div class="mi">${m.vision?'◈':'✦'}</div><div><div class="mn">${esc(name(m))}</div><div class="md">${esc(m.description||'Chat model')} · ${esc(m.provider||'auto')}</div></div>${m.id===selectedModel?'<div class="check">✓</div>':''}`;d.onclick=()=>{selectedModel=m.id;localStorage.setItem('phul_model',selectedModel);setModelButton();renderModels();$('dropdown').classList.remove('open');};list.append(d)})}
async function readFile(file){return new Promise((res,rej)=>{const fr=new FileReader();fr.onload=()=>res(fr.result);fr.onerror=rej;fr.readAsDataURL(file)})}
async function attachImage(file){pendingImage=await readFile(file);$('attachmentPreview').innerHTML=`<div class="attachment"><img src="${pendingImage}"><div><b>${esc(file.name)}</b><br><small>${Math.round(file.size/1024)} KB · Image</small></div><button class="action remove" onclick="pendingImage=null;$('attachmentPreview').innerHTML=''">✕</button></div>`}
async function attachFile(file){if(file.type.startsWith('image/'))return attachImage(file);if(file.size>1500000){toast('File is too large');return}const text=await file.text();pendingFile=text;$('attachmentPreview').innerHTML=`<div class="attachment"><div>📎</div><div><b>${esc(file.name)}</b><br><small>${Math.round(file.size/1024)} KB · Text file</small></div><button class="action remove" onclick="pendingFile=null;$('attachmentPreview').innerHTML=''">✕</button></div>`}
function thinking(body){body.innerHTML='<span class="thinking"><i></i><i></i><i></i> Thinking...</span>'}
async function go(prompt=input.value.trim(),regenerate=false){if(!prompt&&!pendingImage&&!pendingFile)return;lastPrompt=prompt||lastPrompt;if(!regenerate)addMessage('user',prompt+(pendingFile?'\n[File attached]':pendingImage?'\n[Image attached]':''));input.value='';const body=addMessage('assistant','',false, name(models.find(m=>m.id===selectedModel)));thinking(body);let c=ensure();const prior=c.messages.slice(-20);try{const payload={message:prompt||'Analyze the attached content.',model:selectedModel,image_data:pendingImage,file_text:pendingFile,deep_think:deepThink,history:prior};const r=await fetch('/api/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!r.ok)throw new Error('Request failed');const reader=r.body.getReader(),dec=new TextDecoder();let full='';while(true){const {value,done}=await reader.read();if(done)break;const chunk=dec.decode(value,{stream:true});for(const line of chunk.split('\n\n')){if(!line.startsWith('data: '))continue;const ev=JSON.parse(line.slice(6));if(ev.type==='delta'){full+=ev.text;body.innerHTML=markdown(full);window.scrollTo(0,document.body.scrollHeight)}if(ev.type==='error')throw new Error(ev.message)}}if(!full)full='(empty response)';body.innerHTML=markdown(full);c.messages.push({role:'assistant',content:full,model:selectedModel});c.updated=Date.now();saveChats(chats());renderChatList()}catch(e){body.innerHTML='<span class="error">Error: '+esc(e.message)+'</span>'}finally{pendingImage=null;pendingFile=null;$('attachmentPreview').innerHTML=''}}
function regenerate(){const c=current();if(!c)return;const last=c.messages.filter(m=>m.role==='user').pop();if(!last)return;c.messages=c.messages.filter((m,i)=>i<c.messages.length-1);saveChats(chats());renderConversation();go(last.content,true)}
$('send').onclick=()=>go();input.onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();go()}};$('modelBtn').onclick=()=>{$('dropdown').classList.toggle('open')};$('modelSearch').oninput=renderModels;document.addEventListener('click',e=>{if(!e.target.closest('.model-wrap'))$('dropdown').classList.remove('open')});document.addEventListener('click',e=>{const b=e.target.closest('.copycode');if(b){navigator.clipboard.writeText(decodeURIComponent(b.dataset.code||''));toast('Code copied')}});$('menu').onclick=()=>$('sidebar').classList.toggle('open');$('newChat').onclick=()=>{currentId=crypto.randomUUID();localStorage.setItem('phul_current',currentId);ensure();renderConversation();renderChatList();};$('imageBtn').onclick=()=>$('imageInput').click();$('fileBtn').onclick=()=>$('fileInput').click();$('attachBtn').onclick=()=>$('fileInput').click();$('imageInput').onchange=e=>e.target.files[0]&&attachImage(e.target.files[0]);$('fileInput').onchange=e=>e.target.files[0]&&attachFile(e.target.files[0]);$('deepBtn').onclick=()=>{deepThink=!deepThink;$('deepBtn').textContent=deepThink?'🧠 Deep Think: ON':'💡 Deep Think';toast(deepThink?'Deep Think enabled':'Deep Think disabled')};$('regenBtn').onclick=regenerate;$('clearBtn').onclick=()=>{const c=current();if(c){c.messages=[];c.updated=Date.now();saveChats(chats());renderConversation();renderChatList()}};$('searchChats').onclick=()=>{$('chatSearch').classList.toggle('hide');$('chatSearch').focus()};$('chatSearch').oninput=e=>renderChatList(e.target.value);$('themeBtn').onclick=()=>{document.body.classList.toggle('light');localStorage.setItem('phul_theme',document.body.classList.contains('light')?'light':'dark')};if(localStorage.getItem('phul_theme')==='light')document.body.classList.add('light');
let deferredPrompt=null;window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();deferredPrompt=e;$('installBanner').style.display='block'});$('installBtn').onclick=async()=>{if(deferredPrompt){deferredPrompt.prompt();deferredPrompt=null;$('installBanner').style.display='none'}else toast('Use browser menu → Add to Home screen')};$('installNow').onclick=()=>$('installBtn').click();
ensure();renderChatList();renderConversation();loadModels();if('serviceWorker'in navigator)navigator.serviceWorker.register('/service-worker.js');
</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(HTML)
