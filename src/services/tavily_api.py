# src/services/tavily_api.py

import requests
from dotenv import load_dotenv
import os
import json

class TavilyService:
    def __init__(self):
        load_dotenv()  # Load environment variables
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set")
        self.base_url = "https://api.tavily.com"

    def post(self, endpoint: str, data: dict) -> dict:
        """Send a POST request to the Tavily API."""
        try:
            # Add API key to headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"  # Use Bearer token authentication
            }
            
            # Make the request
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"Tavily API request failed: {str(e)}"
            if hasattr(e.response, 'text'):
                try:
                    error_data = json.loads(e.response.text)
                    if 'message' in error_data:
                        error_msg = f"Tavily API error: {error_data['message']}"
                except json.JSONDecodeError:
                    pass
            raise ValueError(error_msg)