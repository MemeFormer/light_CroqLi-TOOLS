# src/main.py
import os
import json
from dotenv import load_dotenv
from src.assistant.utils.menu_helpers import MenuSystem
from src.services.groq_api import GroqService
from src.config import load_config, Config
from src.tools.tools import Tools # Import the Tools class



def register_tools(groq_service, tools: Tools): # Add tools parameter
    groq_service.register_tool("search_history", tools.search_history)
    groq_service.register_tool("execute_command", tools.execute_command)
    groq_service.register_tool("provide_helpful_tips", tools.provide_helpful_tips)
    groq_service.register_tool("get_api_keys", tools.get_api_keys)
    groq_service.register_tool("update_api_keys", tools.update_api_keys)
    groq_service.register_tool("search_tavily", tools.search_tavily) # Register search_tavily
def main():
    load_dotenv()
    dotenv_path = os.path.abspath(".env") # Absolute path
    load_dotenv(dotenv_path=dotenv_path)

    
    config = load_config()
    config.load_systemprompts_U() 
    try:
        groq_service = GroqService()
        tools = Tools(groq_service) # Instantiate Tools
        register_tools(groq_service, tools) # Pass tools to register_tools
    except Exception as e:
        print(f"Error initializing services: {e}")
        return

    menu_system = MenuSystem(config, groq_service, tools) # Instantiate MenuSystem
    menu_system.run() # Run the menu system



if __name__ == "__main__":
    main()