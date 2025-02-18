import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
