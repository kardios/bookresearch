import streamlit as st
import os
import json
import time
from openai import OpenAI
from jsonschema import validate, ValidationError

# ------------------------
# Config / Client
# ------------------------
st.set_page_config(page_title="Readhacker: Metadata + Research (Combined)", page_icon="📚")
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()

client = OpenAI(api_key=API_KEY)

# ------------------------
# Simplified metadata schema (unchanged)
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
# UI inputs
# ------------------------
st.title("📚 Readhacker — Metadata + Combined Research")
st.markdown("Fetch canonical metadata with **gpt-5-nano**, then run a combined research step (Core Thesis, Key Arguments, Controversies) using a chosen model and reasoning level.")

book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

# Research model & reasoning controls
st.sidebar.header("Research model settings")
model_choice = st.sidebar.selectbox(
    "Research model",
    options=["gpt-5-mini", "gpt-5", "gpt-5-pro"],
    index=1,
    help="Choose model for the combined research step (mini = fast, pro = highest-quality)"
)
reasoning_effort = st.sidebar.selectbox(
    "Reasoning effort",
    options=["none", "low", "medium", "high"],
    index=2,
    help="Set internal reasoning effort. 'none' disables reasoning tool behavior."
)
# Option: disable web search for research (use model knowledge only)
use_web_search = st.sidebar.checkbox("Allow web search during research", value=True)

# Session-state for metadata & results
if "metadata_json" not in st.session_state:
    st.session_state["metadata_json"] = None
if "fetch_time" not in st.session_state:
    st.session_state["fetch_time"] = None
if "research_text" not in st.session_state:
    st.session_state["research_text"] = None
if "research_time" not in st.session_state:
    st.session_state["research_time"] = None

