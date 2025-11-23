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
# READHACKER JSON SCHEMA (simplified)
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
                "required": ["full_name", "short_background"],
                "properties": {
                    "full_name": {"type": "string"},
                    "short_background": {"type": "string"}
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
st.title("📚 Readhacker: Book Metadata Finder (One-Step with Timing)")

book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

if st.button("Fetch Metadata"):
    if not book_title.strip():
        st.warning("Please enter a book title.")
        st.stop()

    # -----------------------------
    # 1. Fetch metadata
    # -----------------------------
    fetch_start = time.time()
    with st.spinner("Fetching metadata..."):

        prompt = f"""
        You are a research assistant with web access. Given the book title '{book_title}' 
        and optional author '{book_author}', extract the canonical metadata in JSON only.

        Required fields:
        - title (original and English)
        - authors (full_name and short background; can be multiple)
        - language (original language of the book)
        - publication_date (first publication date)
        - sources (list of URLs you used)

        Only include verified information. Do not hallucinate. Return strict JSON.
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
    fetch_end = time.time()

    st.info(f"Metadata fetch completed in {fetch_end - fetch_start:.2f} seconds")

    # -----------------------------
    # 2. Parse JSON
    # -----------------------------
    parse_start = time.time()
    try:
        metadata_json = json.loads(metadata_output)
    except json.JSONDecodeError:
        st.error("Output is not valid JSON.")
        st.stop()
    parse_end = time.time()
    st.info(f"JSON parsing completed in {parse_end - parse_start:.2f} seconds")

    # -----------------------------
    # 3. Normalize + Validate
    # -----------------------------
    norm_start = time.time()

    # Ensure title.english is a list
    if isinstance(metadata_json["title"].get("english"), str):
        metadata_json["title"]["english"] = [metadata_json["title"]["english"]]

    # Ensure authors is a list of dicts
    authors = metadata_json.get("authors", [])
    if isinstance(authors, dict):
        metadata_json["authors"] = [authors]
    elif isinstance(authors, list):
        metadata_json["authors"] = [
            a if isinstance(a, dict) else {"full_name": str(a), "short_background": ""}
            for a in authors
        ]
    else:
        metadata_json["authors"] = []

    # Validate JSON
    try:
        validate(instance=metadata_json, schema=BOOK_SCHEMA)
        st.success("Metadata is valid and normalized!")
    except ValidationError as ve:
        st.warning(f"Schema validation issue: {ve.message}")
    norm_end = time.time()

    # -----------------------------
    # Display
    # -----------------------------
    st.subheader("Raw Metadata JSON")
    st.code(metadata_output, language="json")

    st.subheader("Normalized + Validated JSON")
    st.json(metadata_json)

    total_time = fetch_end - fetch_start + parse_end - parse_start + norm_end - norm_start
    st.info(f"Timing breakdown (seconds): Fetch={fetch_end - fetch_start:.2f}, Parse={parse_end - parse_start:.2f}, Normalize+Validate={norm_end - norm_start:.2f}, Total={total_time:.2f}")
