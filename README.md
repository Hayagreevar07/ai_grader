# AI Grader

An AI-powered tool to correct handwritten answer sheets by comparing them against a marking scheme using High-Performance OCR and Semantic Analysis.

## Features
- **High-Level OCR**: Uses **Google Gemini 1.5 Flash** (Vision) to accurately transcribe both printed and handwritten text. 
    - Replaces local heavy models for speed and state-of-the-art accuracy.
- **Semantic Grading**: Uses `sentence-transformers` to grade answers based on meaning, not just exact keyword matching.
- **Web Interface**: Simple Flask-based UI for uploading and viewing results.

## Installation

1. Clone the repository (if applicable) or download the files.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up Google API Key**:
   You need a Google API Key (free via [Google AI Studio](https://aistudio.google.com/)).
   
   **Linux/Mac**:
   ```bash
   export GOOGLE_API_KEY="your_api_key_here"
   ```
   **Windows (PowerShell)**:
   ```powershell
   $env:GOOGLE_API_KEY="your_api_key_here"
   ```

## Usage

### Web App (Recommended)
Run the Flask web application:
```bash
python app.py
```
Visit `http://localhost:7860` in your browser.

### Command Line
Run the `main.py` script:
```bash
python main.py --question_paper "path/to/qp.jpg" --answer_sheet "path/to/answer.jpg" --expected_answer "Paris is the capital of France"
```

## How it Works
1. The **Question Paper** and **Answer Sheet** are sent to **Google Gemini 1.5 Flash**, a multimodal AI model that excels at reading text (including handwriting).
2. The extracted student answer is compared against the expected answer using a semantic similarity model (SBERT).
3. A similarity score is generated, and a pass/fail grade is assigned.

## Models Used
- **OCR**: Google Gemini 1.5 Flash (via Google GenAI SDK)
- **NLP**: all-MiniLM-L6-v2 (Sentence Transformers)
