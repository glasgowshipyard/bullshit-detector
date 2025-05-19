from flask import Flask, request, jsonify, render_template, redirect
import logging
import os
import requests
import json
import re
from datetime import datetime
from flask_sslify import SSLify
from preprocess import preprocess_query

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Force SSL
sslify = SSLify(app, permanent=True)

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Function to strip markdown formatting
def strip_markdown(text):
    """Remove common markdown formatting from text"""
    if not text:
        return text
        
    # Remove bold/italic formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # Remove headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r'`(.*?)`', r'\1', text)
    return text

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
        
        elif model_name == "deepseek":
            try:
                headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                }
                endpoint = "https://api.deepseek.com/v1/chat/completions"
                
                logging.debug(f"Sending to DeepSeek API: endpoint={endpoint}")
                
                response = requests.post(endpoint, json=payload, headers=headers)
                logging.debug(f"DeepSeek API status code: {response.status_code}")
                
                response_json = response.json()
                
                # Get content and strip markdown formatting
                content = response_json["choices"][0]["message"]["content"]
                content = strip_markdown(content)  # Strip markdown for consistency with other models
                
                return {
                    "success": True,
                    "content": content,
                    "model": "deepseek",
                    "error": None
                }
            except Exception as e:
                logging.error(f"Error in DeepSeek API request: {str(e)}")
                return {"success": False, "content": None, "model": "deepseek", "error": str(e)}

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
    Analyze responses from multiple models to determine verdict and confidence,
    accounting for policy-based hesitations and uncertainty
    
    Args:
        responses (dict): Dictionary of model responses
        
    Returns:
        dict: Analysis results with verdict and confidence
    """
    # Extract TRUE/FALSE/UNCERTAIN judgments from each model
    judgments = {}
    policy_limited_responses = []
    uncertain_responses = []
    
    # Policy hesitation patterns that indicate reluctance but not factual uncertainty
    policy_patterns = [
        "I apologize", "I do not feel comfortable", "I would suggest referring to",
        "I cannot speculate", "not appropriate to discuss", "recommend consulting",
        "would advise looking at", "suggest referring to factual information",
        "it's important to rely on", "please consult official sources"
    ]
    
    # Uncertainty patterns that indicate factual uncertainty rather than policy limits
    uncertainty_patterns = [
        "cannot be definitively answered", "complex issue", "not enough evidence",
        "remains disputed", "difficult to determine", "would require more information",
        "cannot be answered with a simple", "insufficient evidence", "uncertain",
        "depends on", "ambiguous", "unclear", "debated", "controversial"
    ]
    
    for model, response in responses.items():
        if not (response["success"] and response["content"]):
            continue
            
        content = response["content"].upper()
        text = response["content"].lower()
        
        # Check for uncertainty indicators
        uncertain = any(pattern in text for pattern in uncertainty_patterns)
        
        # Check if response appears to be policy-limited rather than factually uncertain
        policy_limited = any(pattern in text for pattern in policy_patterns)
        
        # Extract explicit judgments
        if "FALSE" in content and not ("NOT FALSE" in content or "ISN'T FALSE" in content):
            if uncertain:
                judgments[model] = "UNCERTAIN"
                uncertain_responses.append(model)
            else:
                judgments[model] = "FALSE"
        elif "TRUE" in content and not ("NOT TRUE" in content or "ISN'T TRUE" in content):
            if uncertain:
                judgments[model] = "UNCERTAIN"
                uncertain_responses.append(model)
            else:
                judgments[model] = "TRUE"
        elif "UNCERTAIN" in content or uncertain:
            judgments[model] = "UNCERTAIN"
            uncertain_responses.append(model)
        elif policy_limited:
            # Look for implicit judgments in policy-limited responses
            if any(phrase in text for phrase in [
                "not supported by evidence", "debunked", "lack credible evidence",
                "conspiracy theory", "no credible evidence", "rejected by experts"
            ]):
                judgments[model] = "FALSE"
                policy_limited_responses.append(model)
            elif any(phrase in text for phrase in [
                "supported by evidence", "confirmed by", "verified by", "evidence shows",
                "research indicates", "studies confirm"
            ]):
                judgments[model] = "TRUE"
                policy_limited_responses.append(model)
            else:
                judgments[model] = "UNCERTAIN"
                policy_limited_responses.append(model)
        else:
            judgments[model] = "UNCERTAIN"
            uncertain_responses.append(model)
    
    # Count different judgments
    judgment_counts = {"TRUE": 0, "FALSE": 0, "UNCERTAIN": 0}
    for judgment in judgments.values():
        judgment_counts[judgment] += 1
    
    # Determine the majority verdict
    # If UNCERTAIN count is significant (1/3 or more), prioritize it
    total_models = len(judgments)
    if judgment_counts["UNCERTAIN"] >= (total_models / 3) or judgment_counts["UNCERTAIN"] >= 2:
        majority_verdict = "UNCERTAIN"
    else:
        # Otherwise use the most common verdict
        majority_verdict = max(
            ("TRUE", judgment_counts["TRUE"]), 
            ("FALSE", judgment_counts["FALSE"]),
            ("UNCERTAIN", judgment_counts["UNCERTAIN"]),
            key=lambda x: x[1]
        )[0]
    
    # If there's a tie between TRUE and FALSE, use UNCERTAIN
    if judgment_counts["TRUE"] == judgment_counts["FALSE"] and judgment_counts["TRUE"] > 0:
        majority_verdict = "UNCERTAIN"
    
    # Calculate confidence percentage
    if total_models == 0:
        confidence = 0
    else:
        # Calculate effective agreement (non-policy-limited models + agreeing policy-limited models)
        agreement_count = judgment_counts[majority_verdict]
        
        # If verdict is UNCERTAIN, confidence is based on uncertainty agreement
        if majority_verdict == "UNCERTAIN":
            # Cap confidence for UNCERTAIN verdicts
            confidence = min(70, (agreement_count / total_models) * 100)
        else:
            # For TRUE/FALSE verdicts
            policy_aligned = sum(1 for model in policy_limited_responses 
                               if model in judgments and judgments[model] == majority_verdict)
            
            # Calculate effective non-policy models
            non_policy_total = total_models - len(policy_limited_responses)
            
            if non_policy_total > 0:
                # Give more weight to direct, non-policy-limited responses
                base_confidence = ((agreement_count - policy_aligned) / non_policy_total) * 100
                
                # Add bonus for policy-limited responses that still align with majority
                policy_bonus = (policy_aligned / total_models) * 20  # 20% max bonus
                
                confidence = min(100, base_confidence + policy_bonus)
            else:
                # If all responses are policy-limited, just use agreement percentage
                confidence = (agreement_count / total_models) * 90  # Cap at 90% if all are policy-limited
            
            # Reduce confidence if there are uncertain responses
            if judgment_counts["UNCERTAIN"] > 0:
                uncertainty_penalty = (judgment_counts["UNCERTAIN"] / total_models) * 30
                confidence = max(40, confidence - uncertainty_penalty)
    
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
        "model_judgments": judgments,
        "policy_limited_responses": policy_limited_responses,
        "uncertain_responses": uncertain_responses
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
        responses["deepseek"] = query_model("deepseek", structured_query)
        
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

@app.route('/api/model-metadata', methods=['GET'])
def get_model_metadata():
    """Return model metadata for the frontend"""
    try:
        # Try to read from the scheduler's updated file
        metadata_file = "/tmp/model_metadata.json"
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                return jsonify(json.load(f))
        else:
            # Return default metadata if scheduler hasn't run yet
            default_metadata = {
                "last_updated": "2025-01-08",
                "models": {
                    "gpt-4o": {"name": "GPT-4o", "provider": "OpenAI", "training_cutoff": "April 2023"},
                    "claude-3": {"name": "Claude 3 Opus", "provider": "Anthropic", "training_cutoff": "August 2023"},
                    "mistral": {"name": "Mistral Large", "provider": "Mistral AI", "training_cutoff": "December 2023"},
                    "deepseek": {"name": "DeepSeek Chat", "provider": "DeepSeek AI", "training_cutoff": "January 2023"}
                }
            }
            return jsonify(default_metadata)
    except Exception as e:
        logging.error(f"Error fetching model metadata: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/credit-status')
def credit_status():
    try:
        # Check if credit status file exists
        credit_file = "/tmp/credit_status.json"
        if os.path.exists(credit_file):
            with open(credit_file, 'r') as f:
                credit_data = json.load(f)
                return jsonify(credit_data)
        else:
            # Return a default status if file doesn't exist
            return jsonify({
                "status": "unknown",
                "icon": "fa-battery",
                "percentage": 100,
                "balance": "N/A",
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    except Exception as e:
        logging.error(f"Error fetching credit status: {e}")
        return jsonify({"error": str(e)}), 500

from metadata_scheduler import get_model_metadata, get_credit_status

@app.route('/admin/run-scheduler', methods=['POST'])
def trigger_scheduler():
    try:
        # Run the metadata collection
        get_model_metadata()
        # Run the credit status check  
        get_credit_status()
        return jsonify({"status": "success", "message": "Scheduler completed"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)