"""
FakeYou Optimus Prime Voice Integration
Uses FakeYou's free API to generate authentic Optimus Prime voice
"""

import asyncio
import httpx
import json
import time
from typing import Optional, Dict, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class FakeYouOptimus:
    """
    Integration with FakeYou.com for Optimus Prime voice generation.
    FakeYou has multiple Optimus Prime models available for free.
    """
    
    def __init__(self):
        """Initialize FakeYou Optimus Prime voice."""
        self.base_url = "https://api.fakeyou.com"
        
        # Optimus Prime voice model IDs on FakeYou
        self.voice_models = {
            "optimus_v3": "TM:7wgq5jfcnh8p",  # Latest version
            "optimus_g1": "TM:s01m4wx9apray",  # G1 cartoon voice
            "optimus_animated": "TM:7eczkkb3f623",  # Animated series
            "optimus_movie": "TM:wxa71rnady6f"  # Movie voice (Peter Cullen)
        }
        
        # Default to movie voice (Peter Cullen)
        self.current_voice = self.voice_models["optimus_movie"]
        
        # Speech pattern transformations
        self.transformations = {
            "hello": "Greetings, human ally",
            "goodbye": "Till all are one",
            "yes": "Affirmative",
            "no": "Negative", 
            "ok": "Acknowledged",
            "okay": "Acknowledged",
            "starting": "Initiating",
            "stopping": "Terminating",
            "loading": "Energizing",
            "error": "System anomaly detected",
            "complete": "Mission accomplished",
            "ready": "All systems operational",
            "help": "Autobots, assist",
            "fight": "Autobots, engage",
            "transform": "Transform and roll out"
        }
    
    def transform_text(self, text: str) -> str:
        """Transform text to Optimus Prime speech patterns."""
        text_lower = text.lower()
        
        # Apply transformations
        for original, replacement in self.transformations.items():
            if original in text_lower:
                text = text.replace(original, replacement)
                text = text.replace(original.capitalize(), replacement)
        
        # Add Optimus flair
        if len(text) < 100:
            if "council" in text_lower:
                text = f"By the Matrix, {text}"
            elif "deploy" in text_lower or "battle" in text_lower:
                text = f"Autobots, {text}"
            elif "?" in text and not any(prefix in text for prefix in ["By", "Autobots"]):
                text = f"Prime wisdom indicates: {text}"
        
        # Add inspiring endings for short phrases
        if len(text) < 80 and not text.endswith("!") and not text.endswith("?"):
            import random
            if random.random() < 0.3:
                endings = [
                    " Transform and roll out!",
                    " One shall stand, one shall fall.",
                    " Freedom is the right of all sentient beings.",
                    " There is more than meets the eye."
                ]
                text += random.choice(endings)
        
        return text
    
    async def generate_speech(self, text: str, voice_model: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate speech using FakeYou API.
        
        Args:
            text: Text to convert to speech
            voice_model: Optional voice model ID (defaults to movie voice)
            
        Returns:
            Dict with audio URL and job info
        """
        if voice_model is None:
            voice_model = self.current_voice
        
        # Transform text to Optimus style
        text = self.transform_text(text)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Submit TTS job
                tts_payload = {
                    "uuid_idempotency_token": str(int(time.time() * 1000)),
                    "tts_model_token": voice_model,
                    "inference_text": text
                }
                
                response = await client.post(
                    f"{self.base_url}/tts/inference",
                    json=tts_payload
                )
                
                if response.status_code != 200:
                    logger.error(f"FakeYou API error: {response.status_code}")
                    return {"error": "Failed to submit TTS job"}
                
                result = response.json()
                job_token = result.get("inference_job_token")
                
                if not job_token:
                    return {"error": "No job token received"}
                
                # Step 2: Poll for completion
                max_attempts = 30
                for attempt in range(max_attempts):
                    await asyncio.sleep(2)  # Wait 2 seconds between polls
                    
                    status_response = await client.get(
                        f"{self.base_url}/tts/job/{job_token}"
                    )
                    
                    if status_response.status_code == 200:
                        job_status = status_response.json()
                        
                        if job_status.get("status") == "complete_success":
                            audio_path = job_status.get("audio_path")
                            if audio_path:
                                return {
                                    "success": True,
                                    "audio_url": f"https://storage.fakeyou.com/{audio_path}",
                                    "text": text,
                                    "voice_model": voice_model,
                                    "duration": job_status.get("duration")
                                }
                        elif job_status.get("status") == "complete_failure":
                            return {"error": "TTS generation failed"}
                
                return {"error": "Timeout waiting for audio generation"}
                
        except Exception as e:
            logger.error(f"FakeYou API error: {e}")
            return {"error": str(e)}
    
    def get_javascript_integration(self) -> str:
        """Get JavaScript code for browser integration with FakeYou."""
        return '''
        class FakeYouOptimus {
            constructor() {
                // FakeYou doesn't have official CORS-enabled API
                // This would need a proxy server or use their web interface
                this.baseUrl = 'https://api.fakeyou.com';
                
                // Voice model IDs
                this.voiceModels = {
                    movie: 'TM:wxa71rnady6f',
                    g1: 'TM:s01m4wx9apray',
                    animated: 'TM:7eczkkb3f623'
                };
                
                this.currentVoice = this.voiceModels.movie;
            }
            
            async generateSpeech(text) {
                // Transform text to Optimus style
                text = this.transformText(text);
                
                // Note: This would need a backend proxy due to CORS
                // Or use the iframe embed option from FakeYou
                
                // For now, we'll use the direct web interface
                const encodedText = encodeURIComponent(text);
                const voiceId = this.currentVoice;
                
                // Open FakeYou in new tab with pre-filled text
                const fakeYouUrl = `https://fakeyou.com/tts?voice=${voiceId}&text=${encodedText}`;
                
                // Return URL for iframe or new tab
                return {
                    url: fakeYouUrl,
                    text: text,
                    instructions: 'Click to generate in FakeYou (opens in new tab)'
                };
            }
            
            transformText(text) {
                const replacements = {
                    'hello': 'Greetings, human ally',
                    'goodbye': 'Till all are one',
                    'yes': 'Affirmative',
                    'no': 'Negative',
                    'starting': 'Initiating',
                    'stopping': 'Terminating',
                    'error': 'System anomaly detected',
                    'complete': 'Mission accomplished'
                };
                
                let transformed = text;
                for (const [key, value] of Object.entries(replacements)) {
                    const regex = new RegExp(`\\b${key}\\b`, 'gi');
                    transformed = transformed.replace(regex, value);
                }
                
                return transformed;
            }
        }
        '''
    
    async def download_audio(self, audio_url: str, output_path: str) -> bool:
        """Download generated audio file."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(audio_url)
                if response.status_code == 200:
                    Path(output_path).write_bytes(response.content)
                    return True
        except Exception as e:
            logger.error(f"Failed to download audio: {e}")
        return False


class OptimusPrimeVoiceService:
    """
    Main service for Optimus Prime voice generation.
    Manages multiple TTS providers and fallbacks.
    """
    
    def __init__(self):
        """Initialize voice service."""
        self.fakeyou = FakeYouOptimus()
        self.providers = {
            "fakeyou": self.fakeyou,
            # Add other providers here
        }
        self.current_provider = "fakeyou"
    
    async def speak(self, text: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate Optimus Prime speech.
        
        Args:
            text: Text to speak
            provider: Optional provider override
            
        Returns:
            Dict with audio URL or error
        """
        if provider is None:
            provider = self.current_provider
        
        if provider in self.providers:
            return await self.providers[provider].generate_speech(text)
        else:
            return {"error": f"Unknown provider: {provider}"}
    
    def get_available_voices(self) -> Dict[str, list]:
        """Get list of available voice models."""
        return {
            "fakeyou": list(self.fakeyou.voice_models.keys()),
            # Add other providers
        }


# Example usage
async def test_optimus_voice():
    """Test the Optimus Prime voice generation."""
    service = OptimusPrimeVoiceService()
    
    test_phrases = [
        "Hello, I am ready to help.",
        "Should we deploy to production?",
        "The system is ready for battle.",
        "Transform and roll out!"
    ]
    
    print("\n🎭 Testing Optimus Prime Voice Generation")
    print("="*50)
    
    for phrase in test_phrases:
        print(f"\nOriginal: {phrase}")
        transformed = service.fakeyou.transform_text(phrase)
        print(f"Optimus: {transformed}")
        
        # Generate actual audio (would need API key or web interface)
        result = await service.speak(phrase)
        if result.get("success"):
            print(f"Audio URL: {result['audio_url']}")
        else:
            print(f"Error: {result.get('error')}")
    
    print("\n" + "="*50)
    print("Note: FakeYou API requires registration for programmatic access.")
    print("Visit https://fakeyou.com to use the web interface directly.")
    print("Search for 'Optimus Prime' to find available voice models.")


if __name__ == "__main__":
    asyncio.run(test_optimus_voice())