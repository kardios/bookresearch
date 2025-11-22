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

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Streamlined JSON schema
BOOK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Readhacker Book Metadata",
    "type": "object",
    "required": ["title", "author", "publication_date", "language", "genre_category"],
    "properties": {
        "title": {
            "type": "object",
            "properties": {
                "original": {"type": "string"},
                "english": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["original"]
        },
        "author": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string"},
                "background": {"type": "string"},
                "life_dates": {"type": "string"}
            },
            "required": ["full_name"]
        },
        "publication_date": {"type": "string"},
        "edition_version": {"type": "string"},
        "language": {"type": "array", "items": {"type": "string"}},
        "genre_category": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string", "format": "uri"}}
    },
    "additionalProperties": False
}

# Streamlit UI
st.set_page_config(page_title="Readhacker Metadata Finder", page_icon="📚")
st.title("📚 Readhacker: Book Metadata Finder")
st.markdown(
    "Enter a book title (and optionally author) to fetch canonical metadata using GPT-5 with web search."
)

# User input
book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

if st.button("Fetch Metadata"):
    if not book_title.strip():
        st.warning("Please enter a book title.")
    else:
        start_time = time.time()
        with st.spinner("Fetching metadata..."):
            prompt = f"""
            You are a research assistant with web access. Given the book title '{book_title}' and author '{book_author}', 
            provide canonical metadata for the book in strict JSON format matching this schema:

            Required fields: title (original and English), author (full_name, background, life_dates), 
            publication_date, edition_version, language, genre_category, sources (URLs).

            Only include info relevant to the correct book. Do not hallucinate.
            """

            try:
                response = client.responses.create(
                    model="gpt-5",
                    tools=[{"type": "web_search"}],
                    reasoning={"effort": "low"},  # faster response
                    tool_choice="auto",
                    input=prompt
                )

                metadata_output = response.output_text
                elapsed = time.time() - start_time

                st.subheader("Raw Metadata JSON")
                st.code(metadata_output, language="json")
                st.info(f"Fetch completed in {elapsed:.2f} seconds")

                # Validate JSON
                try:
                    metadata_json = json.loads(metadata_output)
                    validate(instance=metadata_json, schema=BOOK_SCHEMA)
                    st.success("Metadata is valid according to Readhacker schema!")
                except json.JSONDecodeError:
                    st.error("Output is not valid JSON.")
                except ValidationError as ve:
                    st.warning(f"Metadata JSON does not fully comply with schema: {ve.message}")

            except Exception as e:
                st.error(f"Error fetching metadata: {e}")
