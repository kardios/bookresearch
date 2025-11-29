# 📚 Readhacker: Book Metadata + Research

A Streamlit application that fetches canonical book metadata and performs in-depth research using OpenAI's GPT-5 models with web search capabilities.

## Features

- **Canonical Metadata Extraction**: Automatically fetches verified book metadata including:
  - Original and English titles
  - Authors with full names
  - Original language
  - Publication date
  - Source URLs

- **In-Depth Research**: Performs comprehensive book analysis covering:
  - Core Thesis
  - Key Arguments
  - Controversies
  - Counter-Intuitive Insights

- **Robust Implementation**:
  - Input sanitization to prevent prompt injection
  - Automatic retry logic for API calls (3 retries with exponential backoff)
  - Session state persistence (results survive page refreshes)
  - JSON schema validation
  - Comprehensive error handling with helpful messages

- **Flexible Configuration**:
  - Multiple GPT-5 model options (nano, mini, standard, pro)
  - Adjustable reasoning effort (low, medium, high)
  - Download results as JSON

## Prerequisites

- Python 3.8 or higher
- OpenAI API key with access to GPT-5 models

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd bookresearch
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your API key**:

   Create a `.env` file in the project root:
   ```bash
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```

   Or export it directly:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```

## Usage

1. **Run the application**:
   ```bash
   streamlit run app.py
   ```

2. **Access the web interface**:
   - The app will automatically open in your browser
   - Default URL: `http://localhost:8501`

3. **Use the application**:
   - Enter a book title (required)
   - Optionally specify the author
   - Choose the research model and reasoning effort
   - Click "Fetch Metadata & Research"
   - Download results as JSON if needed

## Project Structure

```
bookresearch/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── .gitignore         # Git ignore rules
└── archive/           # Previous versions of the app
    ├── app1.py
    ├── app2.py
    └── app3.py
```

## Configuration

### Model Options

- **gpt-5-nano**: Fastest, most cost-effective
- **gpt-5-mini**: Good balance of speed and quality
- **gpt-5**: Standard model with high quality
- **gpt-5-pro**: Highest quality, slower (default for research)

### Reasoning Effort

- **low**: Faster responses, less detailed reasoning
- **medium**: Balanced (default)
- **high**: Slower, more thorough reasoning

## Security Features

- **Input Sanitization**: All user inputs are sanitized to prevent prompt injection attacks
- **Environment Variables**: API keys are loaded from environment variables, never hardcoded
- **Error Handling**: Comprehensive error messages without exposing sensitive information
- **Schema Validation**: JSON schema validation ensures data integrity

## Error Handling

The application includes robust error handling with helpful messages:

- **API Errors**: Automatic retry (3 attempts) with exponential backoff
- **JSON Parsing Errors**: Clear error messages with raw output display
- **Validation Errors**: Detailed schema validation messages
- **Network Errors**: Helpful tips for troubleshooting

## Session State

Results are preserved in session state, so:
- Cached results survive page refreshes
- You can review previous results without re-fetching
- Download functionality works even after navigation

## Download Format

The downloaded JSON file includes:
```json
{
  "metadata": {
    "title": {...},
    "authors": [...],
    "language": "...",
    "publication_date": "...",
    "sources": [...]
  },
  "research": "...",
  "fetch_time": 2.34,
  "research_time": 15.67
}
```

## Development

### Code Structure

The application is organized into:
- **Configuration**: Schema and prompt templates
- **Helper Functions**:
  - `sanitize_input()`: Input validation and sanitization
  - `normalize_metadata()`: JSON normalization
  - `validate_metadata()`: Schema validation
  - `fetch_with_retry()`: API calls with retry logic
- **UI Layer**: Streamlit interface and user interactions

### Running Tests

Currently, the project doesn't include automated tests. For manual testing:
1. Test with various book titles and authors
2. Verify error handling with invalid inputs
3. Check network error recovery (disconnect during API call)

## Troubleshooting

### Common Issues

**"Please set the OPENAI_API_KEY environment variable"**
- Ensure your API key is set in the environment
- Check that `.env` file is in the correct location

**"Failed to fetch metadata from OpenAI"**
- Check your internet connection
- Verify your API key is valid
- Ensure you have API credits available

**"Schema validation failed"**
- This is usually non-critical; the app will proceed with caution
- The API response might have an unexpected format
- Results are still usable in most cases

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Make your changes
4. Test thoroughly
5. Commit with clear messages (`git commit -m 'Add feature X'`)
6. Push to your fork (`git push origin feature/improvement`)
7. Create a Pull Request

## License

[Specify your license here]

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [OpenAI GPT-5](https://openai.com/)
- Uses [jsonschema](https://python-jsonschema.readthedocs.io/) for validation
- Retry logic via [tenacity](https://tenacity.readthedocs.io/)

## Contact

[Add your contact information here]
