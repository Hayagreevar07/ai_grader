---
title: AI Grader
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
---

# AI Grader 🚀

[![Sync to Hugging Face](https://github.com/Hayagreevar/ai_grader/actions/workflows/sync.yml/badge.svg)](https://github.com/Hayagreevar/ai_grader/actions/workflows/sync.yml)


An AI-powered tool to correct handwritten answer sheets by comparing them against a marking scheme using High-Performance OCR and Semantic Analysis.

## Features
- **High-Level OCR**: Uses **Google Gemini 1.5 Flash** (Vision) to accurately transcribe both printed and handwritten text. 
- **Premium UI**: Modern, glassmorphism-based design with smooth animations.
- **Role-Based Access**:
    - **Staff/Admin**: Secure login to upload and grade papers.
    - **Student Portal**: Public access for students to check results using their Register Number.
- **Semantic Grading**: Uses `sentence-transformers` for meaning-based evaluation.

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up Environment Variables**:
   You need the following secrets (set them in your `.env` or Cloud Settings):
   
   - `GOOGLE_API_KEY`: Your Gemini API Key.
   - `ADMIN_PASSWORD`: Logic for staff login (default: `admin123`).
   - `ALLOWED_EMAILS`: Comma-separated list of authorized emails (default: `admin@example.com`).

   **Windows (PowerShell)**:
   ```powershell
   $env:GOOGLE_API_KEY="your_key"
   $env:ADMIN_PASSWORD="secure_pass"
   $env:ALLOWED_EMAILS="you@domain.com,admin@domain.com"
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

## 🔥 Firebase Database Setup (Optional)
To save grading results, you need a Firebase Firestore database.

1.  **Create Project:** Go to [Firebase Console](https://console.firebase.google.com/) and create a new project.
2.  **Create Database:** Go to `Build > Firestore Database` and click **Create Database**. Select **Test Mode** for setup.
3.  **Get Credentials:**
    *   Go to `Project Settings` (Gear icon) > `Service accounts`.
    *   Click **Generate new private key**.
    *   This downloads a `.json` file (`serviceAccountKey.json`).
4.  **Connect to App:**
    *   **On Hugging Face:** Open the `.json` file, copy ALL text. Go to Space Settings > Secrets. Create a secret named `FIREBASE_CREDENTIALS` and paste the text.
    *   **Locally:** Rename the file to `serviceAccountKey.json` and place it in the project root.
