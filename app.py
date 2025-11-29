import streamlit as st
import os
import json
import time
from openai import OpenAI
from jsonschema import validate, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Dict, Tuple, Optional

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
# PROMPT TEMPLATES
# ------------------------
METADATA_PROMPT_TEMPLATE = """
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

RESEARCH_PROMPT_TEMPLATE = """
Using the canonical metadata below, analyze the book and return a structured text report.

Canonical Metadata:
{metadata_json}

Research Areas:
1. Core Thesis
2. Key Arguments
3. Controversies
4. Counter-Intuitive Insights

Return plain text, readable summaries under each heading.
Do not include JSON.
"""

# ------------------------
# HELPER FUNCTIONS
# ------------------------

def sanitize_input(text: str, max_length: int = 200) -> str:
    """
    Sanitize user input to prevent prompt injection and ensure safe processing.

    Args:
        text: The input text to sanitize
        max_length: Maximum allowed length for the input

    Returns:
        Sanitized text string
    """
    if not text:
        return ""
    # Remove control characters, keep only printable characters
    text = ''.join(char for char in text if char.isprintable())
    # Limit length to prevent excessive API usage
    return text[:max_length].strip()


def normalize_metadata(metadata_json: Dict) -> Dict:
    """
    Normalize metadata JSON to ensure it matches the schema requirements.

    Args:
        metadata_json: Raw metadata dictionary from API

    Returns:
        Normalized metadata dictionary
    """
    # Normalize title.english to array
    if isinstance(metadata_json.get("title", {}).get("english"), str):
        metadata_json["title"]["english"] = [metadata_json["title"]["english"]]

    # Normalize authors and sources to arrays
    for key in ["authors", "sources"]:
        value = metadata_json.get(key, [])
        if isinstance(value, dict):
            metadata_json[key] = [value]
        elif isinstance(value, str):
            metadata_json[key] = [value]
        elif not isinstance(value, list):
            metadata_json[key] = []

    return metadata_json


def validate_metadata(metadata_json: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate metadata against the schema.

    Args:
        metadata_json: Metadata dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        validate(instance=metadata_json, schema=BOOK_SCHEMA)
        return True, None
    except ValidationError as ve:
        return False, ve.message


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_with_retry(client, model: str, tools: list, reasoning: dict, input_text: str):
    """
    Fetch response from OpenAI API with automatic retry logic.

    Args:
        client: OpenAI client instance
        model: Model name to use
        tools: List of tools to enable
        reasoning: Reasoning configuration
        input_text: Prompt text

    Returns:
        API response object
    """
    return client.responses.create(
        model=model,
        tools=tools,
        reasoning=reasoning,
        tool_choice="auto",
        input=input_text
    )

# ------------------------
# Streamlit UI
# ------------------------
st.set_page_config(page_title="Readhacker Book Research", page_icon="📚")
st.title("📚 Readhacker: Book Metadata + Research")

# Initialize session state
if "metadata_json" not in st.session_state:
    st.session_state.metadata_json = None
if "metadata_fetch_time" not in st.session_state:
    st.session_state.metadata_fetch_time = None
if "research_output" not in st.session_state:
    st.session_state.research_output = None
if "research_time" not in st.session_state:
    st.session_state.research_time = None

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
        st.warning("⚠️ Please enter a book title.")
        st.stop()

    # Sanitize inputs
    sanitized_title = sanitize_input(book_title)
    sanitized_author = sanitize_input(book_author)

    if not sanitized_title:
        st.error("❌ Invalid book title after sanitization.")
        st.stop()

    # -----------------------------
    # Canonical Metadata fetch
    # -----------------------------
    start_time = time.time()
    with st.spinner("Fetching canonical metadata..."):

        metadata_prompt = METADATA_PROMPT_TEMPLATE.format(
            book_title=sanitized_title,
            book_author=sanitized_author
        )

        try:
            metadata_resp = fetch_with_retry(
                client=client,
                model="gpt-5-nano",
                tools=[{"type": "web_search"}],
                reasoning={"effort": "low"},
                input_text=metadata_prompt
            )
            metadata_output = metadata_resp.output_text
        except Exception as e:
            st.error("❌ Failed to fetch metadata from OpenAI.")
            st.error(f"Error details: {str(e)}")
            st.info("💡 Tip: Check your internet connection and API key. The request was retried 3 times.")
            st.stop()

    fetch_time = time.time() - start_time
    st.session_state.metadata_fetch_time = fetch_time
    st.info(f"✅ Metadata fetch completed in {fetch_time:.2f} seconds")

    # -----------------------------
    # Parse & normalize metadata JSON
    # -----------------------------
    try:
        metadata_json = json.loads(metadata_output)
    except json.JSONDecodeError as e:
        st.error("❌ Metadata output is not valid JSON.")
        st.error(f"Error details: {str(e)}")
        st.code(metadata_output, language="text")
        st.stop()

    # Normalize metadata
    metadata_json = normalize_metadata(metadata_json)

    # Validate JSON
    is_valid, error_message = validate_metadata(metadata_json)
    if not is_valid:
        st.error(f"❌ Schema validation failed: {error_message}")
        st.warning("The metadata doesn't fully comply with the expected schema. Proceeding with caution.")
    else:
        st.success("✅ Canonical metadata is valid!")

    # Store in session state
    st.session_state.metadata_json = metadata_json

    # -----------------------------
    # Display metadata in text
    # -----------------------------
    with st.expander("Canonical Metadata (Text)", expanded=True):
        st.text(f"Title (Original): {metadata_json['title'].get('original','')}")
        st.text(f"Title (English): {', '.join(metadata_json['title'].get('english',[]))}")
        authors_list = [a['full_name'] for a in metadata_json.get("authors",[])]
        st.text(f"Authors: {', '.join(authors_list)}")
        st.text(f"Language: {metadata_json.get('language','')}")
        st.text(f"Publication Date: {metadata_json.get('publication_date','')}")
        sources = metadata_json.get("sources",[])
        st.text(f"Sources: {', '.join(sources)}")

    # -----------------------------
    # Research Step
    # -----------------------------
    research_prompt = RESEARCH_PROMPT_TEMPLATE.format(
        metadata_json=json.dumps(metadata_json, indent=2)
    )

    research_start = time.time()
    with st.spinner(f"Running research with {model_choice}..."):
        try:
            research_resp = fetch_with_retry(
                client=client,
                model=model_choice,
                tools=[{"type": "web_search"}],
                reasoning={"effort": reasoning_effort},
                input_text=research_prompt
            )
            research_output = research_resp.output_text
        except Exception as e:
            st.error("❌ Research step failed.")
            st.error(f"Error details: {str(e)}")
            st.info("💡 Tip: Try selecting a different model or reducing the reasoning effort. The request was retried 3 times.")
            st.stop()

    research_time = time.time() - research_start
    st.session_state.research_output = research_output
    st.session_state.research_time = research_time
    st.info(f"✅ Research completed in {research_time:.2f} seconds")

    # -----------------------------
    # Display research output
    # -----------------------------
    with st.expander("Book Research", expanded=True):
        st.markdown(research_output)

# -----------------------------
# Display cached results if available
# -----------------------------
if st.session_state.metadata_json and not st.button("Fetch Metadata & Research"):
    st.divider()
    st.subheader("📝 Cached Results")

    with st.expander("Canonical Metadata (Text)", expanded=False):
        metadata_json = st.session_state.metadata_json
        st.text(f"Title (Original): {metadata_json['title'].get('original','')}")
        st.text(f"Title (English): {', '.join(metadata_json['title'].get('english',[]))}")
        authors_list = [a['full_name'] for a in metadata_json.get("authors",[])]
        st.text(f"Authors: {', '.join(authors_list)}")
        st.text(f"Language: {metadata_json.get('language','')}")
        st.text(f"Publication Date: {metadata_json.get('publication_date','')}")
        sources = metadata_json.get("sources",[])
        st.text(f"Sources: {', '.join(sources)}")

    if st.session_state.research_output:
        with st.expander("Book Research", expanded=False):
            st.markdown(st.session_state.research_output)

# -----------------------------
# Download JSON (if results exist)
# -----------------------------
if st.session_state.metadata_json:
    download_data = {
        "metadata": st.session_state.metadata_json,
        "research": st.session_state.research_output or "Not yet generated",
        "fetch_time": st.session_state.metadata_fetch_time,
        "research_time": st.session_state.research_time
    }
    st.download_button(
        "📥 Download Canonical Metadata + Research",
        data=json.dumps(download_data, indent=2),
        file_name="book_research.json",
        mime="application/json",
    )
