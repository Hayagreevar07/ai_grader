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
            system_prompt = "You are an expert teacher grading a student's answer."
            user_prompt = f"""
            Target Key Answer: "{key_answer}"
            Student Answer: "{student_answer}"
            
            Task:
            1. Compare the MEANING of the Student Answer to the Key Answer.
            2. Ignore minor spelling/grammar mistakes.
            3. If the meaning matches the key, give a high score (0.8 - 1.0).
            4. If partially correct, give (0.1 - 0.7).
            5. If completely wrong, give 0.0.
            
            Output format: JSON object ONLY.
            {{
                "score": <float 0.0-1.0>,
                "reasoning": "<short text>"
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
                # Removed response_format to avoid 400 on models that don't support it
            }

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"OpenRouter Error: {response.text}")
                with open("debug_response.txt", "w", encoding="utf-8") as f:
                    f.write(f"Status: {response.status_code}\n")
                    f.write(response.text)
                return {
                    "student_answer": student_answer,
                    "key_answer": key_answer,
                    "similarity_score": 0.0,
                    "is_correct": False,
                    "error": f"API Error {response.status_code}: {response.text}"
                }

            resp_json = response.json()
            if 'choices' not in resp_json or len(resp_json['choices']) == 0:
                 print(f"Invalid API Response: {resp_json}")
                 return {
                    "student_answer": student_answer,
                    "key_answer": key_answer,
                    "similarity_score": 0.0,
                    "is_correct": False,
                    "error": "Empty choices in API response"
                }

            content = resp_json['choices'][0]['message']['content']
            
            # Write debug log
            with open("debug_response.txt", "w", encoding="utf-8") as f:
                f.write(content)

            # Clean content just in case
            content = content.replace('```json', '').replace('```', '').strip()
            
            try:
                result_data = json.loads(content)
                score = float(result_data.get("score", 0.0))
                reasoning = result_data.get("reasoning", "No reasoning.")
            except json.JSONDecodeError:
                print(f"JSON Parse Error. Raw: {content}")
                score = 0.0
                reasoning = "Parse Error"

            is_correct = score >= threshold
            
            return {
                "student_answer": student_answer,
                "key_answer": key_answer,
                "similarity_score": round(score, 4),
                "is_correct": is_correct,
                "reasoning": reasoning
            }

        except Exception as e:
            print(f"Exception during grading: {e}")
            return {
                "student_answer": student_answer, 
                "key_answer": key_answer,
                "similarity_score": 0.0,
                "is_correct": False,
                "error": str(e)
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
