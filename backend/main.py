from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse,Response
from backend.core.config import APP_NAME
from backend.api.chat import router as chat_router
from backend.api.models import router as models_router
from backend.api.upload import router as upload_router
from backend.api.history import router as history_router
ROOT=Path(__file__).resolve().parents[1]
app=FastAPI(title="Phul Multi-Model AI",version="4.0")
app.include_router(chat_router,prefix="/api");app.include_router(models_router,prefix="/api");app.include_router(upload_router,prefix="/api");app.include_router(history_router,prefix="/api")
@app.get("/health")
def health():return {"ok":True,"app":APP_NAME,"version":"4.0"}
@app.get("/manifest.json")
def manifest():return FileResponse(ROOT/"frontend"/"manifest.json",media_type="application/manifest+json")
@app.get("/service-worker.js")
def sw():return FileResponse(ROOT/"frontend"/"service-worker.js",media_type="application/javascript")
@app.get("/{path:path}")
def frontend(path:str=""):
 if path.startswith("api/"):return Response(status_code=404)
 target=ROOT/"frontend"/(path or "index.html")
 return FileResponse(target if target.is_file() else ROOT/"frontend"/"index.html")