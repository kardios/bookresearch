import streamlit as st
import os
import json
import time
from openai import OpenAI
from jsonschema import validate, ValidationError

# ------------------------
# Load API key
# ------------------------
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()

client = OpenAI(api_key=api_key)

# ------------------------
# JSON Schema (simplified)
# ------------------------
BOOK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Readhacker Book Metadata",
    "type": "object",
    "required": ["title", "authors", "language", "publication_date", "sources"],
    "properties": {
        "title": {
            "type": "object",
            "properties": {
                "original": {"type": "string"},
                "english": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["original"]
        },
        "authors": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["full_name", "background"],
                "properties": {
                    "full_name": {"type": "string"},
                    "background": {"type": "string"}
                }
            }
        },
        "language": {"type": "string"},
        "publication_date": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string", "format": "uri"}}
    },
    "additionalProperties": False
}

# ------------------------
# Streamlit UI
# ------------------------
st.set_page_config(page_title="Readhacker Metadata Finder", page_icon="📚")
st.title("📚 Readhacker: Book Metadata Finder (One-Step, Clean + Sources)")

book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

if st.button("Fetch Metadata"):
    if not book_title.strip():
        st.warning("Please enter a book title.")
        st.stop()

    start_time = time.time()
    with st.spinner("Fetching metadata..."):

        prompt = f"""
        You are a research assistant with web access. Given the book title '{book_title}' 
        and optional author '{book_author}', extract canonical metadata in strict JSON.

        Requirements:
        1. Original title.
        2. All plausible English titles (deduplicate if repeated) with source URLs.
        3. Authors (full_name + short background), only if a source URL is available.
        4. Language and first publication date.
        5. Return a top-level array 'sources' listing ALL URLs used in metadata.
        6. Return strict JSON only; do not include unverified info.
        """

        try:
            response = client.responses.create(
                model="gpt-5-mini",
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                input=prompt
            )

            metadata_output = response.output_text

        except Exception as e:
            st.error(f"Metadata fetch failed: {e}")
            st.stop()

    fetch_time = time.time() - start_time
    st.info(f"Metadata fetch completed in {fetch_time:.2f} seconds")

    # -----------------------------
    # Show raw JSON
    # -----------------------------
    st.subheader("Raw Metadata JSON")
    st.code(metadata_output, language="json")

    # -----------------------------
    # Parse JSON
    # -----------------------------
    try:
        metadata_json = json.loads(metadata_output)
    except json.JSONDecodeError:
        st.error("Output is not valid JSON.")
        st.stop()

    # -----------------------------
    # Normalize English titles and authors
    # -----------------------------
    # Deduplicate English titles
    if "english" in metadata_json.get("title", {}):
        metadata_json["title"]["english"] = list(dict.fromkeys(metadata_json["title"]["english"]))

    # Ensure authors is always a list
    if isinstance(metadata_json.get("authors"), dict):
        metadata_json["authors"] = [metadata_json["authors"]]

    # Ensure sources is a list
    if isinstance(metadata_json.get("sources"), str):
        metadata_json["sources"] = [metadata_json["sources"]]

    # -----------------------------
    # Validate JSON
    # -----------------------------
    try:
        validate(instance=metadata_json, schema=BOOK_SCHEMA)
        st.success("Metadata is valid and normalized!")

    except ValidationError as ve:
        st.warning(f"Schema validation issue: {ve.message}")

    st.subheader("Normalized + Validated JSON")
    st.json(metadata_json)
