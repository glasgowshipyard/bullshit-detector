from flask import Flask, request, jsonify
from preprocess import preprocess_query  # Import the preprocessing function
import requests
import os

# Initialize Flask app
app = Flask(__name__)

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Function to query OpenAI's GPT-4o

def query_openai(prompt):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}]}
    response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
    return response.json()

# Function to query Claude 3

def query_claude(prompt):
    headers = {"Authorization": f"Bearer {CLAUDE_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "claude-3-opus-20240229", "messages": [{"role": "user", "content": prompt}]}
    response = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
    return response.json()

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    raw_query = data.get("query", "").strip()
    
    # Preprocess the query before sending to LLMs
    structured_query = preprocess_query(raw_query)
    
    # Get responses from both models
    openai_response = query_openai(structured_query)
    claude_response = query_claude(structured_query)
    
    return jsonify({
        "query": raw_query,
        "structured_query": structured_query,
        "responses": {
            "gpt-4o": openai_response.get("choices", [{}])[0].get("message", {}).get("content", "Error fetching response"),
            "claude-3": claude_response.get("content", "Error fetching response")
        }
    })

if __name__ == '__main__':
    app.run(debug=True)
