# 🎙️ Optimus Prime Voice Agent Setup

## Quick Start (5 Minutes)

### 1. Get ElevenLabs API Key (Free Tier Available)

1. Go to https://elevenlabs.io
2. Sign up for a free account
3. Go to Profile → API Key
4. Copy your API key

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API key
ELEVENLABS_API_KEY=your_actual_api_key_here
```

### 3. Install Voice Dependencies

```bash
# Install Python voice packages
pip install pydub pyaudio websockets

# On macOS, you might need:
brew install portaudio

# On Ubuntu/Debian:
sudo apt-get install portaudio19-dev
```

### 4. Run the Voice Agent

```bash
# Start the server with voice capabilities
python test_server.py

# Or run the standalone voice agent
python src/voice/voice_agent.py
```

### 5. Access Voice Interface

Open: http://localhost:8003/frontend/voice-interface.html

## Voice Options

### ElevenLabs Voices (Built-in)

The system comes with several pre-configured deep male voices:

- **Adam** (Default): Deep American male voice
- **Antoni**: Well-rounded male voice
- **Arnold**: Crisp, clear male voice
- **Sam**: Raspy American male voice
- **Marcus**: Deep British male voice
- **Clyde**: War veteran character voice

### Creating a Custom Optimus Prime Voice

For the most authentic Optimus Prime experience:

1. **Voice Design Studio** (Instant):
   - Go to ElevenLabs → Voice Design
   - Set Gender: Male
   - Set Age: Middle-aged
   - Set Accent: American
   - Adjust sliders:
     - Lower Pitch: -2
     - Speaking Style: Authoritative
     - Character: Stoic/Serious

2. **Voice Cloning** (Best Quality):
   - Collect 2-5 minutes of Optimus Prime audio clips
   - Go to ElevenLabs → Voice Lab → Add Voice → Instant Voice Cloning
   - Upload the audio samples
   - Name it "Optimus Prime"
   - Get the voice_id and add to .env:
   ```
   ELEVENLABS_VOICE_ID=your_custom_voice_id
   ```

## Features

### ✅ What Works Now

- **Real-time voice generation** with <300ms latency
- **Text transformation** to Optimus Prime speech patterns
- **Multiple voice options** (6 built-in deep voices)
- **WebSocket streaming** for low-latency responses
- **Browser-based interface** with speech recognition
- **API endpoints** for integration

### 🚧 Coming Soon

- **PlayHT integration** for more voice options
- **Uberduck integration** for character voices
- **Local voice processing** with Coqui TTS
- **Voice activity detection** for natural conversation
- **Emotion and tone control**

## API Usage

### Generate Speech

```javascript
// JavaScript example
async function generateOptimusVoice(text) {
    const response = await fetch('http://localhost:8003/api/voice/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: text,
            transform_text: true
        })
    });
    
    const data = await response.json();
    if (data.success) {
        // Play audio from data.audio_url
        const audio = new Audio(data.audio_url);
        audio.play();
    }
}
```

### WebSocket Streaming

```javascript
// Real-time streaming
const ws = new WebSocket('ws://localhost:8003/api/voice/ws');

ws.onopen = () => {
    ws.send(JSON.stringify({
        action: 'speak',
        text: 'Hello, I need help'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'audio') {
        // Play base64 audio
        const audio = new Audio(`data:audio/mpeg;base64,${data.audio}`);
        audio.play();
    }
};
```

## Cost Information

### ElevenLabs Pricing

- **Free Tier**: 10,000 characters/month (~10 minutes of speech)
- **Starter**: $5/month for 30,000 characters
- **Creator**: $22/month for 100,000 characters
- **Pro**: $99/month for 500,000 characters

### Tips to Reduce Costs

1. Use the turbo model for lower cost
2. Cache common responses
3. Batch similar requests
4. Use shorter, more concise responses

## Troubleshooting

### No Audio Output

```bash
# Check if API key is set
echo $ELEVENLABS_API_KEY

# Test API directly
curl -X POST "https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB" \
  -H "xi-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello", "model_id": "eleven_turbo_v2_5"}' \
  --output test.mp3
```

### Voice Sounds Wrong

- Try different voice IDs from the list
- Adjust voice settings in the API call
- Consider creating a custom voice

### High Latency

- Use the turbo model (eleven_turbo_v2_5)
- Enable streaming mode
- Check your internet connection
- Consider using a closer API region

## Advanced Configuration

### Custom Voice Settings

Edit `src/api/voice_agent_api.py`:

```python
voice_settings = {
    "stability": 0.5,        # 0-1, lower = more variation
    "similarity_boost": 0.8,  # 0-1, higher = more consistent
    "style": 0.0,            # 0-1, emotional expressiveness
    "use_speaker_boost": True # Enhanced clarity
}
```

### Add More Transformations

Edit the `transform_to_optimus()` function to add more speech patterns:

```python
replacements = {
    "your_word": "optimus_version",
    # Add more...
}
```

## The Prime Directive

> "Freedom is the right of all sentient beings... including the freedom to have an awesome AI voice agent!"

Your Optimus Prime Voice Agent is ready to **transform and roll out!** 🤖

---

Need help? Check the logs or open an issue on GitHub.