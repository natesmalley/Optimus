"""
Optimus Prime Voice Synthesizer
Creates a deep, authoritative voice like Optimus Prime
"""

import asyncio
import numpy as np
from typing import Optional
import json
import base64
import os

class OptimusPrimeVoice:
    """
    Voice synthesizer that creates Optimus Prime-like speech.
    Uses advanced TTS services and audio processing.
    """
    
    def __init__(self):
        """Initialize Optimus Prime voice settings."""
        self.voice_config = {
            "pitch": -5,  # Lower pitch for deeper voice
            "speed": 0.9,  # Slightly slower for gravitas
            "resonance": 1.5,  # Add chest resonance
            "formant_shift": -2,  # Deeper formants
            "bass_boost": 6,  # Enhance low frequencies
        }
        
        # Optimus Prime speech patterns
        self.speech_patterns = {
            "greeting": [
                "Autobots, roll out!",
                "I am Optimus Prime, and I send this message...",
                "Greetings, human ally.",
                "This is Optimus Prime, reporting.",
            ],
            "acknowledgment": [
                "Understood.",
                "Affirmative.",
                "Your request is acknowledged.",
                "Processing your command.",
            ],
            "inspiration": [
                "Freedom is the right of all sentient beings.",
                "There's more to you than meets the eye.",
                "Together, we shall prevail.",
                "One shall stand, one shall fall.",
            ],
            "prefix": {
                "council": "The Council has deliberated. Their wisdom indicates:",
                "project": "Initiating project protocols.",
                "status": "Systems diagnostic complete.",
                "deploy": "Preparing for deployment operation.",
                "error": "Alert: System anomaly detected.",
            }
        }
    
    def add_optimus_flavor(self, text: str, context: str = "general") -> str:
        """Add Optimus Prime-style phrasing to responses."""
        
        # Add contextual prefix
        if context in self.speech_patterns["prefix"]:
            text = f"{self.speech_patterns['prefix'][context]} {text}"
        
        # Replace common phrases with Optimus-style ones
        replacements = {
            "Starting": "Initiating",
            "Stopping": "Terminating",
            "Error": "System anomaly",
            "Complete": "Mission accomplished",
            "Ready": "All systems operational",
            "Failed": "Mission compromised",
            "Checking": "Scanning",
            "Loading": "Energizing",
            "Saved": "Secured",
            "Deleted": "Eliminated",
            "Updated": "Upgraded",
            "Warning": "Alert",
            "Success": "Victory achieved",
            "I recommend": "My sensors indicate",
            "I think": "My analysis suggests",
            "Hello": "Greetings",
            "Goodbye": "Till all are one",
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
            text = text.replace(old.lower(), new.lower())
        
        return text
    
    def get_elevenlabs_config(self) -> dict:
        """Get ElevenLabs API configuration for Optimus Prime voice."""
        return {
            "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel voice as base (deep female)
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.75,
                "style": 0.5,
                "use_speaker_boost": True
            },
            # Custom settings to make it sound like Optimus
            "pronunciation_dictionary_locators": [],
            "seed": 42,  # Consistent voice generation
            "previous_text": "I am Optimus Prime, leader of the Autobots.",  # Voice priming
            "next_text": "Autobots, transform and roll out!",
            "previous_request_ids": [],
            "use_pvc": True,
            "optimize_streaming_latency": 3,
            "output_format": "mp3_44100_128",
        }
    
    def get_azure_config(self) -> dict:
        """Get Azure Cognitive Services configuration for Optimus voice."""
        return {
            "voice_name": "en-US-DavisNeural",  # Deep male voice
            "pitch": "-15Hz",  # Much lower pitch
            "rate": "-10%",  # Slower speech
            "volume": "+10%",  # Louder
            "emphasis": "strong",
            "style": "serious",
            "style_degree": 1.5,
            "prosody": {
                "contour": "(0%,+0Hz) (50%,-10Hz) (100%,-5Hz)",  # Falling intonation
                "range": "+20%",  # More variation
            },
            "effects": [
                "equalizer:0:-3:0:0:3:6:6:3:0:-3",  # Bass boost EQ
                "reverb:20:10:50:50:5",  # Slight reverb for depth
            ]
        }
    
    def get_google_config(self) -> dict:
        """Get Google Cloud TTS configuration for Optimus voice."""
        return {
            "voice": {
                "language_code": "en-US",
                "name": "en-US-Wavenet-B",  # Deep male voice
                "ssml_gender": "MALE"
            },
            "audio_config": {
                "audio_encoding": "MP3",
                "speaking_rate": 0.9,
                "pitch": -5.0,
                "volume_gain_db": 3.0,
                "effects_profile_id": ["large-automotive-class-device"],
                "sample_rate_hertz": 24000
            }
        }
    
    async def synthesize_with_elevenlabs(self, text: str, api_key: str) -> bytes:
        """Synthesize speech using ElevenLabs API."""
        import httpx
        
        url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM/stream"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        data = {
            "text": self.add_optimus_flavor(text),
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5,
                "style": 0.8,
                "use_speaker_boost": True
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)
            if response.status_code == 200:
                return response.content
            else:
                raise Exception(f"ElevenLabs API error: {response.status_code}")
    
    def process_audio_effects(self, audio_data: np.ndarray, sample_rate: int = 44100) -> np.ndarray:
        """Apply Optimus Prime audio effects to voice."""
        try:
            from scipy import signal
            from scipy.signal import butter, sosfilt
            
            # 1. Pitch shift down (formant-preserving)
            # This would require a library like pyrubberband or soundfile
            
            # 2. Add bass boost (low-pass emphasis)
            sos_bass = butter(4, 300, btype='low', fs=sample_rate, output='sos')
            bass_boost = sosfilt(sos_bass, audio_data) * 2.5
            audio_data = audio_data + bass_boost * 0.3
            
            # 3. Add slight robotic modulation
            t = np.arange(len(audio_data)) / sample_rate
            modulation = np.sin(2 * np.pi * 6 * t) * 0.05  # 6Hz modulation
            audio_data = audio_data * (1 + modulation)
            
            # 4. Add resonance (comb filter for metallic effect)
            delay_samples = int(0.002 * sample_rate)  # 2ms delay
            comb_filtered = np.zeros_like(audio_data)
            comb_filtered[delay_samples:] = audio_data[:-delay_samples] * 0.5
            audio_data = audio_data + comb_filtered
            
            # 5. Compression and limiting
            threshold = 0.7
            ratio = 4
            audio_data = np.where(
                np.abs(audio_data) > threshold,
                np.sign(audio_data) * (threshold + (np.abs(audio_data) - threshold) / ratio),
                audio_data
            )
            
            # 6. Normalize
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data / max_val * 0.95
                
            return audio_data
            
        except ImportError:
            print("Warning: scipy not installed, skipping audio effects")
            return audio_data
    
    def get_voice_javascript(self) -> str:
        """Get JavaScript code for browser-based Optimus voice."""
        return '''
        class OptimusPrimeVoice {
            constructor() {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                this.setupEffects();
            }
            
            setupEffects() {
                // Create audio nodes for Optimus Prime voice effect
                this.gainNode = this.audioContext.createGain();
                this.gainNode.gain.value = 1.2;
                
                // Bass boost
                this.bassFilter = this.audioContext.createBiquadFilter();
                this.bassFilter.type = 'lowshelf';
                this.bassFilter.frequency.value = 300;
                this.bassFilter.gain.value = 6;
                
                // Resonance
                this.resonanceFilter = this.audioContext.createBiquadFilter();
                this.resonanceFilter.type = 'peaking';
                this.resonanceFilter.frequency.value = 150;
                this.resonanceFilter.Q.value = 2;
                this.resonanceFilter.gain.value = 4;
                
                // Compressor for that "broadcast" quality
                this.compressor = this.audioContext.createDynamicsCompressor();
                this.compressor.threshold.value = -20;
                this.compressor.knee.value = 10;
                this.compressor.ratio.value = 8;
                this.compressor.attack.value = 0.003;
                this.compressor.release.value = 0.1;
                
                // Connect the chain
                this.bassFilter.connect(this.resonanceFilter);
                this.resonanceFilter.connect(this.compressor);
                this.compressor.connect(this.gainNode);
                this.gainNode.connect(this.audioContext.destination);
            }
            
            async speakAsOptimus(text, voice = null) {
                // Add Optimus Prime phrasing
                text = this.addOptimusFlavor(text);
                
                const utterance = new SpeechSynthesisUtterance(text);
                
                // Configure for deep voice
                utterance.pitch = 0.3;  // Much lower pitch
                utterance.rate = 0.85;   // Slower, more deliberate
                utterance.volume = 1.0;
                
                // Try to find the deepest available voice
                const voices = speechSynthesis.getVoices();
                const deepVoices = voices.filter(v => 
                    v.name.includes('Male') || 
                    v.name.includes('David') || 
                    v.name.includes('Daniel') ||
                    v.name.includes('James') ||
                    v.name.includes('Microsoft Mark') ||
                    v.name.includes('Google UK English Male')
                );
                
                if (deepVoices.length > 0) {
                    utterance.voice = deepVoices[0];
                } else if (voice) {
                    utterance.voice = voice;
                }
                
                // For Chrome, we can use the Web Audio API to process the voice
                if (window.chrome && this.audioContext) {
                    // This would require capturing the audio stream
                    // which is complex in current browser implementations
                    // So we'll use the standard synthesis with adjusted parameters
                }
                
                speechSynthesis.speak(utterance);
                
                return new Promise(resolve => {
                    utterance.onend = resolve;
                });
            }
            
            addOptimusFlavor(text) {
                const replacements = {
                    'Starting': 'Initiating',
                    'Stopping': 'Terminating',
                    'Error': 'System anomaly detected',
                    'Complete': 'Mission accomplished',
                    'Ready': 'All systems operational',
                    'Hello': 'Greetings, human ally',
                    'Goodbye': 'Till all are one',
                    'Yes': 'Affirmative',
                    'No': 'Negative',
                    'OK': 'Acknowledged',
                    'Loading': 'Energizing',
                    'Processing': 'Analyzing with Cybertronian technology'
                };
                
                for (const [key, value] of Object.entries(replacements)) {
                    const regex = new RegExp(key, 'gi');
                    text = text.replace(regex, value);
                }
                
                // Add occasional Optimus phrases
                if (Math.random() < 0.3) {
                    const phrases = [
                        'Autobots, ',
                        'By the Matrix, ',
                        'As Prime, I decree: ',
                        'Cybertron protocols indicate: '
                    ];
                    text = phrases[Math.floor(Math.random() * phrases.length)] + text;
                }
                
                return text;
            }
            
            getRandomGreeting() {
                const greetings = [
                    "I am Optimus Prime, ready to assist.",
                    "Autobots, roll out! How may I help you?",
                    "This is Optimus Prime, responding to your call.",
                    "Greetings, human ally. What is your request?",
                    "Prime here. State your requirements."
                ];
                return greetings[Math.floor(Math.random() * greetings.length)];
            }
        }
        '''

