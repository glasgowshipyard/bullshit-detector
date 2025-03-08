import re
import logging
import nltk
from nltk.stem import WordNetLemmatizer

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
    logging.debug(f"Original query: {query}")

    # Apply sanitization steps (keep logging each step)
    query = query.strip()
    logging.debug(f"After stripping: {query}")

    for pattern in removal_phrases:
        query = re.sub(pattern, "", query, flags=re.IGNORECASE)
    logging.debug(f"After phrase removal: {query}")

    for word, replacement in synonym_map.items():
        query = re.sub(rf"\b{word}\b", replacement, query, flags=re.IGNORECASE)
    logging.debug(f"After synonym replacement: {query}")

    words = query.split()
    words = [lemmatizer.lemmatize(word.lower()) for word in words]  # Lemmatisation step
    logging.debug(f"After lemmatization: {' '.join(words)}")

    structured_query = f"This is a Bullshit Detector request for a TRUE or FALSE response: {' '.join(words)}"
    logging.debug(f"Final structured query: {structured_query}")

    return structured_query
