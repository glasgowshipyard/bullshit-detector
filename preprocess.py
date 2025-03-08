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

    # Explicitly lemmatize words as verbs to avoid incorrect truncation
    words = [lemmatizer.lemmatize(word.lower(), pos="v") for word in words]

    logging.debug(f"After lemmatization: {' '.join(words)}")

    structured_query = f"This is a Bullshit Detector request for a TRUE or FALSE response: {' '.join(words)}"
    logging.debug(f"Final structured query: {structured_query}")

    return structured_query
