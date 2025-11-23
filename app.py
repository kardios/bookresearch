import streamlit as st
import os
import json
import time
import re
from openai import OpenAI
from jsonschema import validate, ValidationError

# ------------------------
# API key & client setup
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
    "required": ["title", "authors", "language", "publication_date"],
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
        "publication_date": {"type": "string"}
    },
    "additionalProperties": False
}

# ------------------------
# Helper functions
# ------------------------
def strip_links(text: str) -> str:
    """Remove markdown/HTML links from text."""
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

def normalize_lists(metadata: dict):
    if isinstance(metadata["title"].get("english"), str):
        metadata["title"]["english"] = [metadata["title"]["english"]]
    if isinstance(metadata.get("authors"), dict):
        metadata["authors"] = [metadata["authors"]]

# ------------------------
# Streamlit UI
# ------------------------
st.set_page_config(page_title="Readhacker Metadata Finder", page_icon="📚")
st.title("📚 Readhacker: Book Metadata Finder")

book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

if st.button("Fetch Metadata"):

    if not book_title.strip():
        st.warning("Please enter a book title.")
        st.stop()

    start_time = time.time()

    with st.spinner("Resolving book entity..."):

        # -----------------------------
        # STEP 1: ENTITY CONFIRMATION
        # -----------------------------
        entity_prompt = f"""
        Identify the correct book entity for:
        Title: "{book_title}"
        Author: "{book_author}"

        Return ONLY a JSON object:
        {{
            "confirmed_title": "...",
            "confirmed_author": "...",
            "notes": "Brief explanation of how you matched the book."
        }}
        """
        try:
            entity_result = client.responses.create(
                model="gpt-5-mini",
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                input=entity_prompt
            )
            entity_json = json.loads(entity_result.output_text)
        except Exception as e:
            st.error(f"Entity resolution failed: {e}")
            st.stop()

    entity_time = time.time() - start_time
    st.info(f"Entity confirmation completed in {entity_time:.2f}s")

    with st.spinner("Fetching book metadata..."):

        # -----------------------------
        # STEP 2: METADATA EXTRACTION (MINIMAL)
        # -----------------------------
        metadata_prompt = f"""
        Using VERIFIED book identity:

        Title: "{entity_json['confirmed_title']}"
        Author: "{entity_json['confirmed_author']}"

        Return STRICT JSON with ONLY the following fields:
        - title.original
        - title.english
        - authors[].full_name
        - authors[].background
        - language
        - publication_date

        Do not include anything else, even if sources mention it.
        """
        try:
            response = client.responses.create(
                model="gpt-5-mini",
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                input=metadata_prompt
            )
            metadata_output = response.output_text
        except Exception as e:
            st.error(f"Metadata step failed: {e}")
            st.stop()

    metadata_time = time.time() - start_time - entity_time
    st.info(f"Metadata extraction completed in {metadata_time:.2f}s")

    # -----------------------------
    # Parse & clean JSON
    # -----------------------------
    try:
        metadata_json = json.loads(metadata_output)
        normalize_lists(metadata_json)

        # Strip links from all strings
        metadata_json["title"]["original"] = strip_links(metadata_json["title"]["original"])
        metadata_json["title"]["english"] = [strip_links(t) for t in metadata_json["title"]["english"]]
        for author in metadata_json["authors"]:
            author["full_name"] = strip_links(author["full_name"])
            author["background"] = strip_links(author["background"])
        metadata_json["language"] = strip_links(metadata_json["language"])
        metadata_json["publication_date"] = strip_links(metadata_json["publication_date"])

        # Validate
        validate(instance=metadata_json, schema=BOOK_SCHEMA)
        st.success("Metadata is valid and normalized!")

    except json.JSONDecodeError:
        st.error("Output is not valid JSON.")
        st.stop()
    except ValidationError as ve:
        st.warning(f"Schema validation issue: {ve.message}")

    total_time = time.time() - start_time
    st.info(f"Total elapsed time: {total_time:.2f}s")

    st.subheader("Normalized + Validated JSON")
    st.json(metadata_json)
