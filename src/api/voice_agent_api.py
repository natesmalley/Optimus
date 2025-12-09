"""
Voice Agent API
Provides endpoints for the Optimus Prime voice agent
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import os
import httpx
import json
import base64
import io
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter(prefix="/api/voice", tags=["voice"])

# Voice configuration
ELEVENLABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY", os.getenv("ELEVENLABS_API_KEY", ""))
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam - deep voice
ELEVENLABS_MODEL = "eleven_turbo_v2_5"  # Fast model for low latency

class TTSRequest(BaseModel):
    """Text-to-speech request."""
    text: str
    voice_id: Optional[str] = None
    streaming: bool = True
    transform_text: bool = True

class VoiceResponse(BaseModel):
    """Voice generation response."""
    success: bool
    audio_url: Optional[str] = None
    error: Optional[str] = None
    transformed_text: Optional[str] = None

def transform_to_optimus(text: str) -> str:
    """Transform text to Optimus Prime speech patterns."""
    replacements = {
        "hello": "Greetings, human ally",
        "goodbye": "Till all are one",
        "yes": "Affirmative",
        "no": "Negative",
        "okay": "Acknowledged",
        "ok": "Acknowledged",
        "starting": "Initiating",
        "stopping": "Terminating",
        "loading": "Energizing",
        "processing": "Analyzing with Cybertronian protocols",
        "error": "System anomaly detected",
        "complete": "Mission accomplished",
        "ready": "All systems operational",
        "help": "Autobots, assist",
        "thank you": "You honor me",
        "thanks": "You honor me",
        "sorry": "Regrettably",
        "please": "If you would",
        "understand": "My processors confirm",
        "think": "My circuits indicate",
        "believe": "The Matrix reveals"
    }
    
    result = text
    for original, replacement in replacements.items():
        result = result.replace(original, replacement)
        result = result.replace(original.capitalize(), replacement)
    
    # Add Optimus flair
    if len(result) < 100:
        import random
        if "?" in result and random.random() < 0.5:
            result = f"Prime wisdom indicates: {result}"
        elif any(word in result.lower() for word in ["battle", "fight", "attack"]):
            result = f"Autobots, {result}"
        elif random.random() < 0.3:
            endings = [
                " Transform and roll out!",
                " One shall stand, one shall fall.",
                " Freedom is the right of all sentient beings.",
                " There is more than meets the eye."
            ]
            if not result.endswith(("!", "?", ".")):
                result += "."
            result += random.choice(endings)
    
    return result

@router.post("/generate")
async def generate_speech(request: TTSRequest):
    """Generate speech using ElevenLabs API."""
    
    if not ELEVENLABS_API_KEY:
        # Return error but also provide alternative
        return VoiceResponse(
            success=False,
            error="ElevenLabs API key not configured. Set ELEVENLABS_API_KEY environment variable.",
            transformed_text=transform_to_optimus(request.text) if request.transform_text else request.text
        )
    
    try:
        # Transform text if requested
        text = transform_to_optimus(request.text) if request.transform_text else request.text
        
        # Use provided voice_id or default
        voice_id = request.voice_id or ELEVENLABS_VOICE_ID
        
        # Call ElevenLabs API
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        data = {
            "text": text,
            "model_id": ELEVENLABS_MODEL,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # For now, return as base64 encoded audio
                audio_base64 = base64.b64encode(response.content).decode('utf-8')
                audio_data_url = f"data:audio/mpeg;base64,{audio_base64}"
                
                return VoiceResponse(
                    success=True,
                    audio_url=audio_data_url,
                    transformed_text=text
                )
            else:
                return VoiceResponse(
                    success=False,
                    error=f"ElevenLabs API error: {response.status_code}",
                    transformed_text=text
                )
                
    except Exception as e:
        return VoiceResponse(
            success=False,
            error=str(e),
            transformed_text=transform_to_optimus(request.text) if request.transform_text else request.text
        )

@router.get("/stream/{voice_id}")
async def stream_speech(voice_id: str, text: str):
    """Stream speech audio."""
    
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    text = transform_to_optimus(text)
    
    async def audio_stream():
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        data = {
            "text": text,
            "model_id": ELEVENLABS_MODEL,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8
            },
            "optimize_streaming_latency": 3
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream('POST', url, json=data, headers=headers) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk
    
    return StreamingResponse(audio_stream(), media_type="audio/mpeg")

@router.websocket("/ws")
async def voice_websocket(websocket: WebSocket):
    """WebSocket for real-time voice interaction."""
    await websocket.accept()
    
    try:
        while True:
            # Receive text from client
            data = await websocket.receive_json()
            
            if data.get("action") == "speak":
                text = data.get("text", "")
                
                # Transform text
                transformed = transform_to_optimus(text)
                
                # Send back transformed text immediately
                await websocket.send_json({
                    "type": "text_transformed",
                    "text": transformed
                })
                
                # Generate audio if API key is available
                if ELEVENLABS_API_KEY:
                    try:
                        # Generate audio
                        voice_id = data.get("voice_id", ELEVENLABS_VOICE_ID)
                        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                        
                        headers = {
                            "Accept": "audio/mpeg",
                            "Content-Type": "application/json",
                            "xi-api-key": ELEVENLABS_API_KEY
                        }
                        
                        payload = {
                            "text": transformed,
                            "model_id": ELEVENLABS_MODEL,
                            "voice_settings": {
                                "stability": 0.5,
                                "similarity_boost": 0.8
                            }
                        }
                        
                        async with httpx.AsyncClient() as client:
                            response = await client.post(url, json=payload, headers=headers)
                            
                            if response.status_code == 200:
                                # Send audio as base64
                                audio_base64 = base64.b64encode(response.content).decode('utf-8')
                                await websocket.send_json({
                                    "type": "audio",
                                    "audio": audio_base64,
                                    "format": "mpeg"
                                })
                            else:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": f"Audio generation failed: {response.status_code}"
                                })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e)
                        })
                else:
                    await websocket.send_json({
                        "type": "no_api_key",
                        "message": "Voice API not configured"
                    })
            
            elif data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")

@router.get("/voices")
async def get_available_voices():
    """Get list of available voices."""
    
    voices = {
        "elevenlabs": {
            "adam": {"id": "pNInz6obpgDQGcFmaJgB", "description": "Deep American male"},
            "antoni": {"id": "ErXwobaYiN019PkySvjV", "description": "Well-rounded male"},
            "arnold": {"id": "VR6AewLTigWG4xSOukaG", "description": "Crisp American male"},
            "sam": {"id": "yoZ06aMxZJJ28mfd3POQ", "description": "Raspy American male"},
            "marcus": {"id": "EXAVITQu4vr4xnSDxMaL", "description": "Deep British male"},
            "clyde": {"id": "2EiwWnXFnvU5JabPnv8n", "description": "War veteran male"}
        },
        "configured": {
            "api_key_set": bool(ELEVENLABS_API_KEY),
            "default_voice": ELEVENLABS_VOICE_ID
        }
    }
    
    return voices

@router.get("/status")
async def get_voice_status():
    """Get voice agent status."""
    return {
        "status": "operational",
        "provider": "elevenlabs",
        "api_configured": bool(ELEVENLABS_API_KEY),
        "model": ELEVENLABS_MODEL,
        "features": {
            "text_transformation": True,
            "streaming": True,
            "websocket": True,
            "multiple_voices": True
        }
    }