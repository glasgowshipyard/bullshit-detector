from flask import Flask, request, jsonify, render_template
import logging
import os
import requests
import json
from preprocess import preprocess_query

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
# DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # Uncomment when you have the API key

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
            try:
                headers = {
                    "x-api-key": CLAUDE_API_KEY, 
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                }
                payload = {
                    "model": "claude-3-opus-20240229",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                }
                endpoint = "https://api.anthropic.com/v1/messages"
                
                # Log what we're sending
                logging.debug(f"Sending to Claude API: endpoint={endpoint}")
                
                response = requests.post(endpoint, json=payload, headers=headers)

                # Log response metadata
                logging.debug(f"Claude API status code: {response.status_code}")
                
                try:
                    response_json = response.json()
                    
                    # Check for alternative response structures
                    if "content" in response_json and isinstance(response_json["content"], list):
                        content = response_json["content"][0]["text"]
                        return {"success": True, "content": content, "model": "claude-3", "error": None}
                    elif "message" in response_json:
                        return {"success": True, "content": str(response_json["message"]), "model": "claude-3", "error": None}
                    else:
                        return {
                            "success": False,
                            "content": str(response_json)[:200] + "...",
                            "model": "claude-3",
                            "error": "Could not locate content in response"
                        }
                except ValueError as e:
                    logging.error(f"Claude API returned non-JSON response: {response.text[:200]}...")
                    return {"success": False, "content": None, "model": "claude-3", "error": f"Non-JSON response: {str(e)}"}
            except Exception as e:
                logging.error(f"Error in Claude API request: {str(e)}")
                return {"success": False, "content": None, "model": "claude-3", "error": str(e)}

        elif model_name == "mistral":
            try:
                headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": "mistral-large-latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,  # Lower temp for more factual responses
                    "max_tokens": 800
                }
                endpoint = "https://api.mistral.ai/v1/chat/completions"
                
                logging.debug(f"Sending to Mistral API: endpoint={endpoint}")
                
                response = requests.post(endpoint, json=payload, headers=headers)
                logging.debug(f"Mistral API status code: {response.status_code}")
                
                response_json = response.json()
                
                return {
                    "success": True,
                    "content": response_json["choices"][0]["message"]["content"],
                    "model": "mistral",
                    "error": None
                }
            except Exception as e:
                logging.error(f"Error in Mistral API request: {str(e)}")
                return {"success": False, "content": None, "model": "mistral", "error": str(e)}
        
        # elif model_name == "deepseek":
        #     try:
        #         headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        #         payload = {
        #             "model": "deepseek-chat",
        #             "messages": [{"role": "user", "content": prompt}],
        #             "temperature": 0.1
        #         }
        #         endpoint = "https://api.deepseek.com/v1/chat/completions"
        #         
        #         logging.debug(f"Sending to DeepSeek API: endpoint={endpoint}")
        #         
        #         response = requests.post(endpoint, json=payload, headers=headers)
        #         logging.debug(f"DeepSeek API status code: {response.status_code}")
        #         
        #         response_json = response.json()
        #         
        #         return {
        #             "success": True,
        #             "content": response_json["choices"][0]["message"]["content"],
        #             "model": "deepseek",
        #             "error": None
        #         }
        #     except Exception as e:
        #         logging.error(f"Error in DeepSeek API request: {str(e)}")
        #         return {"success": False, "content": None, "model": "deepseek", "error": str(e)}

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

# Function to analyze model responses and calculate confidence
def analyze_responses(responses):
    """
    Analyze responses from multiple models to determine verdict and confidence
    
    Args:
        responses (dict): Dictionary of model responses
        
    Returns:
        dict: Analysis results with verdict and confidence
    """
    # Extract TRUE/FALSE judgments from each model
    judgments = {}
    for model, response in responses.items():
        if response["success"] and response["content"]:
            content = response["content"].upper()
            if "FALSE" in content and not ("NOT FALSE" in content or "ISN'T FALSE" in content):
                judgments[model] = "FALSE"
            elif "TRUE" in content and not ("NOT TRUE" in content or "ISN'T TRUE" in content):
                judgments[model] = "TRUE"
            else:
                judgments[model] = "UNCERTAIN"
    
    # Count different judgments
    judgment_counts = {"TRUE": 0, "FALSE": 0, "UNCERTAIN": 0}
    for judgment in judgments.values():
        judgment_counts[judgment] += 1
    
    # Determine the majority verdict
    majority_verdict = max(judgment_counts, key=judgment_counts.get)
    
    # If there's a tie between TRUE and FALSE, use UNCERTAIN
    if judgment_counts["TRUE"] == judgment_counts["FALSE"] and judgment_counts["TRUE"] > 0:
        majority_verdict = "UNCERTAIN"
    
    # Calculate confidence percentage
    total_models = sum(1 for response in responses.values() if response["success"])
    if total_models == 0:
        confidence = 0
    else:
        # Base confidence on agreement percentage
        agreement_count = judgment_counts[majority_verdict]
        confidence = (agreement_count / total_models) * 100
        
        # Adjust confidence based on UNCERTAIN judgments
        if majority_verdict == "UNCERTAIN":
            confidence = max(30, confidence)  # Cap minimum at 30%
        elif judgment_counts["UNCERTAIN"] > 0:
            confidence = max(50, confidence - (judgment_counts["UNCERTAIN"] * 10))
    
    # Determine confidence level text
    if confidence >= 90:
        confidence_level = "VERY HIGH"
    elif confidence >= 70:
        confidence_level = "HIGH"
    elif confidence >= 50:
        confidence_level = "MEDIUM"
    elif confidence >= 30:
        confidence_level = "LOW"
    else:
        confidence_level = "VERY LOW"
    
    return {
        "verdict": majority_verdict,
        "confidence_percentage": round(confidence),
        "confidence_level": confidence_level,
        "model_judgments": judgments
    }

@app.route('/ask', methods=['POST'])
def ask():
    try:
        # Try different methods to get the JSON data
        if request.is_json:
            data = request.get_json()
        else:
            # Force parsing as JSON even if Content-Type is incorrect
            data = request.get_json(force=True)
        
        logging.debug(f"Received request data: {data}")
        
        if not data or "query" not in data:
            return jsonify({"error": "No query provided"}), 400
        
        raw_query = data["query"].strip()

        # Preprocess the query before sending to LLMs
        structured_query = preprocess_query(raw_query)

        # Get responses from models
        responses = {}
        responses["gpt-4o"] = query_model("gpt-4o", structured_query)
        responses["claude-3"] = query_model("claude-3", structured_query)
        responses["mistral"] = query_model("mistral", structured_query)
        # responses["deepseek"] = query_model("deepseek", structured_query)  # Uncomment when DeepSeek API is available
        
        # Analyze responses to determine verdict and confidence
        analysis = analyze_responses(responses)

        return jsonify({
            "query": raw_query,
            "structured_query": structured_query,
            "responses": responses,
            "analysis": analysis
        })
    except Exception as e:
        logging.error(f"Error in /ask route: {e}")
        return jsonify({"error": str(e)}), 500

# Root route to render the main interface
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)