import json
from pathlib import Path
from backend.core.config import DEFAULT_MODEL
FALLBACK=[{"id":DEFAULT_MODEL,"name":"Kimi-K3","provider":"together","description":"Advanced reasoning & multimodal","vision":True,"streaming":True}]
def local_models():
 p=Path(__file__).resolve().parents[2]/"models"/"models.json"
 try:return json.loads(p.read_text())["models"]
 except:return FALLBACK
def normalize(raw):
 out=[];seen=set()
 for item in raw.get("data",[]) if isinstance(raw,dict) else []:
  mid=item.get("id")
  if not isinstance(mid,str) or not mid:continue
  providers=item.get("providers") or []
  together=any(isinstance(p,dict) and p.get("provider")=="together" for p in providers)
  eid=mid+":together" if together else mid+":fastest"
  if eid in seen:continue
  seen.add(eid);mods=(item.get("architecture") or {}).get("input_modalities") or []
  out.append({"id":eid,"name":mid.split("/")[-1].replace("-"," "),"provider":"together" if together else "auto","description":"Multimodal" if "image" in mods else "Chat model","vision":"image" in mods,"streaming":True})
 return out