import streamlit as st
import os
import json
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
allowed_domains = st.text_area("Optional Allowed Domains (comma-separated)")

if st.button("Fetch Metadata"):
    if not book_title.strip():
        st.warning("Please enter a book title.")
    else:
        with st.spinner("Fetching metadata..."):
            domains_list = [d.strip() for d in allowed_domains.split(",") if d.strip()]
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
                tools_config = [{"type": "web_search"}]
                if domains_list:
                    tools_config[0]["filters"] = {"allowed_domains": domains_list}

                response = client.responses.create(
                    model="gpt-5",
                    tools=tools_config,
                    tool_choice="auto",
                    input=prompt
                )

                metadata_output = response.output_text
                st.subheader("Metadata JSON")
                st.code(metadata_output, language="json")

                # Optionally, validate JSON
                try:
                    metadata_json = json.loads(metadata_output)
                    st.success("Valid JSON detected.")
                except:
                    st.warning("Output may not be valid JSON.")

            except Exception as e:
                st.error(f"Error fetching metadata: {e}")
