"""
Optimus Voice Agent
Real-time voice agent with authentic deep voice using ElevenLabs API
"""

import asyncio
import os
import json
import base64
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import logging

import httpx
import websockets
from pydub import AudioSegment
from pydub.playback import play
import pyaudio
import wave
import io

logger = logging.getLogger(__name__)

class VoiceProvider(Enum):
    """Available voice providers."""
    ELEVENLABS = "elevenlabs"
    PLAYHT = "playht"
    CARTESIA = "cartesia"
    LOCAL = "local"

@dataclass
class VoiceConfig:
    """Voice configuration."""
    provider: VoiceProvider
    api_key: Optional[str] = None
    voice_id: Optional[str] = None
    model: str = "eleven_turbo_v2_5"  # Fast, low-latency model
    stability: float = 0.5
    similarity_boost: float = 0.8
    style: float = 0.0
    use_speaker_boost: bool = True
    streaming: bool = True
    optimize_streaming_latency: int = 3  # 0-4, higher = lower latency

class OptimusVoiceAgent:
    """
    Real-time voice agent with Optimus Prime-like voice.
    Uses ElevenLabs or similar APIs for authentic voice generation.
    """
    
    def __init__(self, config: VoiceConfig):
        """Initialize voice agent."""
        self.config = config
        self.audio_queue = asyncio.Queue()
        self.is_speaking = False
        
        # PyAudio for audio playback
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Default to a deep male voice if no voice_id specified
        if not self.config.voice_id:
            # ElevenLabs deep male voices
            self.voice_options = {
                "adam": "pNInz6obpgDQGcFmaJgB",  # Deep American
                "antoni": "ErXwobaYiN019PkySvjV",  # Well-rounded
                "arnold": "VR6AewLTigWG4xSOukaG",  # Crisp
                "sam": "yoZ06aMxZJJ28mfd3POQ",     # Raspy American
                "marcus": "EXAVITQu4vr4xnSDxMaL",   # Deep British
                "clyde": "2EiwWnXFnvU5JabPnv8n",    # War veteran
                # Custom voice IDs can be added here
            }
            self.config.voice_id = self.voice_options.get("adam")  # Default to Adam
    
    def transform_text(self, text: str) -> str:
        """Transform text to Optimus Prime speech patterns."""
        replacements = {
            "hello": "Greetings, human ally",
            "goodbye": "Till all are one",
            "yes": "Affirmative",
            "no": "Negative",
            "okay": "Acknowledged",
            "starting": "Initiating",
            "stopping": "Terminating",
            "loading": "Energizing",
            "error": "System anomaly detected",
            "complete": "Mission accomplished",
            "ready": "All systems operational",
            "help": "Autobots, assist",
            "fight": "Autobots, engage",
            "transform": "Transform and roll out",
            "think": "My circuits indicate",
            "believe": "The Matrix reveals",
            "understand": "My processors confirm"
        }
        
        text_lower = text.lower()
        for original, replacement in replacements.items():
            if original in text_lower:
                text = text.replace(original, replacement)
                text = text.replace(original.capitalize(), replacement)
        
        # Add Optimus flair for short sentences
        if len(text) < 100:
            if "?" in text:
                text = f"Prime wisdom indicates: {text}"
            elif any(word in text_lower for word in ["battle", "decepticon", "fight"]):
                text = f"Autobots, {text}"
            elif any(word in text_lower for word in ["protect", "save", "help"]):
                text = f"By the Matrix, {text}"
        
        return text
    
    async def generate_speech_elevenlabs(self, text: str) -> bytes:
        """
        Generate speech using ElevenLabs API.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio data as bytes
        """
        if not self.config.api_key:
            raise ValueError("ElevenLabs API key required")
        
        # Transform text
        text = self.transform_text(text)
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.config.voice_id}/stream"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.config.api_key
        }
        
        data = {
            "text": text,
            "model_id": self.config.model,
            "voice_settings": {
                "stability": self.config.stability,
                "similarity_boost": self.config.similarity_boost,
                "style": self.config.style,
                "use_speaker_boost": self.config.use_speaker_boost
            },
            "optimize_streaming_latency": self.config.optimize_streaming_latency
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code}")
    
    async def stream_speech_elevenlabs(self, text: str, on_audio_chunk: Callable):
        """
        Stream speech using ElevenLabs WebSocket API for ultra-low latency.
        
        Args:
            text: Text to convert to speech
            on_audio_chunk: Callback for audio chunks
        """
        if not self.config.api_key:
            raise ValueError("ElevenLabs API key required")
        
        # Transform text
        text = self.transform_text(text)
        
        uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{self.config.voice_id}/stream-input?model_id={self.config.model}&optimize_streaming_latency={self.config.optimize_streaming_latency}"
        
        async with websockets.connect(uri) as websocket:
            # Send authentication
            await websocket.send(json.dumps({
                "xi_api_key": self.config.api_key,
                "voice_settings": {
                    "stability": self.config.stability,
                    "similarity_boost": self.config.similarity_boost,
                    "style": self.config.style,
                    "use_speaker_boost": self.config.use_speaker_boost
                }
            }))
            
            # Send text
            await websocket.send(json.dumps({
                "text": text,
                "flush": True
            }))
            
            # Receive audio chunks
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    if data.get("audio"):
                        audio_chunk = base64.b64decode(data["audio"])
                        await on_audio_chunk(audio_chunk)
                    
                    if data.get("isFinal"):
                        break
                        
                except websockets.exceptions.ConnectionClosed:
                    break
    
    def play_audio(self, audio_data: bytes):
        """Play audio data."""
        # Convert MP3 to WAV for playback
        audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
        
        # Apply audio effects for more robotic/deep sound
        audio_segment = audio_segment.low_pass_filter(3000)  # Remove high frequencies
        audio_segment = audio_segment + AudioSegment.silent(duration=50)  # Add slight reverb
        
        # Play the audio
        play(audio_segment)
    
    async def speak(self, text: str):
        """
        Speak text with Optimus Prime voice.
        
        Args:
            text: Text to speak
        """
        self.is_speaking = True
        
        try:
            if self.config.streaming:
                # Use streaming for lower latency
                audio_chunks = []
                
                async def collect_chunk(chunk):
                    audio_chunks.append(chunk)
                
                await self.stream_speech_elevenlabs(text, collect_chunk)
                
                # Combine and play chunks
                if audio_chunks:
                    audio_data = b''.join(audio_chunks)
                    self.play_audio(audio_data)
            else:
                # Generate complete audio
                audio_data = await self.generate_speech_elevenlabs(text)
                self.play_audio(audio_data)
                
        except Exception as e:
            logger.error(f"Speech generation failed: {e}")
            # Fallback to system TTS or error message
            print(f"[Optimus Voice Error] {e}")
        finally:
            self.is_speaking = False
    
    async def listen(self) -> str:
        """
        Listen for user input (placeholder for STT integration).
        
        Returns:
            Recognized text
        """
        # This would integrate with speech recognition
        # For now, return input from console
        return input("You: ")
    
    async def conversation_loop(self):
        """Main conversation loop."""
        print("\n" + "="*60)
        print("🤖 OPTIMUS PRIME VOICE AGENT")
        print("="*60)
        print("Voice powered by ElevenLabs API")
        print("Speaking with deep, commanding voice")
        print("="*60 + "\n")
        
        # Greeting
        await self.speak("I am Optimus Prime. How may I assist you today?")
        
        while True:
            try:
                # Listen for user input
                user_input = await self.listen()
                
                if user_input.lower() in ['exit', 'quit', 'goodbye']:
                    await self.speak("Till all are one. Goodbye, human ally.")
                    break
                
                # Process and respond
                # This is where you'd integrate with your Council API
                response = await self.process_command(user_input)
                
                # Speak response
                await self.speak(response)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Conversation error: {e}")
                await self.speak("System anomaly detected. Please repeat.")
    
    async def process_command(self, command: str) -> str:
        """
        Process user command and generate response.
        
        Args:
            command: User's spoken command
            
        Returns:
            Response text
        """
        # Here you would integrate with your actual command processing
        # For now, simple responses
        
        command_lower = command.lower()
        
        if "status" in command_lower:
            return "All systems operational. Autobots stand ready."
        elif "deploy" in command_lower:
            return "Initiating deployment sequence. Transform and roll out!"
        elif "council" in command_lower:
            return "The Council of Primes has been consulted. They advise caution and wisdom."
        elif "help" in command_lower:
            return "I can assist with system status, deployments, and strategic decisions. What is your mission?"
        else:
            return f"Acknowledged. Processing your request: {command}"


