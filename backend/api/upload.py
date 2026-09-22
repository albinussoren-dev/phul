from fastapi import APIRouter
router=APIRouter()
@router.get("/upload/info")
def upload_info():return {"mode":"browser","max_text_bytes":1500000,"image":"data-url"}