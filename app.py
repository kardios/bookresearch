import streamlit as st
import json
import time
import os
from openai import OpenAI
from jsonschema import validate, ValidationError

# Initialize client (no proxies argument)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Readhacker metadata schema
READHACKER_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "object",
            "properties": {
                "original": {"type": "string"},
                "english": {"type": "string"}
            },
            "required": ["original", "english"]
        },
        "authors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "background": {"type": "string"}
                },
                "required": ["full_name", "background"]
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
                },
                "required": ["edition_version", "publication_date", "language"]
            }
        },
        "languages": {"type": "array", "items": {"type": "string"}},
        "genres": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["title", "authors", "editions", "languages", "genres", "sources"]
}

# Reasoning effort toggle
REASONING_MAP = {
    "none": "none",
    "low": "low",
    "medium": "medium",
    "high": "high"
}

st.title("📚 Readhacker – Book Metadata Extractor")

# Inputs
title = st.text_input("Book Title:")
author = st.text_input("Author (optional):")

# Construct query
query = title if not author.strip() else f"{title} by {author}"

effort = st.selectbox("Reasoning effort:", ["none", "low", "medium", "high"], index=0)

if st.button("Fetch Metadata"):
    if not title.strip():
        st.error("Please enter a book title.")
        st.stop()

    st.write("🔎 Fetching metadata…")
    start_time = time.time()

    system_prompt = """
You are a metadata extraction assistant for a project called Readhacker.
Your job is to search the web (via your built-in search tools) and return clean,
accurate metadata about the book specified by the user.

Return ONLY JSON matching this schema:

{
  "title": {
    "original": "...",
    "english": "..."
  },
  "authors": [
    {
      "full_name": "...",
      "background": "..."
    }
  ],
  "editions": [
    {
      "edition_version": "...",
      "publication_date": "YYYY-MM-DD",
      "language": "..."
    }
  ],
  "languages": ["..."],
  "genres": ["..."],
  "sources": ["url1", "url2"]
}

Rules:
- All URLs must be real and verifiable.
- If a detail is uncertain, omit it rather than guessing.
- Always include multiple editions when they exist.
- Ensure the metadata corresponds *specifically* to the exact book identified by the given title and author.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            reasoning={"effort": REASONING_MAP[effort]},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Book query: {query}"}
            ],
            temperature=0.1,
        )

        output = response.choices[0].message["content"]

        # Parse JSON
        try:
            metadata = json.loads(output)
        except json.JSONDecodeError:
            st.error("❌ Model returned invalid JSON.")
            st.code(output)
            st.stop()

        # Validate schema
        try:
            validate(instance=metadata, schema=READHACKER_SCHEMA)
            valid = True
        except ValidationError as e:
            valid = False
            st.error(f"⚠️ Metadata does NOT match schema:\n\n{e.message}")

        # Show result
        st.subheader("📄 Extracted Metadata (Raw JSON)")
        st.code(json.dumps(metadata, indent=2), language="json")

        elapsed = time.time() - start_time
        st.write(f"⏱️ Completed in **{elapsed:.2f} seconds**")

    except Exception as e:
        st.error(f"Error fetching metadata: {str(e)}")
