# AI Grader

An AI-powered tool to correct handwritten answer sheets by comparing them against a marking scheme using High-Performance OCR.

## Features
- **Printed Text OCR**: Uses `microsoft/trocr-base-printed` to digest question papers.
- **Handwritten Text OCR**: Uses `microsoft/trocr-base-handwritten` to read student answers.
- **Semantic Grading**: Uses `sentence-transformers` to grade answers based on meaning, not just exact keyword matching.

## Installation

1. Clone the repository (if applicable) or download the files.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the `main.py` script with the paths to your images and the expected answer.

```bash
python main.py --question_paper "path/to/qp.jpg" --answer_sheet "path/to/answer.jpg" --expected_answer "Paris is the capital of France"
```

## How it Works
1. The **Question Paper** is processed using a Transformer-based OCR model optimized for printed text.
2. The **Answer Sheet** is processed using a Transformer-based OCR model optimized for handwriting.
3. The extracted student answer is compared against the expected answer using a semantic similarity model (SBERT).
4. A similarity score is generated, and a pass/fail grade is assigned.

## Models Used
- OCR: Microsoft TrOCR (Transformer OCR)
- NLP: all-MiniLM-L6-v2 (Sentence Transformers)
