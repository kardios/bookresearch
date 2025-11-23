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
# Simplified Readhacker JSON Schema
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
                "required": ["full_name"],
                "properties": {
                    "full_name": {"type": "string"}
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
st.set_page_config(page_title="Readhacker Book Research", page_icon="📚")
st.title("📚 Readhacker: Book Metadata & Research")

book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

model_choice = st.selectbox(
    "Choose LLM for research steps",
    ["gpt-5-nano", "gpt-5-mini", "gpt-5", "gpt-5-pro"],
    index=3
)

if st.button("Fetch Metadata & Run Research"):

    if not book_title.strip():
        st.warning("Please enter a book title.")
        st.stop()

    # -----------------------------
    # Step 1: Fetch Canonical Metadata
    # -----------------------------
    start_time = time.time()
    with st.spinner("Fetching canonical metadata..."):
        metadata_prompt = f"""
        You are a research assistant with web access. Given the book title '{book_title}' 
        and optional author '{book_author}', extract canonical metadata in JSON only.

        Required fields:
        - title (original and English)
        - authors (full_name; short background optional)
        - language
        - publication_date
        - sources

        Only include verified information. Do not hallucinate. Return strict JSON.
        """

        try:
            response = client.responses.create(
                model="gpt-5-nano",
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                input=metadata_prompt
            )
            metadata_output = response.output_text
            metadata_fetch_time = time.time() - start_time
        except Exception as e:
            st.error(f"Metadata fetch failed: {e}")
            st.stop()

    # -----------------------------
    # Parse and Validate JSON
    # -----------------------------
    try:
        metadata_json = json.loads(metadata_output)
        # Ensure english title is an array
        if isinstance(metadata_json["title"].get("english"), str):
            metadata_json["title"]["english"] = [metadata_json["title"]["english"]]
        validate(instance=metadata_json, schema=BOOK_SCHEMA)
        st.success(f"Metadata fetched and validated! (Fetch time: {metadata_fetch_time:.2f}s)")
    except json.JSONDecodeError:
        st.error("Output is not valid JSON.")
        st.stop()
    except ValidationError as ve:
        st.warning(f"Schema validation issue: {ve.message}")

    # -----------------------------
    # Display Metadata in Text
    # -----------------------------
    with st.expander("📄 Canonical Metadata"):
        st.text(f"Title (Original): {metadata_json['title']['original']}")
        st.text(f"Title (English): {', '.join(metadata_json['title']['english'])}")
        st.text(f"Authors: {', '.join([a['full_name'] for a in metadata_json['authors']])}")
        st.text(f"Language: {metadata_json['language']}")
        st.text(f"Publication Date: {metadata_json['publication_date']}")
        st.text(f"Sources: {', '.join(metadata_json['sources'])}")

    # -----------------------------
    # Step 2: Run Research on Book
    # -----------------------------
    research_prompt = f"""
    You are a research assistant. Given the book:

    Title: {metadata_json['title']['original']}
    Authors: {', '.join([a['full_name'] for a in metadata_json['authors']])}
    Language: {metadata_json['language']}
    Publication Date: {metadata_json['publication_date']}

    Summarize the book in four areas:

    1. Core Thesis
    2. Key Arguments & Supporting Points
    3. Counter-Intuitive Insights
    4. Controversies & Debates

    Return plain text for readability, no JSON needed, do not cite URLs.
    """

    research_start = time.time()
    with st.spinner("Running research on book..."):
        try:
            research_response = client.responses.create(
                model=model_choice,
                reasoning={"effort": "medium"},
                input=research_prompt
            )
            research_fetch_time = time.time() - research_start
            research_text = research_response.output_text
        except Exception as e:
            st.error(f"Research step failed: {e}")
            st.stop()

    # -----------------------------
    # Display Research
    # -----------------------------
    with st.expander("📚 Book Research Output"):
        st.text(research_text)
        st.info(f"Research completed in {research_fetch_time:.2f} seconds")

    # -----------------------------
    # Download Button for JSON
    # -----------------------------
    st.download_button(
        label="📥 Download Canonical Metadata JSON",
        data=json.dumps(metadata_json, indent=2),
        file_name=f"{book_title.replace(' ','_')}_metadata.json",
        mime="application/json"
    )
