import streamlit as st
import json
import time
import os
from openai import OpenAI
from jsonschema import validate, ValidationError

# Lazy client initializer (fixes "proxies" bug)
def get_client():
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

REASONING_MAP = {
    "none": "none",
    "low": "low",
    "medium": "medium",
    "high": "high"
}

st.title("📚 Readhacker – Book Metadata Extractor")

query = st.text_input("Enter book title or keywords:")
effort = st.selectbox("Reasoning effort:", ["none", "low", "medium", "high"], index=0)

if st.button("Fetch Metadata"):
    if not query.strip():
        st.error("Please enter a book title.")
        st.stop()

    st.write("🔎 Fetching metadata…")
    start_time = time.time()

    client = get_client()   # ← FIX applied here

    system_prompt = """
You are a metadata extraction assistant for a project called Readhacker.
Your job is to search the web (through the model's web-search ability) and return clean,
accurate metadata about the book the user is referring to.

Return ONLY a JSON object following this schema:

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
- Ensure all fields are correct and tied to the specific book.
- Include multiple editions, languages, and genres if they exist.
- ALL returned URLs must be real and verifiable.
- Do NOT hallucinate publication dates.
- If unsure, leave out uncertain details instead of guessing.
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

        try:
            metadata = json.loads(output)
        except json.JSONDecodeError:
            st.error("❌ Model returned invalid JSON.")
            st.code(output)
            st.stop()

        try:
            validate(instance=metadata, schema=READHACKER_SCHEMA)
        except ValidationError as e:
            st.error(f"⚠️ Metadata does NOT match schema:\n\n{e.message}")

        st.subheader("📄 Extracted Metadata (Raw JSON)")
        st.code(json.dumps(metadata, indent=2), language="json")

        elapsed = time.time() - start_time
        st.write(f"⏱️ Completed in **{elapsed:.2f} seconds**")

    except Exception as e:
        st.error(f"Error fetching metadata: {str(e)}")
