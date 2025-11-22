import streamlit as st
import os
import json
import time
from openai import OpenAI

# Load API key from environment variable
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

st.set_page_config(page_title="Readhacker Metadata Finder", page_icon="📚")
st.title("📚 Readhacker: Book Metadata Finder")
st.markdown(
    "Enter a book title (and optionally author) to fetch canonical metadata using GPT-5 with web search."
)

# User input
book_title = st.text_input("Book Title")
book_author = st.text_input("Author (Optional)")

if st.button("Fetch Metadata"):
    if not book_title.strip():
        st.warning("Please enter a book title.")
    else:
        start_time = time.time()
        with st.spinner("Fetching metadata..."):
            prompt = f"""
            You are a research assistant with web access. Given the book title '{book_title}' and author '{book_author}', 
            provide canonical metadata for the book in strict JSON format with the following fields:
            - title (original and English if available)
            - author (full name, notable positions or background)
            - publication_date
            - edition/version
            - ISBN or other identifiers
            - language
            - genre/category
            - other_identifiers (translator, series, publisher, etc.)
            Only include info relevant to the correct book. Do not hallucinate.
            """

            try:
                response = client.responses.create(
                    model="gpt-5",
                    tools=[{"type": "web_search"}],
                    reasoning={"effort": "low"},  # faster response
                    tool_choice="auto",
                    input=prompt
                )

                metadata_output = response.output_text
                elapsed = time.time() - start_time

                st.subheader("Metadata JSON")
                st.code(metadata_output, language="json")
                st.info(f"Fetch completed in {elapsed:.2f} seconds")

                # Optionally, validate JSON
                try:
                    metadata_json = json.loads(metadata_output)
                    st.success("Valid JSON detected.")
                except:
                    st.warning("Output may not be valid JSON.")

            except Exception as e:
                st.error(f"Error fetching metadata: {e}")
