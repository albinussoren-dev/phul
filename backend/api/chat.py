import json
from fastapi import APIRouter,HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field
from backend.core.config import HF_TOKEN,DEFAULT_MODEL
from backend.services.chat_service import complete,stream
router=APIRouter()
class ChatRequest(BaseModel):
 message:str=""
 model:str=DEFAULT_MODEL
 image_data:str|None=None
 file_text:str|None=None
 deep_think:bool=False
 history:list[dict]=Field(default_factory=list)
@router.post("/chat")
def chat_api(req:ChatRequest):
 if not HF_TOKEN:raise HTTPException(500,"HF_TOKEN is not configured.")
 try:
  r=complete(req);return {"reply":r.choices[0].message.content or "","model":req.model}
 except Exception as e:raise HTTPException(502,str(e))
@router.post("/chat/stream")
def stream_api(req:ChatRequest):
 if not HF_TOKEN:raise HTTPException(500,"HF_TOKEN is not configured.")
 def gen():
  try:
   for chunk in stream(req):
    if not chunk.choices:continue
    t=chunk.choices[0].delta.content
    if t:yield "data: "+json.dumps({"type":"delta","text":t},ensure_ascii=False)+"\n\n"
   yield "data: "+json.dumps({"type":"done","model":req.model})+"\n\n"
  except Exception as e:yield "data: "+json.dumps({"type":"error","message":str(e)})+"\n\n"
 return StreamingResponse(gen(),media_type="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})