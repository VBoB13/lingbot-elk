# This module hold some constants and other variables often used within the main.py file.

DESCRIPTIONS = {
    "/get": "Endpoint for getting single documents according to vendor_id & doc_id.",
    # Delete
    "/delete": "Endpoint for deleting whole indices.",
    "/delete_source": "Endpoint for deleting multiple documents inserted into ELK with the help of a source file, e.g. 'EBR.csv', 'Docs.docx' and so on...",
    # Entities
    "/extract-entities": "Endpoint for extracting entities from travel documents such as event descriptions or blog posts about such events.",
    # Intents
    "/intent-flight": "Endpoint for returning JSON data about the intents from a user wishing to book a flight.",
    # Save
    "/save": "Endpoint used for saving a single document.",
    "/save-bulk": "Endpoint for saving multiple documents.",
    # Search
    "/search": "Endpoint used for searching for documents in Elasticsearch.",
    "/search-gpt": "Endpoint used for searching for documents in Elasticsearch, then providing results as context and retrieving answer from GPT-3 DaVinci AI model.",
    "/search-gpt-v2": "Endpoint used for searching for documents in Elasticsearch using OpenAI LLM generated vectors for semantic search, then providing results as context and retrieving answer from OpenAI's 'gpt-3.5-turbo' model. This endpoint also has much better, clear and concise code as well as memory (conversation) management.",
    "/search/phrase": "Endpoint used for searching for documents according to a phrase rather than terms.\n" +
    "Rules to be aware about when it comes to searching for a 'phrase' instead of 'terms':\n" +
    "Say we want to search for 'Shape of you' (famous song title), then:\n" +
    "1. The search terms 'Shape', 'of', and 'you' must appear in the content field.\n" +
    "2. The terms must appear in that order.\n" +
    "3. The terms must appear next to each other.",
    "/search/timespan": "Endpoint to search for documents according to their timestamp.",
    # Upload
    "/upload": "Endpoint to upload any of .csv, .pdf or .docx files to be parsed and have its content loaded into Elasticsearch with OpenAI embeddings.",
    "/upload/csv": "Endpoint to upload .csv files to be parsed and have its content loaded into the ELK stack (search engine).",
    "/upload/docx": "Endpoint to upload .docx (MS Word) files to be parsed and have its content loaded into the ELK stack.",
}
