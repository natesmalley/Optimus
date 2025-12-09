#!/usr/bin/env python
"""
ElevenLabs Setup and Test Script for Optimus Prime Voice
"""

import os
import asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

class ElevenLabsSetup:
    """Setup and test ElevenLabs integration."""
    
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "")
        self.base_url = "https://api.elevenlabs.io/v1"
        
    async def test_api_key(self):
        """Test if API key is valid."""
        if not self.api_key:
            print("❌ No API key found!")
            print("\n📝 To set up your API key:")
            print("1. Copy your ElevenLabs API key")
            print("2. Create a .env file in this directory")
            print("3. Add: ELEVENLABS_API_KEY=your_key_here")
            return False
            
        print(f"🔑 Testing API key: {self.api_key[:8]}...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/user",
                    headers={"xi-api-key": self.api_key}
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    print(f"✅ API key valid!")
                    print(f"👤 Account: {user_data.get('email', 'Unknown')}")
                    
                    subscription = user_data.get('subscription', {})
                    print(f"📊 Character limit: {subscription.get('character_limit', 0):,}")
                    print(f"📊 Characters used: {subscription.get('character_count', 0):,}")
                    
                    return True
                else:
                    print(f"❌ Invalid API key: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error testing API key: {e}")
            return False
    
    async def get_voices(self):
        """Get available voices."""
        if not self.api_key:
            print("❌ No API key set!")
            return []
            
        print("\n🎤 Fetching available voices...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers={"xi-api-key": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    voices = data.get('voices', [])
                    
                    # Filter for deep male voices
                    male_voices = []
                    for voice in voices:
                        labels = voice.get('labels', {})
                        if labels.get('gender') == 'male' or 'male' in voice.get('name', '').lower():
                            male_voices.append({
                                'id': voice['voice_id'],
                                'name': voice['name'],
                                'description': labels.get('description', 'No description'),
                                'accent': labels.get('accent', 'Unknown'),
                                'age': labels.get('age', 'Unknown')
                            })
                    
                    return male_voices
                else:
                    print(f"❌ Failed to get voices: {response.status_code}")
                    return []
                    
        except Exception as e:
            print(f"❌ Error fetching voices: {e}")
            return []
    
    async def test_voice_generation(self, voice_id=None, text=None):
        """Test voice generation."""
        if not self.api_key:
            print("❌ No API key set!")
            return False
            
        # Default to Adam voice if not specified
        if not voice_id:
            voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam - deep voice
            
        # Default Optimus Prime text
        if not text:
            text = "I am Optimus Prime, leader of the Autobots. Freedom is the right of all sentient beings. Transform and roll out!"
            
        print(f"\n🎯 Testing voice generation...")
        print(f"📝 Text: {text[:50]}...")
        
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
                    # Save audio file
                    output_path = Path("optimus_test.mp3")
                    output_path.write_bytes(response.content)
                    print(f"✅ Audio generated successfully!")
                    print(f"📁 Saved to: {output_path.absolute()}")
                    print(f"🎵 File size: {len(response.content):,} bytes")
                    print(f"\n▶️  Play the file to hear Optimus Prime voice!")
                    return True
                else:
                    print(f"❌ Failed to generate audio: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error generating voice: {e}")
            return False
    
    async def find_best_optimus_voice(self):
        """Find the best voice for Optimus Prime."""
        voices = await self.get_voices()
        
        if not voices:
            print("❌ No voices available")
            return None
            
        print(f"\n🔍 Found {len(voices)} male voices")
        print("\n🎭 Best voices for Optimus Prime:")
        print("-" * 50)
        
        # Rank voices for Optimus Prime
        recommended = []
        
        for voice in voices:
            score = 0
            reasons = []
            
            # Check for deep/low characteristics
            name_lower = voice['name'].lower()
            desc_lower = voice.get('description', '').lower()
            
            if 'deep' in desc_lower or 'deep' in name_lower:
                score += 3
                reasons.append("deep voice")
            
            if 'strong' in desc_lower or 'authoritative' in desc_lower:
                score += 2
                reasons.append("authoritative")
                
            if 'american' in voice.get('accent', '').lower():
                score += 1
                reasons.append("American accent")
                
            if voice.get('age') in ['middle aged', 'old']:
                score += 1
                reasons.append("mature voice")
                
            voice['score'] = score
            voice['reasons'] = reasons
            
            if score > 0:
                recommended.append(voice)
        
        # Sort by score
        recommended.sort(key=lambda x: x['score'], reverse=True)
        
        # Show top 5
        for i, voice in enumerate(recommended[:5], 1):
            print(f"{i}. {voice['name']}")
            print(f"   ID: {voice['id']}")
            print(f"   Score: {voice['score']} - {', '.join(voice['reasons'])}")
            print(f"   Description: {voice['description'][:100]}")
            print()
        
        if recommended:
            return recommended[0]['id']
        return None
    
    async def setup_env_file(self):
        """Create or update .env file with ElevenLabs settings."""
        env_path = Path(".env")
        
        if not self.api_key:
            print("\n📝 Setting up .env file...")
            api_key = input("Enter your ElevenLabs API key: ").strip()
            
            if not api_key:
                print("❌ No API key provided")
                return False
                
            self.api_key = api_key
        
        # Get best voice
        best_voice = await self.find_best_optimus_voice()
        
        # Write to .env
        env_content = f"""# Optimus Voice Configuration
ELEVENLABS_API_KEY={self.api_key}
ELEVENLABS_VOICE_ID={best_voice or 'pNInz6obpgDQGcFmaJgB'}
ELEVENLABS_MODEL=eleven_turbo_v2_5

# Database (optional)
DATABASE_URL=postgresql://postgres:optimus123@localhost/optimus_db
REDIS_URL=redis://localhost:6379
"""
        
        env_path.write_text(env_content)
        print(f"\n✅ .env file created/updated")
        
        return True

async def main():
    """Run ElevenLabs setup."""
    print("="*60)
    print("🤖 OPTIMUS PRIME VOICE - ELEVENLABS SETUP")
    print("="*60)
    
    setup = ElevenLabsSetup()
    
    # Test API key
    if not await setup.test_api_key():
        # Try to set up
        if not await setup.setup_env_file():
            return
        
        # Test again
        if not await setup.test_api_key():
            print("\n❌ Setup failed. Please check your API key.")
            return
    
    # Find best voice
    best_voice = await setup.find_best_optimus_voice()
    
    if best_voice:
        print(f"\n🎯 Testing with recommended voice...")
        
        # Test generation
        test_text = input("\nEnter text for Optimus to say (or press Enter for default): ").strip()
        
        if not test_text:
            test_text = "Autobots, transform and roll out! We must protect Earth from the Decepticons. Freedom is the right of all sentient beings."
        
        await setup.test_voice_generation(best_voice, test_text)
    
    print("\n" + "="*60)
    print("✅ Setup complete! Your voice agent is ready.")
    print("\nNext steps:")
    print("1. Play optimus_test.mp3 to hear the voice")
    print("2. Run: python test_server.py")
    print("3. Open: http://localhost:8003/frontend/voice-interface.html")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())