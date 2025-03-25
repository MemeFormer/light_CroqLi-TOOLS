# src/assistant/search.py
from src.services.groq_api import GroqService
from src.models.models import ChatMessage, ToolCall
from typing import List

def search_groq(groq_service: GroqService, query: str, config) -> str:
    """Searches using Tavily API and summarizes results with Groq."""
    # Define the tool schema
    tool_schema = [{
        "type": "function",
        "function": {
            "name": "search_tavily",
            "description": "Searches the web using Tavily API and returns formatted results",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    }]

    try:
        # First, execute the search directly
        print("Executing Tavily search...")
        search_results = groq_service.tools["search_tavily"](query)
        
        if "error" in search_results:
            return f"Search failed: {search_results['error']}"
            
        # Now ask Groq to summarize the results
        messages = [
            ChatMessage(role="system", content="You are a search assistant. Please provide a clear and concise summary of the search results, highlighting the most important information."),
            ChatMessage(role="user", content=f"Here are the search results for the query '{query}':\n\n{search_results}\n\nPlease summarize these results, focusing on directly answering the query.")
        ]
        
        summary_response = groq_service.generate_response(messages)
        if summary_response and summary_response.input:
            return summary_response.input
        return search_results  # Return raw results if summarization fails
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return f"Search failed: {str(e)}"

def search_mode(config, console, groq_service: GroqService):
    """Initiates the search mode."""
    console.print("\nSearch Mode - Enter your query or '/back' to return to menu", style="bold blue")
    console.print("This mode uses Tavily for web search and Groq for summarization.", style="bold green")
    
    while True:
        query = console.input("\nSearch query: ")

        if query.lower() in ['/quit', '/back']:
            break

        if query.strip() == '':
            continue

        try:
            console.print("\nSearching...", style="bold yellow")
            results = search_groq(groq_service, query, config)
            console.print("\nResults:", style="bold green")
            console.print(results)
        except Exception as e:
            console.print(f"An error occurred: {str(e)}", style="bold red")

    console.print("Exiting search mode.", style="bold blue")