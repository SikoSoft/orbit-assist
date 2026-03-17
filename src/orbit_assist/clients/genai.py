from google import genai


def create_genai_client(api_key: str) -> genai.Client:
    print("Creating GenAI client with provided API key.")
    print("API Key:", api_key[:4] + "****" + api_key[-4:])  # Mask the API key for security
    return genai.Client(api_key=api_key)
