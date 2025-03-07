import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/ask', methods=['POST'])
def ask():
    query = request.json.get('query')

    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }

    openai_response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": query}]
        }
    ).json()

    return jsonify({
        "query": query,
        "openai_response": openai_response
    })

if __name__ == '__main__':
    app.run(debug=True)
