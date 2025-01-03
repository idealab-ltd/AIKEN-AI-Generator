# PDF Question Extractor

This project extracts multiple-choice questions from PDF documents and converts them to Aiken format in Italian. It uses LLaMA 2 through Ollama for question extraction and translation.

## Features

- PDF text extraction
- Question identification and formatting using LLaMA 2
- Conversion to Aiken format
- Italian translation
- Batch processing for large documents

## Requirements

- Python 3.8+
- Ollama with LLaMA 2 model installed
- Required Python packages (see requirements.txt)

## Project Structure

- `pdf_extractor.py`: Handles PDF reading and text extraction
- `question_generator.py`: Processes text and generates questions using LLaMA 2
- `translator.py`: Handles translation to Italian
- `aiken_formatter.py`: Formats questions in Aiken format
- `main.py`: Main script to run the entire pipeline
- `utils.py`: Utility functions and helpers

## Usage

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure Ollama is running with LLaMA 2 model

3. Run the script:
```bash
python main.py path_to_your_pdf
```

## Output

The script will generate a file containing multiple-choice questions in Aiken format in Italian. Each question will have four options (a, b, c, d) with one correct answer marked.
