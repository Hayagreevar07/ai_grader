import google.generativeai as genai
from PIL import Image
import os
import time

class OCREngine:
    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            print("WARNING: GOOGLE_API_KEY environment variable is not set. OCR will fail.")
        else:
            genai.configure(api_key=self.api_key)
            print("Google Generative AI configured.")
            # DEBUG: List available models to find the correct name
            print("Listing available models:")
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(m.name)
            
        # We will initialize the model dynamically in process_image to support fallback
        self.model_name = None

    def process_image(self, image_path, model_type="handwritten"):
        """
        Performs OCR on an image using Google Gemini Vision with FALLBACK support.
        """
        if not self.api_key:
            return "Error: GOOGLE_API_KEY not configured."

        image = Image.open(image_path)
        
        # Craft the prompt
        if model_type == "handwritten":
            prompt = "Please transcribe the handwritten text in this image exactly as it appears. Do not add any introductory text or markdown formatting. Just the raw text."
        else:
            prompt = "Please transcribe the printed text in this image exactly as it appears. Do not add any introductory text or markdown formatting. Just the raw text."

        # List of models to try in order of preference
        candidate_models = [
            'gemini-1.5-flash',
            'gemini-1.5-flash-001',
            'gemini-1.5-flash-latest',
            'gemini-pro-vision',  # Legacy backup
            'gemini-1.5-pro'      # Slower but powerful backup
        ]

        last_error = None
        
        for model_name in candidate_models:
            print(f"DEBUG: Attempting OCR with model: {model_name}")
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([prompt, image])
                
                if response.text:
                    print(f"SUCCESS: Model {model_name} worked!")
                    return response.text.strip()
                else:
                    print(f"WARNING: Model {model_name} returned empty text.")
            except Exception as e:
                print(f"WARNING: Model {model_name} failed with error: {e}")
                last_error = e
                # Continue to next model
        
        return f"Error: All models failed. Last error: {last_error}"

if __name__ == "__main__":
    # Test block
    ocr = OCREngine()
    # Ensure you have an image 'test.jpg' if you run this manually
    # print(ocr.process_image("test_image.jpg", "printed"))
