# Lazy import in __init__
import sys
import os
import json
import requests
from dotenv import load_dotenv

# Load env if available
load_dotenv()

class Grader:
    def __init__(self, model_name='nvidia/nemotron-nano-12b-v2-vl:free'):
        self.model_name = model_name
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.site_url = os.environ.get("SITE_URL", "http://localhost")
        self.app_name = os.environ.get("APP_NAME", "AI Grader")
        
        if not self.api_key:
            print("WARNING: OPENROUTER_API_KEY environment variable is not set. Grading will fail.")
        else:
            print(f"Grader initialized with OpenRouter ({self.model_name}).")

    def _load_model(self):
        pass

    def grade_answer(self, student_answer, key_answer, threshold=0.5):
        """
        Compares the student's answer with the key answer using OpenRouter LLM.
        """
        if not self.api_key:
             return {
                "student_answer": student_answer,
                "key_answer": key_answer,
                "similarity_score": 0.0,
                "is_correct": False,
                "error": "Missing OPENROUTER_API_KEY"
            }

        try:
            # Construct a prompt for semantic grading
            system_prompt = "You are a strict but fair teacher grading a student's handwritten answer."
            user_prompt = f"""
            Target Key Answer: "{key_answer}"
            Student Answer: "{student_answer}"
            
            Task:
            1. Compare the MEANING of the Student Answer to the Key Answer.
            2. Ignore minor spelling/grammar mistakes.
            3. CRITICAL: Check if the Final Answer/Conclusion is present and logically matches the Key's final outcome. If the final answer is missing or incorrect, deduct significant marks (maximum score should be 0.6).
            4. If the core steps and meaning match perfectly or very closely, give a high score (0.8 - 1.0).
            5. Provide a Raw Score between 0.0 and 1.0.
            
            Output format: JSON object ONLY. Do not use markdown blocks.
            {{
                "score": <float 0.0-1.0>,
                "feedback": "<detailed 2-3 sentence explanation of what they got right, wrong, and if the final answer was present>"
            }}
            """

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": self.site_url,
                "X-Title": self.app_name,
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"OpenRouter Error: {response.text}")
                return {
                    "student_answer": student_answer,
                    "key_answer": key_answer,
                    "similarity_score": 0.0,
                    "is_correct": False,
                    "error": f"API Error {response.status_code}: {response.text}",
                    "reasoning": "Failed to connect to AI engine."
                }

            resp_json = response.json()
            if 'choices' not in resp_json or len(resp_json['choices']) == 0:
                 return {
                    "student_answer": student_answer,
                    "key_answer": key_answer,
                    "similarity_score": 0.0,
                    "is_correct": False,
                    "error": "Empty choices in API response",
                    "reasoning": "AI Engine returned no data."
                }

            content = resp_json['choices'][0]['message']['content']
            
            # Clean content just in case
            content = content.replace('```json', '').replace('```', '').strip()
            
            try:
                result_data = json.loads(content)
                raw_score = float(result_data.get("score", 0.0))
                feedback = result_data.get("feedback", "No detailed feedback provided.")
            except json.JSONDecodeError:
                print(f"JSON Parse Error. Raw: {content}")
                raw_score = 0.0
                feedback = "Failed to parse AI response."

            # NEW: Realistic Rules
            # 1. 80% Rule (If 0.8 or above, award full 1.0 marks)
            if raw_score >= 0.80:
                final_score = 1.0
            else:
                final_score = raw_score

            is_correct = final_score >= threshold
            
            return {
                "student_answer": student_answer,
                "key_answer": key_answer,
                "similarity_score": round(final_score, 4),
                "accuracy_raw": round(raw_score, 4),
                "is_correct": is_correct,
                "reasoning": feedback
            }

        except Exception as e:
            print(f"Exception during grading: {e}")
            return {
                "student_answer": student_answer, 
                "key_answer": key_answer,
                "similarity_score": 0.0,
                "is_correct": False,
                "error": str(e),
                "reasoning": "System Exception occurred."
            }

if __name__ == "__main__":
    grader = Grader()
    print("--- Test 1: Match ---")
    res1 = grader.grade_answer("Paris is the capital city of France", "The capital of France is Paris")
    print(f"Score: {res1.get('similarity_score')}")
    print(f"Reasoning: {res1.get('reasoning')}")
    
    print("\n--- Test 2: Wrong ---")
    res2 = grader.grade_answer("London is the capital of France", "The capital of France is Paris")
    print(f"Score: {res2.get('similarity_score')}")
    print(f"Reasoning: {res2.get('reasoning')}")
