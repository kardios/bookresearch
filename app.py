import os
import json
import streamlit as st
from openai import OpenAI
from jsonschema import validate, ValidationError

# ---- Streamlit settings to reduce frontend reloads ----
st.set_page_config(page_title="📘 Readhacker — Book Metadata Extractor", layout="wide")
st.experimental_set_query_params()  # prevent old state caching issues

# ---- Initialize OpenAI client once ----
@st.experimental_singleton
def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        st.error("OPENAI_API_KEY environment variable not set.")
        st.stop()
    return OpenAI(api_key=api_key)

client = get_openai_client()

# ---- Readhacker metadata schema ----
READHACKER_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "object"},
        "authors": {"type": "array"},
        "editions": {"type": "array"},
        "languages": {"type": "array"},
        "genres": {"type": "array"},
        "sources": {"type": "array"},
    },
    "required": ["title", "authors", "editions", "languages", "genres", "sources"]
}

# ---- UI ----
st.title("📘 Readhacker — Book Metadata Extractor")
st.markdown(
    "Fetch structured, validated book metadata using GPT-5.1-mini + Web Search."
)

# Input form
with st.form("book_form"):
    book_title = st.text_input("Book title")
    author_name = st.text_input("Author (optional)")
    reasoning_effort = st.selectbox("Reasoning effort", ["none", "low", "medium", "high"], index=1)
    submitted = st.form_submit_button("Fetch Metadata")

# ---- Fetch and display ----
if submitted:
    if not book_title:
        st.warning("Please enter a book title.")
        st.stop()

    with st.spinner("Fetching metadata..."):
        try:
            response = client.responses.create(
                model="gpt-5.1-mini",
                reasoning={"effort": reasoning_effort},
                input=f"Fetch structured book metadata in JSON according to Readhacker schema for:\n"
                      f"Title: {book_title}\nAuthor: {author_name}"
            )

            metadata_text = response.output_text
            metadata_json = json.loads(metadata_text)

            # Validate JSON against schema
            try:
                validate(instance=metadata_json, schema=READHACKER_SCHEMA)
                st.success("✅ Metadata is valid according to Readhacker schema!")
            except ValidationError as e:
                st.warning(f"⚠️ Metadata JSON does not fully comply with schema: {e.message}")

            # Display raw JSON
            st.subheader("Metadata JSON")
            st.json(metadata_json)

        except Exception as e:
            st.error(f"Error fetching metadata: {e}")
