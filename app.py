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
                "required": ["full_name"],
                "properties": {"full_name": {"type": "string"}}
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
st.title("📚 Readhacker: Book Metadata + Research")

# Inputs
book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

model_choice = st.selectbox(
    "Choose model for research",
    options=["gpt-5-nano", "gpt-5-mini", "gpt-5", "gpt-5-pro"],
    index=3,
)
reasoning_effort = st.radio("Reasoning Effort", options=["low", "medium", "high"], index=1)

if st.button("Fetch Metadata & Research"):

    if not book_title.strip():
        st.warning("Please enter a book title.")
        st.stop()

    start_time = time.time()
    with st.spinner("Fetching canonical metadata..."):

        # -----------------------------
        # Canonical Metadata fetch
        # -----------------------------
        metadata_prompt = f"""
        You are a research assistant with web access. Given the book title '{book_title}' 
        and optional author '{book_author}', extract canonical metadata in JSON only.

        Required fields:
        - title (original and English)
        - authors (full_name)
        - language (original language of the book)
        - publication_date (first publication date)
        - sources (list of URLs)

        Only include verified information. Do not hallucinate. Return strict JSON.
        """

        try:
            metadata_resp = client.responses.create(
                model="gpt-5-nano",
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                reasoning={"effort": "low"},
                input=metadata_prompt,
            )
            metadata_output = metadata_resp.output_text
        except Exception as e:
            st.error(f"Metadata fetch failed: {e}")
            st.stop()

    fetch_time = time.time() - start_time
    st.info(f"Metadata fetch completed in {fetch_time:.2f} seconds")

    # -----------------------------
    # Parse & normalize metadata JSON
    # -----------------------------
    try:
        metadata_json = json.loads(metadata_output)
    except json.JSONDecodeError:
        st.error("Metadata output is not valid JSON.")
        st.stop()

    # Normalize lists
    if isinstance(metadata_json.get("title", {}).get("english"), str):
        metadata_json["title"]["english"] = [metadata_json["title"]["english"]]

    for key in ["authors", "sources"]:
        if isinstance(metadata_json.get(key), dict):
            metadata_json[key] = [metadata_json[key]]
        elif isinstance(metadata_json.get(key), str):
            metadata_json[key] = [metadata_json[key]]

    # Validate JSON
    try:
        validate(instance=metadata_json, schema=BOOK_SCHEMA)
        st.success("Canonical metadata is valid!")
    except ValidationError as ve:
        st.warning(f"Schema validation issue: {ve.message}")

    # -----------------------------
    # Display metadata in text
    # -----------------------------
    with st.expander("Canonical Metadata (Text)"):
        st.text(f"Title (Original): {metadata_json['title'].get('original','')}")
        st.text(f"Title (English): {', '.join(metadata_json['title'].get('english',[]))}")
        authors_list = [a['full_name'] for a in metadata_json.get("authors",[])]
        st.text(f"Authors: {', '.join(authors_list)}")
        st.text(f"Language: {metadata_json.get('language','')}")
        st.text(f"Publication Date: {metadata_json.get('publication_date','')}")
        sources = metadata_json.get("sources",[]) or []
        if isinstance(sources, str):
            sources = [sources]
        st.text(f"Sources: {', '.join(sources)}")

    # -----------------------------
    # Research Step
    # -----------------------------
    research_prompt = f"""
    Using the canonical metadata below, analyze the book and return a structured text report.

    Canonical Metadata:
    {json.dumps(metadata_json, indent=2)}

    Research Areas:
    1. Core Thesis
    2. Key Arguments
    3. Controversies
    4. Counter-Intuitive Insights

    Return plain text, readable summaries under each heading.
    Do not include JSON.
    """

    research_start = time.time()
    with st.spinner("Running research..."):
        try:
            research_resp = client.responses.create(
                model=model_choice,
                reasoning={"effort": reasoning_effort},
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                input=research_prompt,
            )
            research_output = research_resp.output_text
        except Exception as e:
            st.error(f"Research step failed: {e}")
            st.stop()
    research_time = time.time() - research_start
    st.info(f"Research completed in {research_time:.2f} seconds")

    # -----------------------------
    # Display research output
    # -----------------------------
    with st.expander("Book Research"):
        st.text(research_output)

    # -----------------------------
    # Download JSON
    # -----------------------------
    st.download_button(
        "Download Canonical Metadata + Research",
        data=json.dumps({"metadata": metadata_json, "research": research_output}, indent=2),
        file_name="book_research.json",
        mime="application/json",
    )