# ------------------------
# METADATA FETCH (gpt-5-nano)
# ------------------------
if st.button("Fetch Canonical Metadata (gpt-5-nano)"):
    if not book_title.strip():
        st.warning("Please enter a book title.")
    else:
        start_time = time.time()
        with st.spinner("Fetching canonical metadata with gpt-5-nano..."):
            prompt_metadata = f"""
You are a research assistant with web access. Given the book title '{book_title}'
and optional author '{book_author}', extract canonical metadata in strict JSON.

Required fields:
- title (original and english)
- authors (full_name; multiple allowed)
- language (original language)
- publication_date (first publication date)
- sources (list of URLs used)

Only include verified information. Do not hallucinate. Return strict JSON.
"""
            try:
                resp = client.responses.create(
                    model="gpt-5-nano",
                    tools=[{"type": "web_search"}] if True else [],
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
            # clear previous research
            st.session_state["research_text"] = None
            st.session_state["research_time"] = None
        except ValidationError as ve:
            st.warning(f"Schema validation issue: {ve.message}")
            st.session_state["metadata_json"] = None
            st.session_state["fetch_time"] = fetch_time

# Display metadata if present
if st.session_state["metadata_json"]:
    st.subheader("Canonical Metadata")
    st.json(st.session_state["metadata_json"])
    st.info(f"Metadata fetch time: {st.session_state['fetch_time']:.2f} s")

    st.markdown("---")

    # ------------------------
    # Combined research step (one API call)
    # ------------------------
    st.markdown("### Combined Research Step (one call)")
    st.write("This will produce: **Core Thesis**, **Key Arguments & Supporting Points**, and **Controversies & Debates** in one response. No source citations will be included.")
    col1, col2 = st.columns([2,1])
    with col1:
        if st.button("Run Combined Research"):
            # Build research prompt using validated metadata
            md = st.session_state["metadata_json"]
            # Compose a short, deterministic metadata summary
            first_english = md["title"]["english"][0] if md.get("title") and md["title"].get("english") else ""
            authors_list = ", ".join([a.get("full_name", "") for a in md.get("authors", [])])
            metadata_text = (
                f"Title (original): {md['title'].get('original','')}\n"
                f"Title (english sample): {first_english}\n"
                f"Authors: {authors_list}\n"
                f"Language: {md.get('language','')}\n"
                f"Publication date: {md.get('publication_date','')}\n"
            )

            # Single combined prompt (no citations)
            prompt_research = f"""
You are an expert literary and intellectual analyst with web access (if allowed). Using ONLY the verified metadata below,
produce a human-readable answer containing three labeled sections:

1) Core Thesis:
   - A single concise paragraph (3-6 sentences) that states the book's core thesis.

2) Key Arguments & Supporting Points:
   - Provide 3-5 numbered key arguments the author uses to support the thesis.
   - For each argument, include 1-2 short supporting bullet points (evidence, examples, or reasoning).

3) Controversies & Debates:
   - List the main controversies, criticisms, or debates related to the book or its central claims. Keep these as bullet points.
   - Do NOT include web URLs or formal citations — plain text only.

Metadata (verified):
{metadata_text}

Constraints:
- Base your output only on verifiable information from the provided metadata and your web search (if enabled).
- Do NOT invent facts or attribute claims without basis.
- Output only plain, human-readable text formatted with clear headings: "Core Thesis:", "Key Arguments:", "Controversies & Debates:".
- Keep the entire response concise (aim for ~300-700 words).

"""
            # Prepare API call options
            tools = [{"type":"web_search"}] if use_web_search else []
            reasoning_param = None
            if reasoning_effort != "none":
                # models that support reasoning accept a reasoning param
                reasoning_param = {"effort": reasoning_effort}

            # Time and call
            research_start = time.time()
            with st.spinner(f"Running research with {model_choice} (reasoning={reasoning_effort})..."):
                try:
                    # Build call dictionary to include reasoning only if not None
                    call_kwargs = {
                        "model": model_choice,
                        "tools": tools,
                        "tool_choice": "auto",
                        "input": prompt_research
                    }
                    if reasoning_param is not None:
                        call_kwargs["reasoning"] = reasoning_param

                    resp_research = client.responses.create(**call_kwargs)
                    research_text = resp_research.output_text
                except Exception as e:
                    st.error(f"Research call failed: {e}")
                    research_text = None
            research_time = time.time() - research_start

            # Save
            st.session_state["research_text"] = research_text
            st.session_state["research_time"] = research_time

    with col2:
        if st.session_state.get("research_time") is not None:
            st.info(f"Last research run: {st.session_state['research_time']:.2f} s")

    # Display research output (readable text in expanders)
    if st.session_state.get("research_text"):
        # Attempt to split into the three labeled sections. If the model used exact headings, split by them; otherwise, fallback to whole text.
        text = st.session_state["research_text"]
        # Try to locate headings
        sections = {"Core Thesis:": "", "Key Arguments:": "", "Controversies & Debates:": ""}
        # naive split: find indices
        idx_core = text.find("Core Thesis:")
        idx_key = text.find("Key Arguments:")
        idx_cont = text.find("Controversies & Debates:")
        if idx_core != -1 and idx_key != -1:
            sections["Core Thesis:"] = text[idx_core + len("Core Thesis:"): idx_key].strip()
            if idx_cont != -1:
                sections["Key Arguments:"] = text[idx_key + len("Key Arguments:"): idx_cont].strip()
                sections["Controversies & Debates:"] = text[idx_cont + len("Controversies & Debates:"):].strip()
            else:
                sections["Key Arguments:"] = text[idx_key + len("Key Arguments:"):].strip()
        else:
            # fallback: put entire text under Core Thesis expander
            sections["Core Thesis:"] = text

        with st.expander("Core Thesis", expanded=True):
            st.markdown(sections["Core Thesis:"] or "No content returned.")

        with st.expander("Key Arguments & Supporting Points", expanded=False):
            st.markdown(sections["Key Arguments:"] or "No content returned.")

        with st.expander("Controversies & Debates", expanded=False):
            st.markdown(sections["Controversies & Debates:"] or "No content returned.")

else:
    st.info("No validated metadata yet. Fetch canonical metadata first (left).")
