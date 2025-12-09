# 🎭 Optimus Prime Voice Setup Guide

## Current Implementation

The voice interface now includes an **Optimus Prime Voice Synthesizer** that:
- Uses the deepest available male voice on your system
- Transforms speech patterns to match Optimus Prime's style
- Adds iconic phrases and Cybertronian terminology
- Speaks with authority and gravitas

## Access the Voice Interface

**URL**: http://localhost:8003/frontend/voice-interface.html

## Voice Improvements Applied

### 1. **Speech Transformation**
Common phrases are transformed to Optimus Prime style:
- "Starting" → "Initiating"
- "Hello" → "Greetings, human ally"
- "Complete" → "Mission accomplished"
- "Error" → "System anomaly detected"
- "The Council" → "The Council of Primes"

### 2. **Voice Settings**
- **Pitch**: 0.1 (minimum for deepest voice)
- **Rate**: 0.75 (slower for gravitas)
- **Volume**: 1.0 (full authority)

### 3. **Iconic Phrases**
Randomly adds Optimus Prime signatures:
- "Autobots, roll out!"
- "Freedom is the right of all sentient beings"
- "One shall stand, one shall fall"
- "Till all are one"

## For Even Better Optimus Voice

### Option 1: Uberduck.ai (Recommended) 🎯
```bash
# 1. Sign up at https://uberduck.ai
# 2. Get API key from dashboard
# 3. Search for "Optimus Prime" voice model
# 4. Add to .env:
UBERDUCK_API_KEY=your_key_here
UBERDUCK_VOICE_MODEL=optimus-prime
```

### Option 2: FakeYou.com
```bash
# 1. Visit https://fakeyou.com
# 2. Search for "Optimus Prime" 
# 3. Use their TTS model (TM:7wgq5jfcnh8p)
# 4. API available with account
```

### Option 3: ElevenLabs (Voice Cloning)
```bash
# 1. Sign up at https://elevenlabs.io
# 2. Upload Optimus Prime voice samples
# 3. Train custom voice model
# 4. Use voice ID in API calls
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_custom_voice_id
```

### Option 4: Local Voice Processing
```bash
# Install advanced audio processing
pip install pydub scipy soundfile pyrubberband

# This enables:
# - Pitch shifting
# - Bass boost
# - Robotic modulation
# - Resonance effects
```

## Testing the Voice

### Browser Test Commands:
1. **"Hey Optimus, status report"**
   - Response: "By the Matrix, all systems operational. Transform and roll out!"

2. **"Ask the council about deployment"**
   - Response: "The Council of Primes suggests to proceed with caution..."

3. **"Should I buy a new car seat?"**
   - Response: "Cybertron wisdom indicates: Prioritize safety certifications..."

## Browser Voice Selection

The system automatically selects the deepest voice available:

### Priority Order:
1. Microsoft Mark (Windows)
2. Microsoft David (Windows)
3. Google UK English Male (Chrome)
4. Daniel (macOS)
5. Any voice with "Male" in name

### Check Available Voices:
Open browser console (F12) and run:
```javascript
speechSynthesis.getVoices().forEach(v => 
    console.log(v.name, v.lang)
);
```

## Advanced Customization

### Modify Voice Personality
Edit `/src/voice/optimus_prime_voice.py`:
```python
# Add more transformations
self.speech_patterns = {
    "greeting": ["Custom greeting..."],
    "battle": ["Autobots, attack!"],
    # Add your own
}
```

### Adjust Browser Voice
Edit `/frontend/voice-interface.html`:
```javascript
// Modify voice settings
utterance.pitch = 0.05;  // Even deeper
utterance.rate = 0.6;    // Even slower
```

## Troubleshooting

### Voice Too High?
- Check browser console for selected voice
- Try different browser (Chrome/Edge recommended)
- Install Microsoft Speech Platform if on Windows

### No Deep Voices Available?
**macOS**: System Preferences → Accessibility → Spoken Content → System Voice → Download more voices
**Windows**: Settings → Time & Language → Speech → Add voices
**Linux**: Install `espeak` or `festival` with deep voice packages

### Voice Not Working?
- Enable microphone permissions
- Check browser compatibility (Chrome/Edge best)
- Verify server is running on port 8003

## Future Enhancements

1. **Real Optimus Voice**: Integration with Uberduck/FakeYou API
2. **Voice Effects**: Real-time audio processing for metallic effect
3. **Visual Effects**: Screen flashes blue/red during speech
4. **Sound Effects**: Transformation sounds on commands
5. **Multi-Character**: Switch between Autobots/Decepticons

## The Prime Directive

Remember Optimus Prime's wisdom:
> "Freedom is the right of all sentient beings."

This includes the freedom to have an awesome voice interface that sounds like the leader of the Autobots!

---

**Roll out and test your new voice interface!** 🚛→🤖