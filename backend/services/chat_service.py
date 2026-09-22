from backend.core.config import DEFAULT_MODEL
from backend.providers.together import chat
def messages(req):
 m=[{"role":"system","content":"You are Phul, a helpful multi-model AI assistant. Be clear and accurate."}]
 if req.deep_think:m[0]["content"]+=" Reason carefully and give useful reasoning summaries without revealing private chain-of-thought."
 for h in req.history[-20:]:
  if h.get("role") in ("user","assistant") and isinstance(h.get("content"),str):m.append({"role":h["role"],"content":h["content"][:12000]})
 content=req.message or "Analyze the attached content."
 if req.file_text:content+="\n\n[Attached file]\n"+req.file_text[:50000]
 if req.image_data:content=[{"type":"text","text":content},{"type":"image_url","image_url":{"url":req.image_data}}]
 m.append({"role":"user","content":content});return m
def complete(req):return chat(model=req.model or DEFAULT_MODEL,messages=messages(req))
def stream(req):return chat(model=req.model or DEFAULT_MODEL,messages=messages(req),stream=True)