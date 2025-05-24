import logging
import re
import nltk
from nltk.stem import WordNetLemmatizer

# Ensure necessary NLTK data is available
nltk.download('wordnet')

# Initialize lemmatizer
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
    logging.debug(f"Original query: {query}")

    query = query.strip()
    logging.debug(f"After stripping: {query}")

    for pattern in removal_phrases:
        query = re.sub(pattern, "", query, flags=re.IGNORECASE)
    logging.debug(f"After phrase removal: {query}")

    for word, replacement in synonym_map.items():
        query = re.sub(rf"\b{word}\b", replacement, query, flags=re.IGNORECASE)
    logging.debug(f"After synonym replacement: {query}")

    words = query.split()

    # Explicitly prevent "was" → "be" conversion
    #words = [word if word.lower() in ["was", "were"] else lemmatizer.lemmatize(word.lower(), pos="v") for word in words]
    #logging.debug(f"After lemmatization: {' '.join(words)}")

    structured_query = f"You are part of the Bullshit Detector multi-model consensus system. Evaluate this claim's factual accuracy and respond with TRUE, FALSE, UNCERTAIN, RECUSE (if unanswerable/paradoxical), or POLICY_LIMITED (if you cannot evaluate due to safety/policy constraints), followed by your reasoning: {' '.join(words)}"
    logging.debug(f"Final structured query: {structured_query}")

    return structured_query
