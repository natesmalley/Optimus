# 🚀 ElevenLabs Quick Start Guide

## Step 1: Get Your API Key

1. Go to your ElevenLabs dashboard
2. Click on your profile (top right)
3. Click on "API Key" 
4. Copy the API key

## Step 2: Create .env File

Create a file called `.env` in the Optimus directory with:

```
ELEVENLABS_API_KEY=paste_your_api_key_here
ELEVENLABS_VOICE_ID=pNInz6obpgDQGcFmaJgB
```

## Step 3: Test Voice Generation

Run this command to test:

```bash
# Test the voice
venv/bin/python -c "
import os
import httpx
import asyncio
from pathlib import Path

async def test():
    api_key = os.getenv('ELEVENLABS_API_KEY', '')
    if not api_key:
        print('❌ Please add your API key to .env file')
        return
        
    print('🎯 Generating Optimus Prime voice...')
    
    text = 'I am Optimus Prime. Autobots, transform and roll out!'
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB',
            headers={
                'xi-api-key': api_key,
                'Content-Type': 'application/json'
            },
            json={
                'text': text,
                'model_id': 'eleven_turbo_v2_5',
                'voice_settings': {
                    'stability': 0.3,
                    'similarity_boost': 0.8
                }
            }
        )
        
        if response.status_code == 200:
            Path('optimus_test.mp3').write_bytes(response.content)
            print('✅ Audio saved to optimus_test.mp3')
            print('▶️  Open the file to hear Optimus Prime!')
        else:
            print(f'❌ Error: {response.status_code}')

asyncio.run(test())
"
```

## Step 4: Play the Audio

```bash
# On macOS
open optimus_test.mp3

# On Linux
xdg-open optimus_test.mp3

# On Windows
start optimus_test.mp3
```

## Available Voices to Try

Change `ELEVENLABS_VOICE_ID` in your .env file to try different voices:

### Deep Male Voices:
- **Adam**: `pNInz6obpgDQGcFmaJgB` (Deep American)
- **Antoni**: `ErXwobaYiN019PkySvjV` (Well-rounded)
- **Arnold**: `VR6AewLTigWG4xSOukaG` (Crisp)
- **Clyde**: `2EiwWnXFnvU5JabPnv8n` (War veteran)
- **Marcus**: `EXAVITQu4vr4xnSDxMaL` (British)

## Creating Custom Optimus Voice

1. Go to ElevenLabs → Voice Lab
2. Click "Add Voice" → "Voice Design"
3. Set:
   - Gender: Male
   - Age: Middle Aged
   - Accent: American
   - Accent Strength: Medium
4. Generate samples until you get a deep, commanding voice
5. Save it as "Optimus Prime"
6. Copy the voice_id and update your .env file

## Test Complete Integration

Once your .env is set up:

```bash
# Start the server
venv/bin/python test_server.py

# Open in browser
open http://localhost:8003/frontend/voice-interface.html
```

Now when you speak to Optimus, it will use the real ElevenLabs voice!