class VoiceAgentConfig:
    """Configuration for the voice agent."""
    
    @staticmethod
    def from_env() -> VoiceConfig:
        """Load configuration from environment variables."""
        provider = os.getenv("VOICE_PROVIDER", "elevenlabs")
        
        if provider == "elevenlabs":
            return VoiceConfig(
                provider=VoiceProvider.ELEVENLABS,
                api_key=os.getenv("ELEVENLABS_API_KEY"),
                voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
                model=os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2_5"),
                streaming=True,
                optimize_streaming_latency=3
            )
        else:
            return VoiceConfig(provider=VoiceProvider.LOCAL)


# Example usage
async def main():
    """Run the voice agent."""
    # Load config
    config = VoiceAgentConfig.from_env()
    
    # Check if API key is set
    if not config.api_key:
        print("\n" + "="*60)
        print("⚠️  ELEVENLABS API KEY REQUIRED")
        print("="*60)
        print("\nTo use the Optimus Prime Voice Agent:")
        print("1. Sign up at https://elevenlabs.io")
        print("2. Get your API key from the profile section")
        print("3. Set environment variable:")
        print("   export ELEVENLABS_API_KEY='your-api-key-here'")
        print("\nOptional: Create a custom deep voice:")
        print("1. Use Voice Design or Voice Cloning")
        print("2. Get the voice_id")
        print("3. Set: export ELEVENLABS_VOICE_ID='voice-id-here'")
        print("="*60)
        return
    
    # Create and run agent
    agent = OptimusVoiceAgent(config)
    await agent.conversation_loop()


if __name__ == "__main__":
    asyncio.run(main())