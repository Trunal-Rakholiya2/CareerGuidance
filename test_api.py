import os
from google import genai
from dotenv import load_dotenv

# Load the .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found.")
    exit()

client = genai.Client(api_key=api_key)

# We use the model name we found in your list
model_name = "gemini-2.5-flash"

print(f"Testing model: {model_name}...")

try:
    response = client.models.generate_content(
        model=model_name,
        contents="Hello! Are you working?"
    )
    print(f"\n✅ SUCCESS! Response from AI:\n{response.text}")

except Exception as e:
    print(f"❌ Error: {e}")