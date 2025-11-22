import os
import json
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="📘 Readhacker — Book Metadata Extractor", layout="wide")
st.title("📘 Readhacker — Book Metadata Extractor")
st.markdown("Enter a book title and optionally an author to fetch structured book metadata in JSON.")

book_title = st.text_input("Book title")
author_name = st.text_input("Author (optional)")

if st.button("Fetch Metadata"):
    if not book_title:
        st.warning("Please enter a book title.")
    else:
        if not os.environ.get("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY environment variable not set.")
        else:
            client = OpenAI()  # <-- Do NOT pass api_key here; SDK reads from environment

            try:
                prompt = f"Return structured book metadata in JSON format for the following book:\nTitle: {book_title}"
                if author_name:
                    prompt += f"\nAuthor: {author_name}"

                response = client.responses.create(
                    model="gpt-5-mini",
                    input=prompt
                )

                metadata_text = response.output_text
                try:
                    metadata_json = json.loads(metadata_text)
                    st.subheader("Metadata JSON")
                    st.json(metadata_json)
                except json.JSONDecodeError:
                    st.error("Failed to parse JSON from model output.")
                    st.text(metadata_text)

            except Exception as e:
                st.error(f"Error fetching metadata: {e}")
