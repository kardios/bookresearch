import streamlit as st
import os
import json
import time
from openai import OpenAI
from jsonschema import validate, ValidationError

# ------------------------
# CONFIG / CLIENT
# ------------------------
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()

client = OpenAI(api_key=api_key)

# ------------------------
# CONTROLLED VOCABULARIES
# ------------------------
CONTROLLED_GENRES = {
    "fiction", "nonfiction", "biography", "memoir", "history",
    "economics", "philosophy", "political science", "science & technology",
    "business", "psychology", "sociology", "literature", "classics"
}

CONTROLLED_LANGUAGES = {
    "english", "chinese", "japanese", "korean", "french", "german", "spanish",
    "italian", "portuguese", "russian", "arabic", "greek", "latin"
}

# ------------------------
# READHACKER JSON SCHEMA
# ------------------------
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

# ------------------------
# APP UI
# ------------------------
st.set_page_config(page_title="Readhacker Metadata Finder", page_icon="📚")
st.title("📚 Readhacker: Book Metadata Finder")

book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

if st.button("Fetch Metadata"):

    if not book_title.strip():
        st.warning("Please enter a book title.")
        st.stop()

    t0 = time.time()
    with st.spinner("Resolving book entity..."):

        # -----------------------------
        # 1. ENTITY CONFIRMATION STEP
        # -----------------------------
        entity_prompt = f"""
        Identify the correct book entity for:
        Title: "{book_title}"
        Author: "{book_author}"

        Return ONLY a JSON object:
        {{
            "confirmed_title": "...",
            "confirmed_author": "...",
            "notes": "Very short clarification on how the entity was matched."
        }}
        """
        try:
            entity_result = client.responses.create(
                model="gpt-5-mini",
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                input=entity_prompt
            )
            entity_json = json.loads(entity_result.output_text)
            t1 = time.time()
            time_entity = t1 - t0
            st.info(f"Entity confirmation completed in {time_entity:.2f}s")

        except Exception as e:
            st.error(f"Entity resolution failed: {e}")
            st.stop()

    # -----------------------------
    # 2. METADATA GENERATION STEP
    # -----------------------------
    with st.spinner("Fetching book metadata..."):
        metadata_prompt = f"""
        Using VERIFIED book identity:

        Title: "{entity_json['confirmed_title']}"
        Author: "{entity_json['confirmed_author']}"

        Extract canonical metadata using ONLY confirmed sources.

        Return strict JSON following this structure:
        {{
            "title": {{
                "original": "...",
                "english": ["...", "..."]
            }},
            "authors": [
                {{"full_name": "...", "background": "..."}}
            ],
            "editions": [
                {{"edition_version": "...", "publication_date": "...", "language": "..."}}
            ],
            "languages": ["..."],
            "genres": ["..."],
            "sources": ["https://..."]
        }}

        Do not include anything not supported by sources.
        """
        try:
            metadata_result = client.responses.create(
                model="gpt-5-mini",
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                input=metadata_prompt
            )
            metadata_output = metadata_result.output_text
            t2 = time.time()
            time_metadata = t2 - t1
            st.info(f"Metadata extraction completed in {time_metadata:.2f}s")

        except Exception as e:
            st.error(f"Metadata step failed: {e}")
            st.stop()

    # -----------------------------
    # Show raw JSON
    # -----------------------------
    st.subheader("Raw Metadata JSON")
    st.code(metadata_output, language="json")

    # -----------------------------
    # Parse JSON
    # -----------------------------
    try:
        metadata_json = json.loads(metadata_output)
    except json.JSONDecodeError:
        st.error("Output is not valid JSON.")
        st.stop()

    # -----------------------------
    # Auto-normalize list fields
    # -----------------------------
    if isinstance(metadata_json["title"].get("english"), str):
        metadata_json["title"]["english"] = [metadata_json["title"]["english"]]

    for key in ["languages", "genres", "authors", "editions", "sources"]:
        if isinstance(metadata_json.get(key), str):
            metadata_json[key] = [metadata_json[key]]
        if isinstance(metadata_json.get(key), dict):
            metadata_json[key] = [metadata_json[key]]

    # -----------------------------
    # HARD ENFORCEMENT: Controlled vocabularies + Other
    # -----------------------------
    normalized_genres = []
    for g in metadata_json.get("genres", []):
        g_lower = g.lower().strip()
        if g_lower in CONTROLLED_GENRES:
            normalized_genres.append(g)
        else:
            normalized_genres.append(f"Other: {g}")
    metadata_json["genres"] = normalized_genres

    normalized_languages = []
    for lang in metadata_json.get("languages", []):
        lang_lower = lang.lower().strip()
        if lang_lower in CONTROLLED_LANGUAGES:
            normalized_languages.append(lang)
        else:
            normalized_languages.append(f"Other: {lang}")
    metadata_json["languages"] = normalized_languages

    # -----------------------------
    # Validate against schema
    # -----------------------------
    try:
        validate(instance=metadata_json, schema=BOOK_SCHEMA)
        st.success("Metadata is valid and normalized!")
    except ValidationError as ve:
        st.warning(f"Schema validation issue: {ve.message}")

    # -----------------------------
    # Final output + elapsed
    # -----------------------------
    elapsed_total = time.time() - t0
    st.info(f"Total elapsed time: {elapsed_total:.2f}s")

    st.subheader("Normalized + Validated JSON")
    st.json(metadata_json)
