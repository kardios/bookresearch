import streamlit as st
import os
import json
import time
import pandas as pd
from openai import OpenAI
from jsonschema import validate, ValidationError

# Load API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()

client = OpenAI(api_key=api_key)

# Readhacker schema
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
st.title("📚 Readhacker: Metadata Fetch (GPT-5-mini)")

st.markdown(
    "Fetch canonical book metadata from the web using GPT-5-mini. "
    "Results are displayed in a structured table."
)

# Inputs
book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

if st.button("Fetch Metadata"):
    if not book_title.strip():
        st.warning("Please enter a book title.")
    else:
        start_time = time.time()
        with st.spinner("Fetching metadata (GPT-5-mini)..."):
            fetch_prompt = f"""
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
                    model="gpt-5-mini",
                    tools=[{"type": "web_search"}],
                    tool_choice="auto",
                    input=fetch_prompt
                )

                metadata_output = response.output_text
                elapsed = time.time() - start_time
                st.subheader("Raw Metadata JSON")
                st.code(metadata_output, language="json")
                st.info(f"Metadata fetch completed in {elapsed:.2f} seconds")

                try:
                    metadata_json = json.loads(metadata_output)

                    # Normalize arrays
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

                    # Validate schema
                    validate(instance=metadata_json, schema=BOOK_SCHEMA)
                    st.success("Metadata is valid according to Readhacker schema!")

                    # Display nicely in table
                    table_data = []

                    # Title
                    table_data.append({
                        "Field": "Title (Original)",
                        "Value": metadata_json["title"].get("original", "")
                    })
                    table_data.append({
                        "Field": "Title (English)",
                        "Value": ", ".join(metadata_json["title"].get("english", []))
                    })

                    # Authors
                    author_strings = [
                        f"{a.get('full_name')} ({a.get('background')})"
                        for a in metadata_json.get("authors", [])
                    ]
                    table_data.append({"Field": "Authors", "Value": "; ".join(author_strings)})

                    # Editions
                    edition_strings = [
                        f"{e.get('edition_version')} | {e.get('publication_date')} | {e.get('language')}"
                        for e in metadata_json.get("editions", [])
                    ]
                    table_data.append({"Field": "Editions", "Value": "; ".join(edition_strings)})

                    # Languages
                    table_data.append({"Field": "Languages", "Value": ", ".join(metadata_json.get("languages", []))})

                    # Genres
                    table_data.append({"Field": "Genres", "Value": ", ".join(metadata_json.get("genres", []))})

                    # Sources
                    table_data.append({"Field": "Sources", "Value": "\n".join(metadata_json.get("sources", []))})

                    df = pd.DataFrame(table_data)
                    st.subheader("Structured Metadata Table")
                    st.dataframe(df)

                except json.JSONDecodeError:
                    st.error("Metadata output is not valid JSON.")
                except ValidationError as ve:
                    st.warning(f"Metadata JSON does not fully comply with schema: {ve.message}")

            except Exception as e:
                st.error(f"Error fetching metadata: {e}")
