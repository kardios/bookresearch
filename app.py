import streamlit as st
import os
import json
import time
from openai import OpenAI
from jsonschema import validate, ValidationError

# ------------------------
# LOAD API KEY
# ------------------------
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()

client = OpenAI(api_key=api_key)

# ------------------------
# SIMPLIFIED READHACKER SCHEMA
# ------------------------
BOOK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Readhacker Core Book Metadata",
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
# STREAMLIT UI
# ------------------------
st.set_page_config(page_title="Readhacker Core Metadata", page_icon="📚")
st.title("📚 Readhacker: Core Book Metadata Finder")
st.markdown("Enter a book title (and optionally author) to fetch canonical metadata using GPT-5-mini with web search.")

book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

if st.button("Fetch Metadata"):

    if not book_title.strip():
        st.warning("Please enter a book title.")
        st.stop()

    overall_start = time.time()

    # -----------------------------
    # STEP 1: ENTITY CONFIRMATION
    # -----------------------------
    step1_start = time.time()
    entity_prompt = f"""
    Identify the correct book entity for:
    Title: "{book_title}"
    Author: "{book_author}"

    Return ONLY a JSON object with:
    {{
        "confirmed_title": "...",
        "confirmed_author": "...",
        "notes": "Brief explanation of entity matching."
    }}
    Do not include extra fields.
    """
    try:
        entity_result = client.responses.create(
            model="gpt-5-mini",
            tools=[{"type": "web_search"}],
            tool_choice="auto",
            input=entity_prompt
        )
        entity_json = json.loads(entity_result.output_text)
        step1_elapsed = time.time() - step1_start
        st.info(f"Entity confirmation completed in {step1_elapsed:.2f}s")
    except Exception as e:
        st.error(f"Entity resolution failed: {e}")
        st.stop()

    # -----------------------------
    # STEP 2: CORE METADATA EXTRACTION
    # -----------------------------
    step2_start = time.time()
    metadata_prompt = f"""
    Using VERIFIED book identity:
    Title: "{entity_json['confirmed_title']}"
    Author: "{entity_json['confirmed_author']}"

    Extract ONLY the core canonical metadata:
    - title (original + English titles)
    - authors (full_name + short background)
    - language (original language)
    - publication_date (first publication year)

    Return strict JSON following this structure:
    {{
        "title": {{
            "original": "...",
            "english": ["..."]
        }},
        "authors": [
            {{
                "full_name": "...",
                "background": "..."
            }}
        ],
        "language": "...",
        "publication_date": "..."
    }}

    Do not include any extra fields or hallucinated information.
    """
    try:
        metadata_result = client.responses.create(
            model="gpt-5-mini",
            tools=[{"type": "web_search"}],
            tool_choice="auto",
            input=metadata_prompt
        )
        metadata_output = metadata_result.output_text
        step2_elapsed = time.time() - step2_start
        st.info(f"Metadata extraction completed in {step2_elapsed:.2f}s")
    except Exception as e:
        st.error(f"Metadata step failed: {e}")
        st.stop()

    # Show raw JSON
    st.subheader("Raw Metadata JSON")
    st.code(metadata_output, language="json")

    # -----------------------------
    # PARSE & NORMALIZE JSON
    # -----------------------------
    try:
        metadata_json = json.loads(metadata_output)
        # Ensure title.english is always an array
        if isinstance(metadata_json["title"].get("english"), str):
            metadata_json["title"]["english"] = [metadata_json["title"]["english"]]
    except json.JSONDecodeError:
        st.error("Output is not valid JSON.")
        st.stop()

    # -----------------------------
    # VALIDATE AGAINST SCHEMA
    # -----------------------------
    try:
        validate(instance=metadata_json, schema=BOOK_SCHEMA)
        st.success("Metadata is valid and normalized!")
    except ValidationError as ve:
        st.warning(f"Schema validation issue: {ve.message}")

    overall_elapsed = time.time() - overall_start
    st.info(f"Total elapsed time: {overall_elapsed:.2f}s")

    st.subheader("Normalized + Validated JSON")
    st.json(metadata_json)
