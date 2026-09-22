from fastapi import APIRouter
router=APIRouter()
@router.get("/history/info")
def history_info():return {"mode":"local-browser","cloud_sync":False}