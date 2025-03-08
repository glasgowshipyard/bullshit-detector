from flask import Flask, request, jsonify
import re
import nltk
from nltk.stem import WordNetLemmatizer

# Initialize Flask app
app = Flask(__name__)

# Initialize NLP tools
nltk.download('wordnet')
lemmatizer = WordNetLemmatizer()

# Standard phrase removals to reduce bias
removal_phrases = [
    r"^Is it true that ",
    r"^I heard that ",
    r"^Some people say ",
    r"^They claim that ",
    r"^Wouldn't you agree that ",
    r"^Isn't it obvious that ",
    r"^Many believe that "
]

# Synonym mappings for standardization
synonym_map = {
    "covid": "COVID-19",
    "global warming": "climate change",
    "fake news": "misinformation",
    "hoax": "false claim"
}

# Function to preprocess query
def preprocess_query(query):
    query = query.strip()
    
    # Remove leading phrases that introduce bias
    for pattern in removal_phrases:
        query = re.sub(pattern, "", query, flags=re.IGNORECASE)
    
    # Replace synonyms with canonical terms
    for word, replacement in synonym_map.items():
        query = re.sub(rf"\b{word}\b", replacement, query, flags=re.IGNORECASE)
    
    # Tokenize and lemmatize
    words = query.split()
    words = [lemmatizer.lemmatize(word.lower()) for word in words]
    query = " ".join(words)
    
    # Ensure query follows the standard format
    structured_query = f"This is a Bullshit Detector request for a TRUE or FALSE response: {query}"
    
    return structured_query

@app.route('/preprocess', methods=['POST'])
def preprocess():
    data = request.json
    raw_query = data.get("query", "").strip()
    processed_query = preprocess_query(raw_query)
    return jsonify({"structured_query": processed_query})

if __name__ == '__main__':
    app.run(debug=True)
