import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Bullshit Detector API is live."

@app.route('/ask', methods=['POST'])
def ask():
    query = request.json.get('query')

    # Sandbox API for testing
    sandbox_url = "https://jsonplaceholder.typicode.com/todos/1"
    response = requests.get(sandbox_url).json()

    return jsonify({"query": query, "sandbox_response": response})

if __name__ == '__main__':
    app.run(debug=True)
