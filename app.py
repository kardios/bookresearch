import streamlit as st
import os
import json
import time
from openai import OpenAI
from jsonschema import validate, ValidationError

# Load API key from environment variable
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()

client = OpenAI(api_key=api_key)

# Multi-valued JSON schema for Readhacker
BOOK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Readhacker Book Metadata",
    "type": "object",
    "required": ["title", "authors", "languages", "genres", "sources"],
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
        "editions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "edition_version": {"type": "string"},
                    "publication_date": {"type": "string"},
                    "language": {"type": "string"}
                }
            }
        },
        "languages": {"type": "array", "items": {"type": "string"}},
        "genres": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string", "format": "uri"}}
    },
    "additionalProperties": False
}

# Streamlit UI
st.set_page_config(page_title="Readhacker Metadata Finder", page_icon="📚")
st.title("📚 Readhacker: Book Metadata Finder (GPT-5.1, Reasoning None)")
st.markdown(
    "Enter a book title (and optionally author) to fetch canonical metadata using GPT-5.1 with web search. "
    "This version uses `reasoning: none` for fastest responses. No caching is used."
)

# User input
book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

if st.button("Fetch Metadata"):
    if not book_title.strip():
        st.warning("Please enter a book title.")
    else:
        start_time = time.time()
        with st.spinner("Fetching metadata from web (GPT-5.1, reasoning none)..."):
            prompt = f"""
            You are a research assistant with web access. Given the book title '{book_title}' and author '{book_author}', 
            provide canonical metadata for the book in strict JSON format matching the Readhacker multi-valued schema.

            Required fields: 
            - title (original and English) 
            - authors (full_name and background; can be multiple) 
            - editions (edition_version, publication_date, language; can be multiple) 
            - languages (array) 
            - genres (array) 
            - sources (URLs; array)

            Only include info relevant to the correct book. Do not hallucinate.
            """

            try:
                response = client.responses.create(
                    model="gpt-5.1",                   # GPT-5.1
                    tools=[{"type": "web_search"}],
                    reasoning={"effort": "none"},      # reasoning none for fastest fetch
                    tool_choice="auto",
                    input=prompt
                )

                metadata_output = response.output_text
                elapsed = time.time() - start_time
                st.subheader("Raw Metadata JSON")
                st.code(metadata_output, language="json")
                st.info(f"Fetch completed in {elapsed:.2f} seconds")

                # Parse JSON
                try:
                    metadata_json = json.loads(metadata_output)

                    # === Auto-normalization ===
                    if isinstance(metadata_json["title"].get("english"), str):
                        metadata_json["title"]["english"] = [metadata_json["title"]["english"]]

                    if isinstance(metadata_json.get("languages"), str):
                        metadata_json["languages"] = [metadata_json["languages"]]

                    if isinstance(metadata_json.get("genres"), str):
                        metadata_json["genres"] = [metadata_json["genres"]]

                    if isinstance(metadata_json.get("authors"), dict):
                        metadata_json["authors"] = [metadata_json["authors"]]

                    if isinstance(metadata_json.get("editions"), dict):
                        metadata_json["editions"] = [metadata_json["editions"]]

                    # Validate against schema
                    validate(instance=metadata_json, schema=BOOK_SCHEMA)
                    st.success("Metadata is valid according to Readhacker schema!")

                except json.JSONDecodeError:
                    st.error("Output is not valid JSON.")
                except ValidationError as ve:
                    st.warning(f"Metadata JSON does not fully comply with schema: {ve.message}")

            except Exception as e:
                st.error(f"Error fetching metadata: {e}")
