import httpx
from openai import OpenAI
from backend.core.config import HF_BASE,HF_TOKEN
def client(): return OpenAI(base_url=HF_BASE,api_key=HF_TOKEN)
async def list_models():
    async with httpx.AsyncClient(timeout=20) as h:
        r=await h.get(HF_BASE+"/models",headers={"Authorization":"Bearer "+HF_TOKEN});r.raise_for_status();return r.json()