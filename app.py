# ===============================
# Remove proxy variables FIRST
# ===============================
import os

for key in [
    "HTTP_PROXY", "HTTPS_PROXY",
    "http_proxy", "https_proxy",
    "ALL_PROXY", "all_proxy"
]:
    os.environ.pop(key, None)

# ===============================
# Imports AFTER cleaning proxies
# ===============================
import streamlit as st
import json
from jsonschema import validate, ValidationError
from openai import OpenAI
import time

# ===============================
# Initialize OpenAI client
# ===============================
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ===============================
# Readhacker metadata schema
# ===============================
READHACKER_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "object",
            "properties": {
                "original": {"type": "string"},
                "english": {"type": "string"}
            },
            "required": ["original"]
        },
        "authors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "background": {"type": "string"}
                },
                "required": ["full_name"]
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
                "required": ["edition_version"]
            }
        },
        "languages": {"type": "array", "items": {"type": "string"}},
        "genres": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["title", "authors", "editions", "languages", "genres", "sources"]
}

# ===============================
# Streamlit App UI
# ===============================
st.title("📘 Readhacker — Book Metadata Extractor")

st.write("Fetch structured, validated book metadata using GPT-5.1-mini + Web Search.")

book_title = st.text_input("Book Title")
author_name = st.text_input("Author Name (optional)")

reasoning_effort = st.selectbox(
    "Reasoning Effort",
    ["none", "low", "medium", "high"],
    index=0
)

if st.button("Fetch Metadata"):
    if not book_title:
        st.error("Please enter a book title.")
        st.stop()

    with st.spinner("Querying GPT-5.1-mini with Web Search..."):
        start = time.time()

        try:
            # Construct query
            user_query = (
                f"Book title: {book_title}\n"
                f"Author (optional): {author_name or 'N/A'}\n\n"
                "Return metadata compliant with this schema:\n"
                f"{json.dumps(READHACKER_SCHEMA, indent=2)}"
            )

            # Call GPT-5.1-mini with web search enabled
            response = client.chat.completions.create(
                model="gpt-5.1-mini",
                reasoning={"effort": reasoning_effort},
                temperature=0,
                messages=[
                    {"role": "system", "content": "Extract structured book metadata."},
                    {"role": "user", "content": user_query}
                ],
                web_search={"enabled": True}
            )

            raw_output = response.choices[0].message["content"]

            # Parse JSON
            metadata = json.loads(raw_output)

            # Validate JSON against schema
            try:
                validate(instance=metadata, schema=READHACKER_SCHEMA)
                st.success("Metadata is valid according to the Readhacker schema!")
            except ValidationError as ve:
                st.error("Metadata does NOT comply with schema.")
                st.write(str(ve))

            # Display formatted JSON
            st.subheader("📄 Extracted Metadata")
            st.json(metadata)

        except Exception as e:
            st.error(f"Error fetching metadata: {e}")

        end = time.time()
        st.write(f"⏱️ Fetch completed in **{end - start:.2f} seconds**")
