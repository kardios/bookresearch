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
st.title("📚 Readhacker: Metadata + Confidence Checker (GPT-5.1)")

st.markdown(
    "Fetch canonical book metadata and automatically check confidence per field "
    "by cross-referencing sources. Toggle reasoning effort to compare speed vs depth."
)

# Inputs
book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

reasoning_effort = st.selectbox(
    "Select Reasoning Effort",
    options=["none", "low", "medium", "high"],
    index=0,
    help="none = fastest, low/medium/high = progressively more reasoning and depth"
)

if st.button("Fetch Metadata + Confidence"):
    if not book_title.strip():
        st.warning("Please enter a book title.")
    else:
        start_time = time.time()
        with st.spinner(f"Fetching metadata (GPT-5.1, reasoning: {reasoning_effort})..."):
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
                # Fetch metadata
                response = client.responses.create(
                    model="gpt-5.1",
                    tools=[{"type": "web_search"}],
                    reasoning={"effort": reasoning_effort},
                    tool_choice="auto",
                    input=fetch_prompt
                )

                metadata_output = response.output_text
                elapsed = time.time() - start_time
                st.subheader("Raw Metadata JSON")
                st.code(metadata_output, language="json")
                st.info(f"Metadata fetch completed in {elapsed:.2f} seconds")

                # Parse JSON
                try:
                    metadata_json = json.loads(metadata_output)

                    # Auto-normalization
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

                    # === Confidence check ===
                    st.subheader("Confidence Check by Cross-Referencing Sources")
                    confidence_prompt = f"""
                    Given this metadata for a book:
                    {json.dumps(metadata_json, indent=2)}
                    
                    And the listed sources:
                    {json.dumps(metadata_json.get('sources', []), indent=2)}
                    
                    For each field (title, authors, editions, languages, genres), check the sources:
                    - If all sources agree, mark as VERIFIED.
                    - If there is minor discrepancy, mark as PARTIALLY VERIFIED.
                    - If sources conflict, mark as CONFLICTING.
                    
                    Return a JSON object with confidence per field, like:
                    {{
                      "title": "Verified",
                      "authors": "Partially Verified",
                      "editions": "Conflicting",
                      "languages": "Verified",
                      "genres": "Verified"
                    }}
                    """

                    confidence_resp = client.responses.create(
                        model="gpt-5.1",
                        reasoning={"effort": reasoning_effort},
                        tool_choice="auto",
                        input=confidence_prompt
                    )

                    confidence_json = json.loads(confidence_resp.output_text)

                    # === Display in color-coded table ===
                    table_data = []
                    for field in ["title", "authors", "editions", "languages", "genres"]:
                        value = metadata_json.get(field, "N/A")
                        conf = confidence_json.get(field, "Unknown")

                        # Format value
                        if isinstance(value, list):
                            display_value = ", ".join([json.dumps(v) if isinstance(v, dict) else str(v) for v in value])
                        elif isinstance(value, dict):
                            display_value = json.dumps(value)
                        else:
                            display_value = str(value)

                        # Color coding
                        if conf.lower() == "verified":
                            color = "background-color: #d4edda"  # Green
                        elif conf.lower() == "partially verified":
                            color = "background-color: #fff3cd"  # Yellow
                        elif conf.lower() == "conflicting":
                            color = "background-color: #f8d7da"  # Red
                        else:
                            color = ""

                        table_data.append({"Field": field, "Value": display_value, "Confidence": conf, "Color": color})

                    df = pd.DataFrame(table_data)

                    def highlight_confidence(row):
                        return [row["Color"]] * len(row)

                    st.dataframe(df.style.apply(highlight_confidence, axis=1).hide_columns(["Color"]))

                except json.JSONDecodeError:
                    st.error("Metadata output is not valid JSON.")
                except ValidationError as ve:
                    st.warning(f"Metadata JSON does not fully comply with schema: {ve.message}")

            except Exception as e:
                st.error(f"Error fetching metadata: {e}")
