# src/assistant/search.py
from src.services.groq_api import GroqService

def search_groq(groq_service: GroqService, query, config): # Accept groq_service
    """Searches Groq API with the given query."""
    body = {
        "query": query,
        "model": config.groq_model,
        "max_tokens": config.max_tokens
    }

    # Assuming GroqService has a post method. If not, adjust accordingly.
    response = groq_service.client.post("/search", json=body) # Use groq_service.client
    response.raise_for_status()
    return response.json()


def search_mode(config, console, groq_service: GroqService): # Accept groq_service
    """Initiates the search mode."""
    while True:
        query = console.input("Enter search query: ")

        if query.lower() in ['/quit', '/back']:
            break

        try:
            results = search_groq(groq_service, query, config) # Pass groq_service
            console.print(f"Search Results: {results}")
        except Exception as e:
            console.print(f"An error occurred: {str(e)}", style="bold red")

    console.print("Exiting search mode.")