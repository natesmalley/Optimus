#!/usr/bin/env python
"""
Complete Voice Setup for Optimus Prime
Interactive setup with voice testing and selection
"""

import os
import asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv, set_key
import json
import base64
import subprocess
import sys

# Load existing environment
load_dotenv()

class OptimusVoiceSetup:
    """Complete voice setup with ElevenLabs integration."""
    
    def __init__(self):
        self.api_key = ""
        self.selected_voice_id = ""
        self.base_url = "https://api.elevenlabs.io/v1"
        self.test_audio_path = Path("optimus_voice_test.mp3")
        
    def display_banner(self):
        """Display setup banner."""
        print("\n" + "="*70)
        print("    🤖 OPTIMUS PRIME VOICE CONFIGURATION 🤖")
        print("    Transform Your AI Into The Leader of the Autobots")
        print("="*70 + "\n")
        
    def display_step(self, step_num, title):
        """Display step header."""
        print(f"\n{'─'*60}")
        print(f"  Step {step_num}: {title}")
        print(f"{'─'*60}\n")
        
    async def get_api_key(self):
        """Get API key from user or .env file."""
        self.display_step(1, "ElevenLabs API Key Configuration")
        
        # Check if already in .env
        existing_key = os.getenv("ELEVENLABS_API_KEY", "")
        
        if existing_key:
            print(f"✓ Found existing API key: {existing_key[:8]}...")
            use_existing = input("\nUse this key? (y/n): ").strip().lower()
            if use_existing == 'y':
                self.api_key = existing_key
                return True
        
        print("📝 To get your ElevenLabs API key:")
        print("   1. Go to https://elevenlabs.io")
        print("   2. Click on your profile (top right)")
        print("   3. Click on 'API Keys' or 'Profile'")
        print("   4. Copy the API key\n")
        
        api_key = input("Paste your API key here: ").strip()
        
        if not api_key:
            print("❌ No API key provided")
            return False
            
        self.api_key = api_key
        return True
        
    async def test_api_key(self):
        """Verify API key works."""
        print("\n🔑 Testing API key...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/user",
                    headers={"xi-api-key": self.api_key}
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    print(f"✅ API key valid!")
                    
                    subscription = user_data.get('subscription', {})
                    character_limit = subscription.get('character_limit', 0)
                    character_count = subscription.get('character_count', 0)
                    
                    print(f"📊 Monthly limit: {character_limit:,} characters")
                    print(f"📊 Used this month: {character_count:,} characters")
                    print(f"📊 Remaining: {character_limit - character_count:,} characters")
                    
                    return True
                else:
                    print(f"❌ Invalid API key: {response.status_code}")
                    print("Please check your key and try again.")
                    return False
                    
        except Exception as e:
            print(f"❌ Error testing API key: {e}")
            return False
            
    async def get_available_voices(self):
        """Fetch and display available voices."""
        self.display_step(2, "Voice Selection")
        
        print("🎤 Fetching available voices...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers={"xi-api-key": self.api_key}
                )
                
                if response.status_code != 200:
                    print(f"❌ Failed to fetch voices: {response.status_code}")
                    return []
                    
                data = response.json()
                voices = data.get('voices', [])
                
                # Filter and rank for Optimus Prime
                male_voices = []
                for voice in voices:
                    labels = voice.get('labels', {})
                    name = voice.get('name', '')
                    description = labels.get('description', '').lower()
                    
                    # Score based on Optimus characteristics
                    score = 0
                    if 'male' in str(labels.get('gender', '')).lower():
                        score += 2
                    if 'deep' in description or 'low' in description:
                        score += 3
                    if 'american' in str(labels.get('accent', '')).lower():
                        score += 2
                    if any(word in description for word in ['strong', 'authoritative', 'commanding']):
                        score += 2
                    if 'middle' in str(labels.get('age', '')).lower():
                        score += 1
                        
                    if score > 0:
                        male_voices.append({
                            'id': voice['voice_id'],
                            'name': name,
                            'description': labels.get('description', 'No description'),
                            'accent': labels.get('accent', 'Unknown'),
                            'age': labels.get('age', 'Unknown'),
                            'score': score
                        })
                
                # Sort by score
                male_voices.sort(key=lambda x: x['score'], reverse=True)
                
                return male_voices[:10]  # Top 10 voices
                
        except Exception as e:
            print(f"❌ Error fetching voices: {e}")
            return []
            
    async def test_voice(self, voice_id, voice_name, text=None):
        """Generate test audio with selected voice."""
        if not text:
            text = "I am Optimus Prime, leader of the Autobots. Freedom is the right of all sentient beings. Autobots, transform and roll out!"
            
        print(f"\n🎯 Generating audio with {voice_name}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_turbo_v2_5",
                        "voice_settings": {
                            "stability": 0.3,
                            "similarity_boost": 0.8,
                            "style": 0.2,
                            "use_speaker_boost": True
                        }
                    }
                )
                
                if response.status_code == 200:
                    self.test_audio_path.write_bytes(response.content)
                    print(f"✅ Audio saved to: {self.test_audio_path}")
                    return True
                else:
                    print(f"❌ Failed to generate audio: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error generating audio: {e}")
            return False
            
    def play_audio(self):
        """Play the generated audio file."""
        if not self.test_audio_path.exists():
            print("❌ No audio file to play")
            return
            
        print("\n▶️  Playing audio...")
        
        # Try different methods based on OS
        if sys.platform == "darwin":  # macOS
            subprocess.run(["afplay", str(self.test_audio_path)])
        elif sys.platform == "win32":  # Windows
            os.startfile(str(self.test_audio_path))
        else:  # Linux
            try:
                subprocess.run(["xdg-open", str(self.test_audio_path)])
            except:
                print(f"Please open {self.test_audio_path} manually to hear the voice")
                
    async def select_voice_interactive(self):
        """Interactive voice selection with testing."""
        voices = await self.get_available_voices()
        
        if not voices:
            print("❌ No suitable voices found")
            # Use default
            self.selected_voice_id = "pNInz6obpgDQGcFmaJgB"
            print(f"Using default voice: {self.selected_voice_id}")
            return
            
        print("\n🎭 Top voices for Optimus Prime:")
        print("─" * 60)
        
        for i, voice in enumerate(voices, 1):
            print(f"\n{i}. {voice['name']} (Score: {voice['score']})")
            print(f"   Accent: {voice['accent']}, Age: {voice['age']}")
            print(f"   Description: {voice['description'][:80]}...")
            
        print(f"\n0. Use default (Adam - Deep American)")
        print("─" * 60)
        
        while True:
            choice = input("\nSelect a voice to test (1-10) or 'done' to finish: ").strip()
            
            if choice.lower() == 'done':
                break
                
            if choice == '0':
                voice_id = "pNInz6obpgDQGcFmaJgB"
                voice_name = "Adam (Default)"
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(voices):
                        voice_id = voices[idx]['id']
                        voice_name = voices[idx]['name']
                    else:
                        print("Invalid choice")
                        continue
                except:
                    print("Invalid choice")
                    continue
                    
            # Test the voice
            success = await self.test_voice(voice_id, voice_name)
            
            if success:
                self.play_audio()
                
                use_this = input(f"\nUse {voice_name} as Optimus Prime? (y/n): ").strip().lower()
                if use_this == 'y':
                    self.selected_voice_id = voice_id
                    print(f"✅ Selected: {voice_name}")
                    return
                    
        # If no voice selected, use the top scoring one
        if not self.selected_voice_id and voices:
            self.selected_voice_id = voices[0]['id']
            print(f"\n✅ Using top-ranked voice: {voices[0]['name']}")
            
    async def update_env_file(self):
        """Update .env file with configuration."""
        self.display_step(3, "Saving Configuration")
        
        env_path = Path(".env")
        
        # Update or create .env
        set_key(env_path, "ELEVENLABS_API_KEY", self.api_key)
        set_key(env_path, "ELEVENLABS_VOICE_ID", self.selected_voice_id)
        set_key(env_path, "ELEVENLABS_MODEL", "eleven_turbo_v2_5")
        
        print(f"✅ Configuration saved to .env")
        print(f"   API Key: {self.api_key[:8]}...")
        print(f"   Voice ID: {self.selected_voice_id}")
        
    async def test_full_integration(self):
        """Test the complete voice system."""
        self.display_step(4, "Testing Full Integration")
        
        print("🧪 Testing voice transformation...")
        
        test_phrases = [
            "Hello, how are you?",
            "Starting the analysis now",
            "Error detected in system",
            "Thank you for your help"
        ]
        
        from src.api.voice_agent_api import transform_to_optimus
        
        for phrase in test_phrases:
            transformed = transform_to_optimus(phrase)
            print(f"   '{phrase}' → '{transformed}'")
            
        print("\n✅ Voice transformation working!")
        
        # Generate final test
        print("\n🎯 Generating final test audio...")
        
        final_text = transform_to_optimus("Hello human. I am ready to assist you with your projects. Together we shall achieve victory.")
        
        success = await self.test_voice(
            self.selected_voice_id,
            "Optimus Prime",
            final_text
        )
        
        if success:
            self.play_audio()
            print("\n✅ Voice system fully configured!")
            
    def display_next_steps(self):
        """Show what to do next."""
        print("\n" + "="*70)
        print("    ✅ OPTIMUS PRIME VOICE READY!")
        print("="*70)
        
        print("\n📋 Next Steps:\n")
        
        print("1. Start the server with voice:")
        print("   python test_server.py\n")
        
        print("2. Open the voice interface:")
        print("   http://localhost:8003/frontend/voice-interface.html\n")
        
        print("3. Test voice commands:")
        print("   - 'Hello Optimus'")
        print("   - 'Show me my projects'")
        print("   - 'What's the system status?'\n")
        
        print("4. Custom voice creation (optional):")
        print("   - Go to ElevenLabs → Voice Lab")
        print("   - Create a voice with these settings:")
        print("     • Gender: Male")
        print("     • Age: Middle-aged")
        print("     • Accent: American")
        print("     • Pitch: Lower")
        print("     • Style: Authoritative\n")
        
        print("💡 Tip: Your free tier gives you ~10 minutes of speech per month")
        print("        Use it wisely, Autobot!")
        
async def main():
    """Run the complete setup."""
    setup = OptimusVoiceSetup()
    
    setup.display_banner()
    
    # Step 1: API Key
    if not await setup.get_api_key():
        print("\n❌ Setup cancelled")
        return
        
    if not await setup.test_api_key():
        print("\n❌ Invalid API key. Please run setup again.")
        return
        
    # Step 2: Voice Selection
    await setup.select_voice_interactive()
    
    # Step 3: Save Configuration
    await setup.update_env_file()
    
    # Step 4: Test Integration
    await setup.test_full_integration()
    
    # Step 5: Next Steps
    setup.display_next_steps()
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Setup error: {e}")
        print("Please check your connection and try again")