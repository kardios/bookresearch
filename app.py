import streamlit as st
import json
import time
import os
from jsonschema import validate, ValidationError

# --- FIX FOR STREAMLIT CLOUD PROXY ISSUE ---
for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(key, None)

from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Readhacker metadata schema
READHACKER_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "object",
            "properties": {
                "original": {"type": "string"},
                "english": {"type": "string"},
            },
            "required": ["original", "english"]
        },
        "authors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "background": {"type": "string"},
                },
                "required": ["full_name", "background"]
            }
        },
        "editions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "edition_version": {"type": "string"},
                    "publication_date": {"type": "string"},
                    "language": {"type": "string"},
                },
                "required": ["edition_version", "publication_date", "language"]
            }
        },
        "languages": {"type": "array", "items": {"type": "string"}},
        "genres": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "authors", "editions", "languages", "genres", "sources"]
}

# --- STREAMLIT UI ---
st.title("📚 Book Metadata Fetcher (GPT-5.1 Mini)")
st.write("Enter a **book title** and (optionally) an **author name**.")

book_title = st.text_input("Book title")
author_name = st.text_input("Author (optional)")

run_button = st.button("Fetch Metadata")

# --- FUNCTION TO VALIDATE JSON ---
def validate_metadata(metadata):
    try:
        validate(instance=metadata, schema=READHACKER_SCHEMA)
        return True, None
    except ValidationError as e:
        return False, str(e)

# --- OPENAI METADATA REQUEST ---
def fetch_metadata(title, author):
    query = f"Title: {title}\n"
    if author.strip():
        query += f"Author: {author}\n"

    response = client.responses.create(
        model="gpt-5.1-mini",
        input=f"Generate complete Readhacker metadata JSON for the following book.\n{query}",
        max_output_tokens=800
    )

    # Extract the JSON from the model output
    content = response.output_text

    try:
        metadata = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("Model returned invalid JSON.")

    return metadata

# --- MAIN ACTION ---
if run_button:
    if not book_title.strip():
        st.error("Please enter a book title.")
    else:
        with st.spinner("Fetching metadata from GPT-5.1 Mini..."):
            try:
                metadata = fetch_metadata(book_title, author_name)
                valid, error = validate_metadata(metadata)

                if not valid:
                    st.error("❌ Metadata failed schema validation:")
                    st.code(error)
                else:
                    st.success("✅ Metadata fetched and validated!")
                    st.json(metadata)

            except Exception as e:
                st.error(f"Error: {e}")