# Configuration for popular TTS services
TTS_SERVICE_CONFIGS = {
    "elevenlabs": {
        "url": "https://elevenlabs.io",
        "docs": "https://docs.elevenlabs.io/speech-synthesis/voice-settings",
        "features": [
            "Most realistic voices",
            "Voice cloning capability",
            "Custom voice creation",
            "Real-time streaming"
        ],
        "setup": """
        1. Sign up at elevenlabs.io
        2. Get API key from profile
        3. Use voice ID '21m00Tcm4TlvDq8ikWAM' or clone Optimus Prime voice
        4. Add API key to .env as ELEVENLABS_API_KEY
        """
    },
    "azure": {
        "url": "https://azure.microsoft.com/services/cognitive-services/text-to-speech/",
        "features": [
            "Neural voices",
            "SSML support", 
            "Custom neural voice",
            "Multiple languages"
        ],
        "setup": """
        1. Create Azure account
        2. Create Speech resource
        3. Get key and region
        4. Add to .env as AZURE_SPEECH_KEY and AZURE_SPEECH_REGION
        """
    },
    "google": {
        "url": "https://cloud.google.com/text-to-speech",
        "features": [
            "WaveNet voices",
            "Neural2 voices",
            "Studio voices",
            "SSML support"
        ],
        "setup": """
        1. Enable Google Cloud TTS API
        2. Create service account
        3. Download credentials JSON
        4. Set GOOGLE_APPLICATION_CREDENTIALS env var
        """
    },
    "uberduck": {
        "url": "https://uberduck.ai",
        "features": [
            "Celebrity voices",
            "Character voices (including Optimus Prime!)",
            "Custom voice training",
            "Community voices"
        ],
        "setup": """
        1. Sign up at uberduck.ai
        2. Get API key
        3. Search for 'Optimus Prime' voice
        4. Add to .env as UBERDUCK_API_KEY
        """
    },
    "fakeyou": {
        "url": "https://fakeyou.com",
        "features": [
            "Wide character selection",
            "Optimus Prime voice available",
            "Community models",
            "Voice conversion"
        ],
        "setup": """
        1. Create account at fakeyou.com
        2. Find Optimus Prime model
        3. Use API or web interface
        4. Note: API may have rate limits
        """
    }
}

