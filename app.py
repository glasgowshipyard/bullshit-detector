import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

def query_openai(query):
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": query}]}
    )
    return response.json()

def query_claude(query):
    headers = {
        "x-api-key": os.getenv("CLAUDE_API_KEY"),
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json={"model": "claude-3-opus-20240229", "messages": [{"role": "user", "content": query}], "max_tokens": 200}
    )
    return response.json()

@app.route('/ask', methods=['POST'])
def ask():
    query = request.json.get('query')
    
    openai_response = query_openai(query)
    claude_response = query_claude(query)

    return jsonify({
        "query": query,
        "responses": {
            "gpt-4o": openai_response.get("choices", [{}])[0].get("message", {}).get("content", "No response"),
            "claude-3": claude_response.get("content", [{}])[0].get("text", "No response")
        }
    })

if __name__ == '__main__':
    app.run(debug=True)
