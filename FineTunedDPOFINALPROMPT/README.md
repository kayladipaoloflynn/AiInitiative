# Flynn Construction Handover Analysis

A Python tool for analyzing construction handover transcripts using OpenAI's fine-tuned GPT-4 model.

## Features

- Supports both .txt and .docx transcript files
- Processes multiple questions against transcripts
- Generates structured Word document reports
- Uses Flynn's custom fine-tuned model: `ft:gpt-4o-2024-08-06:flynn:test-nine:BcuSbEPv`

## Requirements

- Python 3.8+
- OpenAI API key
- Required packages (see requirements.txt)

## Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set your OpenAI API key as an environment variable: `OPENAI_API_KEY`

## Usage

1. Update the file paths in the `quick_run()` function
2. Run: `python DPOFINALPROMPT.py`

## Output

The tool generates a Word document with:
- Expert interpretation of findings
- Supporting quotes from the transcript
- Professional summary with gaps and next steps