def print_setup_instructions():
    """Print instructions for setting up Optimus Prime voice."""
    print("\n" + "="*60)
    print("🎭 OPTIMUS PRIME VOICE SETUP")
    print("="*60)
    print("\nTo get the authentic Optimus Prime voice, choose one of these services:\n")
    
    for service, config in TTS_SERVICE_CONFIGS.items():
        print(f"📢 {service.upper()}")
        print(f"   URL: {config['url']}")
        print(f"   Features: {', '.join(config['features'][:2])}")
        print(f"   Setup: {config['setup'][:100]}...")
        print()
    
    print("🎯 RECOMMENDED: Uberduck or FakeYou for actual Optimus Prime voice!")
    print("="*60)

if __name__ == "__main__":
    optimus_voice = OptimusPrimeVoice()
    print_setup_instructions()
    
    # Test phrase transformation
    test_phrases = [
        "Hello, how can I help you?",
        "Starting the project now.",
        "Error detected in system.",
        "Task complete.",
        "System ready."
    ]
    
    print("\n🎤 Voice Transformation Examples:")
    print("-"*40)
    for phrase in test_phrases:
        transformed = optimus_voice.add_optimus_flavor(phrase)
        print(f"Original: {phrase}")
        print(f"Optimus:  {transformed}\n")