import os
import requests
import base64
import json
from dotenv import load_dotenv

# Load env variables
load_dotenv()

class OCREngine:
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.site_url = os.environ.get("SITE_URL", "http://localhost")
        self.app_name = os.environ.get("APP_NAME", "AI Grader")
        
        if not self.api_key:
            print("WARNING: OPENROUTER_API_KEY environment variable is not set. OCR will fail.")
        else:
            print("OCR Engine initialized with OpenRouter.")
            
        # Default Vision Model (Free Tier)
        self.model_name = "nvidia/nemotron-nano-12b-v2-vl:free"

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def process_image(self, image_path, model_type="handwritten"):
        """
        Performs OCR on an image using OpenRouter Vision Models.
        """
        if not self.api_key:
            return "Error: OPENROUTER_API_KEY not configured."

        if not os.path.exists(image_path):
             return f"Error: Image file not found at {image_path}"

        try:
            # Prepare Image
            base64_image = self.encode_image(image_path)
            
            # Craft the prompt
            if model_type == "handwritten":
                text_prompt = "Transcribe the handwritten text in this image exactly as it appears. output only the text."
            else:
                text_prompt = "Transcribe the printed text in this image exactly as it appears. output only the text."

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": self.site_url,
                "X-Title": self.app_name,
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": text_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
            }

            print(f"DEBUG: sending OCR request to OpenRouter ({self.model_name})...")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=60
            )

            if response.status_code != 200:
                print(f"OCR API Error: {response.text}")
                return f"Error: API returned {response.status_code} - {response.text}"

            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                extracted_text = result['choices'][0]['message']['content']
                print("SUCCESS: OCR text extracted.")
                return extracted_text.strip()
            else:
                print(f"WARNING: Unexpected API response structure: {result}")
                return "Error: No content in API response."

        except Exception as e:
            error_msg = str(e)
            print(f"OCR Exception: {error_msg}")
            return f"Error executing OCR: {error_msg}"

if __name__ == "__main__":
    # Test block
    ocr = OCREngine()
    # Need a real image to test; can't test without one.
    print("OCR Engine Ready (OpenRouter). Run app to test.")
