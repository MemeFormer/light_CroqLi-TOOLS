# src/assistant/search.py

from src.services.groq_api import GroqService

def search_groq(query, config):
    """Searches Groq API with the given query."""
    groq_service = GroqService()
    body = {
        "query": query,
        "model": config.groq_model,
        "max_tokens": config.max_tokens
    }

    response = groq_service.post("/search", json=body)
    response.raise_for_status()
    return response.json()

def search_mode(config, console):
    """Initiates the search mode."""
    groq_service = GroqService()

    while True:
        query = console.input("Enter search query: ")

        if query.lower() in ['/quit', '/back']:
            break

        try:
            results = search_groq(query, config)
            console.print(f"Search Results: {results}")
        except Exception as e:
            console.print(f"An error occurred: {str(e)}", style="bold red")

    console.print("Exiting search mode.")