# This module hold some constants and other variables often used within the main.py file.

DESCRIPTIONS = {
    "/get": "Endpoint for getting single documents according to vendor_id & doc_id.",
    # Delete
    "/delete": "Endpoint for deleting whole indices.",
    # Save
    "/save": "Endpoint used for saving documents.",
    # Search
    "/search": "Endpoint used for searching for documents in Elasticsearch.",
    "/search-gpt": "Endpoint used for searching for documents in Elasticsearch, then providing results as context and retrieving answer from GPT-3 DaVinci AI model.",
    "/search/phrase": "Endpoint used for searching for documents according to a phrase rather than terms.\n" +
    "Rules to be aware about when it comes to searching for a 'phrase' instead of 'terms':\n" +
    "Say we want to search for 'Shape of you' (famous song title), then:\n" +
    "1. The search terms 'Shape', 'of', and 'you' must appear in the content field.\n" +
    "2. The terms must appear in that order.\n" +
    "3. The terms must appear next to each other.",
    "/search/timespan": "Endpoint to search for documents according to their timestamp.",
    # Upload
    "/upload/csv": "Endpoint to upload .csv files to be parsed and have its content loaded into the ELK stack (search engine).",
    "/upload/docx": "Endpoint to upload .docx (MS Word) files to be parsed and have its content loaded into the ELK stack.",
}
