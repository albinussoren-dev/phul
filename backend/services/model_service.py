from backend.core.config import HF_TOKEN
from backend.providers.huggingface import list_models
from backend.providers.registry import FALLBACK,normalize
async def models():
 if not HF_TOKEN:return FALLBACK
 try:
  found=normalize(await list_models());ids={x["id"] for x in found};return [x for x in FALLBACK if x["id"] not in ids]+found[:100]
 except:return FALLBACK