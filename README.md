<div align="center">
  <img src="https://img.shields.io/badge/AI-Grader-4f46e5?style=for-the-badge&logo=flask&logoColor=white" alt="AI Grader Banner">
  <h1>✨ AI Grader ✨</h1>
  <p><strong>An Intelligent OCR-based Answer Sheet Correction System</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white" alt="Flask">
    <img src="https://img.shields.io/badge/Pytesseract-4f46e5?style=flat-square&logo=google&logoColor=white" alt="OCR">
    <img src="https://img.shields.io/badge/Gemini_1.5_Flash-FFaa00?style=flat-square&logo=google&logoColor=white" alt="Gemini">
    <img src="https://img.shields.io/badge/Firebase-FFA611?style=flat-square&logo=firebase&logoColor=black" alt="Firebase">
  </p>
</div>

---

## 🚀 About The Project

**AI Grader** is an automated system designed to ease the burden of grading handwritten answer sheets. Using advanced **OCR (Optical Character Recognition)** and **Large Language Models (LLMs)**, it extracts handwritten text and intelligently compares it against expected answer keys, highlighting differences, and giving an estimated accuracy score.

It comes packed with a beautiful UI featuring a dashboard for staff to bulk-upload answer sheets, export lists, and email results directly to students.

### ✨ Features
- 📝 **OCR Extraction:** Uses `pytesseract` to read handwritten answer sheets.
- 🧠 **AI Grading:** Compares extracted student answers to expected answer keys using OpenRouter / Google Gemini models.
- 💾 **Data Storage:** Saves results securely to Firestore (with local mock fallback).
- 🧑‍💻 **Staff Dashboard:** Drag-and-drop or manual entry for bulk grading.
- 📊 **Results Management:** View the entire class list, search, filter, and export as CSV!
- 📧 **Email Functionality:** Direct emailing of grades and report cards to students/staff.
- 🗣️ **Voice AI Setup:** Added hooks for text-to-speech feedback.

---

## 🛠️ Prerequisites & Installation

### 1. Requirements
- Python 3.9+
- Tesseract OCR engine installed on your system.
  - **Windows:** Download from [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).
  - **Linux:** `sudo apt install tesseract-ocr`
  - **Mac:** `brew install tesseract`

### 2. Setup Guide

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/ai_grader-main.git
   cd ai_grader-main
   ```

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables Configuration:**
   Create a `.env` file in the root directory (using the variables shown below).

   ```env
   # LLM Config
   OPENROUTER_API_KEY=your_openrouter_api_key
   
   # App Details
   SITE_URL=http://localhost:7860
   APP_NAME=AI_Grader
   
   # Flask Session Security (Optional but recommended)
   SECRET_KEY=super_secret_session_key
   
   # Admin Access
   ADMIN_PASSWORD=admin123
   ALLOWED_EMAILS=teacher1@college.edu,admin@college.edu
   
   # Email Config (For sending Email reports)
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   ```

---

## 💻 Usage

Start the web application locally on port 7860:

```bash
python app.py
```

### Endpoints / Workflow:
1. **Login:** Navigate to `http://localhost:7860/login` with your configured email and admin password.
2. **Dashboard:** Go to `http://localhost:7860/upload` to Create Exams or Upload student papers.
3. **All Results List & Report:** Navigate to `http://localhost:7860/all_results` to view the comprehensive list, search for students, download CSVs, and trigger Email report cards.
4. **Student Portal:** Students can search for their grades at `http://localhost:7860/student` using their Roll No.

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

<div align="center">
  <sub>Built with ❤️ by AI Enthusiasts</sub>
</div>
