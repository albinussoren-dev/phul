import os
from dotenv import load_dotenv
load_dotenv()
APP_NAME="Phul"
HF_TOKEN=os.getenv("HF_TOKEN","")
HF_BASE="https://router.huggingface.co/v1"
DEFAULT_MODEL="moonshotai/Kimi-K3:together"