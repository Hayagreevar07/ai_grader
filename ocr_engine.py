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
            
        # Try using the specific 'latest' alias or fallback to 'gemini-pro' (text) / 'gemini-pro-vision' logic if needed.
        # However, 1.5-flash is multimodal. Let's try the concrete 001 version or latest.
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')

    def process_image(self, image_path, model_type="handwritten"):
        """
        Performs OCR on an image using Google Gemini Vision.
        Args:
            image_path (str): Path to the image file.
            model_type (str): 'handwritten' or 'printed' - used to fine-tune the prompt.
        Returns:
            str: The recognized text.
        """
        if not self.api_key:
            return "Error: GOOGLE_API_KEY not configured."

        try:
            print(f"Processing image: {image_path} with type: {model_type}")
            image = Image.open(image_path)
            
            # Craft the prompt based on the type
            if model_type == "handwritten":
                prompt = "Please transcribe the handwritten text in this image exactly as it appears. Do not add any introductory text or markdown formatting. Just the raw text."
            else:
                prompt = "Please transcribe the printed text in this image exactly as it appears. Do not add any introductory text or markdown formatting. Just the raw text."

            response = self.model.generate_content([prompt, image])
            
            # Simple error handling/retries could be added here
            if response.text:
                return response.text.strip()
            else:
                return "Error: No text detected or blocked."

        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return f"Error: {e}"

if __name__ == "__main__":
    # Test block
    ocr = OCREngine()
    # Ensure you have an image 'test.jpg' if you run this manually
    # print(ocr.process_image("test_image.jpg", "printed"))
