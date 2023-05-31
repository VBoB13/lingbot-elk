# This module hold some constants and other variables often used within the main.py file.

DESCRIPTIONS = {
    # Delete
    "/delete_source": "Endpoint for deleting multiple documents inserted into ELK with the help of a source file, e.g. 'EBR.csv', 'Docs.docx' and so on...",
    "/delete_bot": "Endpoint for deleting EVERYTHING ('info' AND 'history' indices) that relates to any newer Lingbot (e.g. created using V2 endpoints).",
    # Search
    "/search-file": "Endpoint for searching through contents found within the /data/csv folder (dedicated to return only source documents based on query).",
    "/search-gpt": "Endpoint used for searching for documents in Elasticsearch, then providing results as context and retrieving answer from GPT-3 DaVinci AI model.",
    # Template
    "/set-template": "Endpoint for setting template for any `vendor_id` or file specific index.",
    # Local LLM
    "/set-llm-address": "Endpoint for Claude to use to set the value of the current local LLM address.",
    # Upload
    "/upload": "Endpoint to upload any of .csv, .pdf or .docx files to be parsed and have its content loaded into Elasticsearch with OpenAI embeddings.",
    "/upload/csv": "Endpoint to upload .csv files to be parsed and have its content loaded into the ELK stack (search engine).",
    "/upload/docx": "Endpoint to upload .docx (MS Word) files to be parsed and have its content loaded into the ELK stack.",
}
