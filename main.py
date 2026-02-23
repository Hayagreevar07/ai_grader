import os
import argparse
from ocr_engine import OCREngine
from grader import Grader

def main():
    parser = argparse.ArgumentParser(description="AI Grader: OCR-based Answer Sheet Corrector")
    parser.add_argument("--question_paper", required=True, help="Path to the Question Paper image")
    parser.add_argument("--answer_sheet", required=True, help="Path to the Answer Sheet image")
    parser.add_argument("--expected_answer", required=True, help="The correct answer text (or path to text file) for comparison")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.question_paper):
        print(f"Error: Question paper not found at {args.question_paper}")
        return
    if not os.path.exists(args.answer_sheet):
        print(f"Error: Answer sheet not found at {args.answer_sheet}")
        return

    print("Initializing AI Grader...")
    
    # Initialize Engines
    ocr = OCREngine()
    grader = Grader()
    
    print("\n--- Processing Question Paper (Printed) ---")
    qp_text = ocr.process_image(args.question_paper, model_type="printed")
    print(f"Extracted QP Text: {qp_text}")
    
    print("\n--- Processing Answer Sheet (Handwritten) ---")
    ans_text = ocr.process_image(args.answer_sheet, model_type="handwritten")
    print(f"Extracted Answer Text: {ans_text}")
    
    # Handle expected answer input
    expected_text = args.expected_answer
    if os.path.exists(args.expected_answer):
        with open(args.expected_answer, 'r') as f:
            expected_text = f.read().strip()
            
    print("\n--- Grading ---")
    result = grader.grade_answer(ans_text, expected_text)
    
    print(f"Student Answer (OCR): {result['student_answer']}")
    print(f"Expected Answer: {result['key_answer']}")
    print(f"Similarity Score: {result['similarity_score']}")
    print(f"Result: {'CORRECT' if result['is_correct'] else 'INCORRECT'}")

if __name__ == "__main__":
    main()
