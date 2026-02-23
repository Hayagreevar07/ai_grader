import asyncio
import edge_tts
import os
import uuid

class VoiceManager:
    def __init__(self, output_dir="static/audio"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        # Default voice - English US
        self.voice = "en-US-AriaNeural"

    async def _generate_audio(self, text, output_path):
        """Async function to generate audio using edge-tts."""
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_path)

    def text_to_speech(self, text):
        """
        Generates TTS audio for the given text.
        Returns the relative path to the generated audio file.
        """
        filename = f"{uuid.uuid4()}.mp3"
        output_path = os.path.join(self.output_dir, filename)
        
        try:
            # edge-tts is async, so we need to run it in a loop
            # Check if there is already a running loop (e.g. jupyter)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we are in an async web server context (like some uvicorn setups), logic differs.
                    # For standard Flask (sync), we create a new loop or use asyncio.run
                    # But asyncio.run cannot be called when a loop is running.
                    # Since Flask dev server is threaded/sync, asyncio.run usually works.
                    # However, to be safe:
                     asyncio.run(self._generate_audio(text, output_path))
                else:
                     loop.run_until_complete(self._generate_audio(text, output_path))
            except RuntimeError:
                # No event loop found
                asyncio.run(self._generate_audio(text, output_path))
            
            return f"/{self.output_dir}/{filename}".replace("\\", "/")
            
        except Exception as e:
            print(f"TTS Generation Error: {e}")
            return None

if __name__ == "__main__":
    # Test
    vm = VoiceManager()
    path = vm.text_to_speech("Hello! This is a test of the AI Grader voice system.")
    print(f"Generated at: {path}")
