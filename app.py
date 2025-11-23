import streamlit as st
import os
import json
import time
from openai import OpenAI
from jsonschema import validate, ValidationError

# ------------------------
# CONFIG
# ------------------------
st.set_page_config(page_title="Readhacker: Metadata + Research", page_icon="📚")
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()

client = OpenAI(api_key=API_KEY)

# ------------------------
# SCHEMA (simplified)
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
# UI - Inputs
# ------------------------
st.title("📚 Readhacker — Metadata & Two-Step Research")
st.markdown("Fetch canonical metadata, then run research in two steps: (1) Core Thesis & Key Arguments, (2) Controversies & Debates. Each step is timed.")

book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

# Session-state storage so results persist between interactions
if "metadata_json" not in st.session_state:
    st.session_state["metadata_json"] = None
if "fetch_time" not in st.session_state:
    st.session_state["fetch_time"] = None
if "step1_text" not in st.session_state:
    st.session_state["step1_text"] = None
if "step1_time" not in st.session_state:
    st.session_state["step1_time"] = None
if "step2_text" not in st.session_state:
    st.session_state["step2_text"] = None
if "step2_time" not in st.session_state:
    st.session_state["step2_time"] = None

# ------------------------
# METADATA FETCH
# ------------------------
if st.button("Fetch Metadata"):
    if not book_title.strip():
        st.warning("Please enter a book title.")
    else:
        start_time = time.time()
        with st.spinner("Fetching canonical metadata..."):
            prompt_metadata = f"""
You are a research assistant with web access. Given the book title '{book_title}'
and optional author '{book_author}', extract canonical metadata in strict JSON.

Required fields:
- title (original and English)
- authors (full_name; can be multiple)
- language (original language)
- publication_date (first publication date)
- sources (list of URLs used)

Only include verified information. Do not hallucinate. Return strict JSON.
"""
            try:
                resp = client.responses.create(
                    model="gpt-5-nano",
                    tools=[{"type": "web_search"}],
                    tool_choice="auto",
                    input=prompt_metadata
                )
                metadata_output = resp.output_text
            except Exception as e:
                st.error(f"Metadata fetch failed: {e}")
                metadata_output = None

        fetch_time = time.time() - start_time

        if not metadata_output:
            st.stop()

        # Parse & normalize
        try:
            metadata_json = json.loads(metadata_output)
        except json.JSONDecodeError:
            st.error("Metadata output is not valid JSON.")
            st.stop()

        # Ensure title.english is an array
        if isinstance(metadata_json.get("title", {}).get("english"), str):
            metadata_json["title"]["english"] = [metadata_json["title"]["english"]]

        # Ensure authors is list
        authors = metadata_json.get("authors", [])
        if isinstance(authors, dict):
            metadata_json["authors"] = [authors]
        elif not isinstance(authors, list):
            metadata_json["authors"] = []

        # Validate
        try:
            validate(instance=metadata_json, schema=BOOK_SCHEMA)
            st.success("Metadata validated.")
            st.session_state["metadata_json"] = metadata_json
            st.session_state["fetch_time"] = fetch_time
            # reset research steps
            st.session_state["step1_text"] = None
            st.session_state["step1_time"] = None
            st.session_state["step2_text"] = None
            st.session_state["step2_time"] = None
        except ValidationError as ve:
            st.warning(f"Schema validation issue: {ve.message}")
            st.session_state["metadata_json"] = None
            st.session_state["fetch_time"] = fetch_time

# Show metadata if present
if st.session_state["metadata_json"]:
    st.subheader("Canonical Metadata")
    st.json(st.session_state["metadata_json"])
    st.info(f"Metadata fetch time: {st.session_state['fetch_time']:.2f} s")

    st.markdown("---")

    # ------------------------
    # STEP 1: Core Thesis & Key Arguments
    # ------------------------
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Generate Core Thesis & Key Arguments"):
            # run step 1
            step1_start = time.time()
            with st.spinner("Generating Core Thesis & Key Arguments..."):
                metadata_fragment = json.dumps(st.session_state["metadata_json"], ensure_ascii=False)
                prompt_step1 = f"""
Using only the verified metadata and sources below, identify the book's CORE THESIS and 3-5 KEY ARGUMENTS with 1-2 supporting points for each.

Metadata:
{metadata_fragment}

Return only plain, human-readable text formatted for display. Use a short heading "Core Thesis:" followed by one paragraph, then "Key Arguments:" and numbered bullet points with 1-2 supporting lines each. Do NOT output JSON.
"""
                try:
                    resp1 = client.responses.create(
                        model="gpt-5-nano",
                        tools=[{"type": "web_search"}],
                        tool_choice="auto",
                        input=prompt_step1
                    )
                    step1_text = resp1.output_text
                except Exception as e:
                    st.error(f"Step 1 failed: {e}")
                    step1_text = None
            step1_time = time.time() - step1_start
            st.session_state["step1_text"] = step1_text
            st.session_state["step1_time"] = step1_time

    with col2:
        if st.session_state.get("step1_time") is not None:
            st.info(f"Last Step 1 run: {st.session_state['step1_time']:.2f} s")

    # Display step1 result
    if st.session_state["step1_text"]:
        with st.expander("Core Thesis & Key Arguments", expanded=True):
            st.markdown(st.session_state["step1_text"])

    st.markdown("---")

    # ------------------------
    # STEP 2: Controversies & Debates
    # ------------------------
    col3, col4 = st.columns([1, 1])
    with col3:
        if st.button("Generate Controversies & Debates"):
            # run step 2
            step2_start = time.time()
            with st.spinner("Generating Controversies & Debates..."):
                metadata_fragment = json.dumps(st.session_state["metadata_json"], ensure_ascii=False)
                # If step1_text exists, include it so the controversies prompt has context
                step1_context = st.session_state.get("step1_text") or ""
                prompt_step2 = f"""
Using only the verified metadata and sources below (and the previously generated Core Thesis & Key Arguments if available), list the main CONTROVERSIES, CRITICISMS, and DEBATES about this book or its arguments.

Metadata:
{metadata_fragment}

Previously generated (optional) — Core Thesis & Key Arguments:
{step1_context}

Return plain, human-readable text. Use a short heading "Controversies & Debates:" and then bullet points describing each criticism/debate and, if available, the narrow source or perspective (no raw URLs required). Do NOT output JSON.
"""
                try:
                    resp2 = client.responses.create(
                        model="gpt-5-nano",
                        tools=[{"type": "web_search"}],
                        tool_choice="auto",
                        input=prompt_step2
                    )
                    step2_text = resp2.output_text
                except Exception as e:
                    st.error(f"Step 2 failed: {e}")
                    step2_text = None
            step2_time = time.time() - step2_start
            st.session_state["step2_text"] = step2_text
            st.session_state["step2_time"] = step2_time

    with col4:
        if st.session_state.get("step2_time") is not None:
            st.info(f"Last Step 2 run: {st.session_state['step2_time']:.2f} s")

    # Display step2 result
    if st.session_state["step2_text"]:
        with st.expander("Controversies & Debates", expanded=False):
            st.markdown(st.session_state["step2_text"])

else:
    st.info("No validated metadata yet. Fetch metadata first, then run research steps.")
