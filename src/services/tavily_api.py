# src/services/tavily_api.py

import requests
from dotenv import load_dotenv
import os

class TavilyService:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("TAVILY_API_KEY")
        self.base_url = os.getenv("TAVILY_API_URL", "https://api.tavily.com")

    def post(self, endpoint, json):
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json=json)
        return response