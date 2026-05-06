from pydantic import BaseModel
import os
from dotenv import load_dotenv
load_dotenv()
class Config(BaseModel):
    XAI_API_KEY: str = os.getenv('XAI_API_KEY', '')
config = Config()