from flask import Flask, request, jsonify
import logging
import os
import requests
from preprocess import preprocess_query

# Initialize Flask app
app = Flask(__name__)

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Function to query different AI models
def query_model(model_name, prompt):
    """
    Generic function to query any supported AI model
    
    Args:
        model_name (str): Identifier for the model to use ("gpt-4o", "claude-3", etc.)
        prompt (str): The preprocessed query to send
        
    Returns:
        dict: Standardized response with keys:
            - success: Boolean indicating if the request succeeded
            - content: The model's response text
            - model: Name of the model that provided the response
            - error: Error message (if success is False)
    """
    try:
        if model_name == "gpt-4o":
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}]}
            endpoint = "https://api.openai.com/v1/chat/completions"

            response = requests.post(endpoint, json=payload, headers=headers)
            response_json = response.json()

            return {
                "success": True,
                "content": response_json["choices"][0]["message"]["content"],
                "model": "gpt-4o",
                "error": None
            }
        
        elif model_name == "claude-3":
            headers = {"x-api-key": CLAUDE_API_KEY, "Content-Type": "application/json"}
            payload = {
                "model": "claude-3-opus-20240229",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }
            endpoint = "https://api.anthropic.com/v1/messages"

            response = requests.post(endpoint, json=payload, headers=headers)
            response_json = response.json()

            logging.debug(f"Claude API raw response: {response_json}")  # **Log full response**

            return {
                "success": True if "content" in response_json else False,
                "content": response_json.get("content", "Missing 'content' field"),
                "model": "claude-3",
                "error": None if "content" in response_json else "'content' key missing"
            }

        else:
            return {
                "success": False,
                "content": None,
                "model": model_name,
                "error": f"Unsupported model: {model_name}"
            }
    
    except Exception as e:
        logging.error(f"Error querying {model_name}: {e}")
        return {
            "success": False,
            "content": None,
            "model": model_name,
            "error": str(e)
        }

@app.route('/ask', methods=['POST'])
def ask():
    try:
        # Force Flask to parse JSON correctly
        data = request.get_json(force=True)

        logging.debug(f"Received request data: {data}")

        if not data or "query" not in data:
            return jsonify({"error": "No query provided"}), 400  # Return 400 if query is missing
        
        raw_query = data["query"].strip()

        # Preprocess the query before sending to LLMs
        structured_query = preprocess_query(raw_query)

        # Get responses from both models
        openai_response = query_model("gpt-4o", structured_query)
        claude_response = query_model("claude-3", structured_query)

        return jsonify({
            "query": raw_query,
            "structured_query": structured_query,
            "responses": {
                "gpt-4o": openai_response,
                "claude-3": claude_response
            }
        })
    except Exception as e:
        logging.error(f"Error in /ask route: {e}")
        return jsonify({"error": str(e)}), 500

# Root route to prevent 404 errors
@app.route('/')
def home():
    return "Bullshit Detector is running!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
