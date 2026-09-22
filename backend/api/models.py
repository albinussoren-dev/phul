from fastapi import APIRouter
from backend.services.model_service import models
router=APIRouter()
@router.get("/models")
async def get_models():return {"models":await models()}