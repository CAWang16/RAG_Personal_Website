from dotenv import load_dotenv
import os
from google import genai

load_dotenv()

print("API KEY:", os.getenv("GEMINI_API_KEY"))

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

response = client.models.embed_content(
    model="models/gemini-embedding-001",
    contents="hello world"
)

print(len(response.embeddings[0].values))