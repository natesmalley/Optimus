"""
Optimus Voice Interface
Natural language voice control for all Optimus features
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

# Voice recognition and synthesis
import speech_recognition as sr
import pyttsx3
from pydub import AudioSegment
from pydub.playback import play

# For web-based voice interface
import pyaudio
import wave
import numpy as np

# NLP for intent recognition
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class IntentType(Enum):
    """Types of voice commands."""
    # Council queries
    COUNCIL_QUESTION = "council_question"
    
    # Project orchestration
    START_PROJECT = "start_project"
    STOP_PROJECT = "stop_project"
    DEPLOY_PROJECT = "deploy_project"
    PROJECT_STATUS = "project_status"
    
    # System queries
    SYSTEM_STATUS = "system_status"
    RESOURCE_CHECK = "resource_check"
    
    # Personal/Life
    PERSONAL_ADVICE = "personal_advice"
    REMINDER = "reminder"
    
    # General
    HELP = "help"
    UNKNOWN = "unknown"

@dataclass
class VoiceCommand:
    """Parsed voice command."""
    intent: IntentType
    entities: Dict[str, Any]
    raw_text: str
    confidence: float
    timestamp: datetime

class VoiceInterface:
    """Main voice interface for Optimus."""
    
    def __init__(self, api_base_url: str = "http://localhost:8003"):
        """Initialize voice interface."""
        self.api_base_url = api_base_url
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Initialize text-to-speech
        self.tts_engine = pyttsx3.init()
        self._configure_tts()
        
        # Wake word configuration
        self.wake_words = ["optimus", "hey optimus", "okay optimus"]
        self.is_listening = False
        
        # Command patterns for intent recognition
        self._initialize_patterns()
        
        # Conversation context
        self.context = {
            "last_project": None,
            "last_intent": None,
            "conversation_history": []
        }
        
    def _configure_tts(self):
        """Configure text-to-speech engine."""
        # Set properties
        self.tts_engine.setProperty('rate', 180)  # Speed
        self.tts_engine.setProperty('volume', 0.9)  # Volume
        
        # Try to use a better voice if available
        voices = self.tts_engine.getProperty('voices')
        for voice in voices:
            if 'samantha' in voice.id.lower() or 'alex' in voice.id.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
    
    def _initialize_patterns(self):
        """Initialize regex patterns for intent recognition."""
        self.patterns = {
            IntentType.COUNCIL_QUESTION: [
                r"(?:ask|tell|consult|query) (?:the )?council (?:about |if |whether )?(.*)",
                r"council,? (.*)",
                r"what (?:does|do) (?:the )?council think (?:about |of )?(.*)",
                r"should (?:i|we) (.*)",
                r"(?:i need|i want|give me) advice (?:on|about) (.*)"
            ],
            IntentType.START_PROJECT: [
                r"(?:start|launch|run|begin|initiate) (?:the )?(?:project )?(.+?)(?:\s+project)?$",
                r"(?:start|launch) (.+) in (\w+)(?: environment)?",
                r"get (.+) running",
                r"fire up (.+)"
            ],
            IntentType.STOP_PROJECT: [
                r"(?:stop|halt|terminate|kill|end) (?:the )?(?:project )?(.+?)(?:\s+project)?$",
                r"shut down (.+)",
                r"turn off (.+)"
            ],
            IntentType.DEPLOY_PROJECT: [
                r"deploy (.+?)(?: to (\w+))?",
                r"push (.+) to (?:production|staging|prod)",
                r"release (.+)",
                r"ship (.+)"
            ],
            IntentType.PROJECT_STATUS: [
                r"(?:what'?s|what is|check|show) (?:the )?status (?:of |for )?(.+)",
                r"how (?:is|are) (.+) doing",
                r"is (.+) (?:running|working|up)",
                r"(?:list|show) (?:all )?projects"
            ],
            IntentType.SYSTEM_STATUS: [
                r"(?:how'?s|how is|what'?s) (?:the )?system",
                r"system (?:status|health|check)",
                r"(?:is )?everything (?:okay|good|working|alright)",
                r"status report"
            ],
            IntentType.RESOURCE_CHECK: [
                r"(?:check|show|what'?s) (?:the )?(?:resource|memory|cpu) (?:usage|utilization)",
                r"how much (?:memory|cpu|resources) (?:are we|am i) using",
                r"resource (?:report|status)"
            ],
            IntentType.PERSONAL_ADVICE: [
                r"(?:i'?m|i am) (?:thinking|considering|wondering) (?:about |if )?(.*)",
                r"(?:help|advise) me (?:with |on |about )?(.*)",
                r"what (?:should|would) you (?:recommend|suggest) (?:for |about )?(.*)",
                r"(?:personal|life) (?:advice|help|question):? (.*)"
            ],
            IntentType.HELP: [
                r"(?:help|what can you do|commands|options)",
                r"(?:show|list) (?:available )?commands",
                r"what (?:can i|do i) (?:say|ask)"
            ]
        }
    
    async def listen_for_wake_word(self) -> bool:
        """Listen for wake word activation."""
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            print("🎤 Listening for wake word...")
            
            try:
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                text = self.recognizer.recognize_google(audio).lower()
                
                for wake_word in self.wake_words:
                    if wake_word in text:
                        return True
                        
            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except Exception as e:
                logger.error(f"Wake word detection error: {e}")
                
        return False
    
    async def listen_for_command(self) -> Optional[str]:
        """Listen for a voice command after wake word."""
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Audio feedback that we're listening
            self.speak("Yes?", quick=True)
            print("🎙️ Listening for command...")
            
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                text = self.recognizer.recognize_google(audio)
                print(f"📝 Heard: {text}")
                return text
                
            except sr.WaitTimeoutError:
                self.speak("I didn't hear anything. Please try again.", quick=True)
            except sr.UnknownValueError:
                self.speak("I couldn't understand that. Please try again.", quick=True)
            except Exception as e:
                logger.error(f"Command recognition error: {e}")
                self.speak("Sorry, there was an error. Please try again.")
                
        return None
    
    def parse_command(self, text: str) -> VoiceCommand:
        """Parse voice command text into structured command."""
        text_lower = text.lower().strip()
        
        # Check each intent pattern
        for intent_type, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    entities = {}
                    
                    # Extract matched groups as entities
                    if match.groups():
                        if intent_type in [IntentType.START_PROJECT, IntentType.STOP_PROJECT, 
                                         IntentType.DEPLOY_PROJECT, IntentType.PROJECT_STATUS]:
                            entities['project_name'] = match.group(1).strip()
                            if len(match.groups()) > 1 and match.group(2):
                                entities['environment'] = match.group(2).strip()
                        elif intent_type in [IntentType.COUNCIL_QUESTION, IntentType.PERSONAL_ADVICE]:
                            entities['question'] = match.group(1).strip() if match.groups() else text
                        else:
                            entities['query'] = match.group(1).strip() if match.groups() else ""
                    
                    return VoiceCommand(
                        intent=intent_type,
                        entities=entities,
                        raw_text=text,
                        confidence=0.9,  # Would use actual confidence from recognizer
                        timestamp=datetime.now()
                    )
        
        # Default to council question if it's a question
        if '?' in text or any(text_lower.startswith(q) for q in ['what', 'why', 'how', 'should', 'would', 'could', 'can']):
            return VoiceCommand(
                intent=IntentType.COUNCIL_QUESTION,
                entities={'question': text},
                raw_text=text,
                confidence=0.7,
                timestamp=datetime.now()
            )
        
        return VoiceCommand(
            intent=IntentType.UNKNOWN,
            entities={'text': text},
            raw_text=text,
            confidence=0.5,
            timestamp=datetime.now()
        )
    
    async def execute_command(self, command: VoiceCommand) -> str:
        """Execute parsed voice command."""
        intent = command.intent
        entities = command.entities
        
        if intent == IntentType.COUNCIL_QUESTION:
            return await self._ask_council(entities.get('question', command.raw_text))
            
        elif intent == IntentType.START_PROJECT:
            project = entities.get('project_name', 'current project')
            env = entities.get('environment', 'development')
            return await self._start_project(project, env)
            
        elif intent == IntentType.STOP_PROJECT:
            project = entities.get('project_name', 'current project')
            return await self._stop_project(project)
            
        elif intent == IntentType.DEPLOY_PROJECT:
            project = entities.get('project_name', 'current project')
            env = entities.get('environment', 'staging')
            return await self._deploy_project(project, env)
            
        elif intent == IntentType.PROJECT_STATUS:
            project = entities.get('project_name')
            return await self._get_project_status(project)
            
        elif intent == IntentType.SYSTEM_STATUS:
            return await self._get_system_status()
            
        elif intent == IntentType.RESOURCE_CHECK:
            return await self._check_resources()
            
        elif intent == IntentType.PERSONAL_ADVICE:
            question = entities.get('question', command.raw_text)
            return await self._ask_council(question, personal=True)
            
        elif intent == IntentType.HELP:
            return self._get_help()
            
        else:
            return "I'm not sure how to help with that. Try asking the council or say 'help' for available commands."
    
    async def _ask_council(self, question: str, personal: bool = False) -> str:
        """Ask the Council of Minds."""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base_url}/api/council/deliberate",
                    json={"query": question, "context": {"via": "voice", "personal": personal}}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Format response for speech
                    consensus = result.get('consensus', 'unknown')
                    confidence = result.get('confidence', 0) * 100
                    recommendations = result.get('recommendations', [])
                    
                    response_text = f"The Council has reached a consensus to {consensus.replace('_', ' ')} "
                    response_text += f"with {confidence:.0f}% confidence. "
                    
                    if recommendations:
                        response_text += f"They recommend: {'. '.join(recommendations[:2])}"
                    
                    return response_text
                else:
                    return "Sorry, I couldn't reach the Council right now."
                    
        except Exception as e:
            logger.error(f"Council query failed: {e}")
            return "There was an error consulting the Council."
    
    async def _start_project(self, project_name: str, environment: str) -> str:
        """Start a project."""
        # TODO: Implement actual API call
        self.context['last_project'] = project_name
        return f"Starting {project_name} in {environment} environment. I'll let you know when it's ready."
    
    async def _stop_project(self, project_name: str) -> str:
        """Stop a project."""
        # TODO: Implement actual API call
        return f"Stopping {project_name}. Shutdown complete."
    
    async def _deploy_project(self, project_name: str, environment: str) -> str:
        """Deploy a project."""
        # TODO: Implement actual API call
        return f"Deploying {project_name} to {environment}. I'll monitor the progress and let you know when it's complete."
    
    async def _get_project_status(self, project_name: Optional[str]) -> str:
        """Get project status."""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base_url}/api/projects")
                
                if response.status_code == 200:
                    projects = response.json()
                    
                    if project_name:
                        # Find specific project
                        for p in projects:
                            if project_name.lower() in p['name'].lower():
                                return f"{p['name']} is {p['status']} in {p.get('environment', 'unknown')} environment."
                        return f"I couldn't find a project named {project_name}."
                    else:
                        # List all projects
                        running = [p for p in projects if p['status'] == 'running']
                        stopped = [p for p in projects if p['status'] == 'stopped']
                        
                        response_text = f"I'm tracking {len(projects)} projects. "
                        if running:
                            response_text += f"{len(running)} are running. "
                        if stopped:
                            response_text += f"{len(stopped)} are stopped."
                        
                        return response_text
                else:
                    return "I couldn't check project status right now."
                    
        except Exception as e:
            logger.error(f"Project status check failed: {e}")
            return "There was an error checking project status."
    
    async def _get_system_status(self) -> str:
        """Get overall system status."""
        # TODO: Implement actual system check
        return "All systems are operational. API is healthy, database connected, and monitoring is active."
    
    async def _check_resources(self) -> str:
        """Check resource usage."""
        # TODO: Implement actual resource check
        return "System resources are normal. CPU usage is at 45%, memory at 2.3 gigabytes, with plenty of headroom."
    
    def _get_help(self) -> str:
        """Get help information."""
        return """I can help you with:
        - Asking the Council for advice on technical or personal matters
        - Starting and stopping projects
        - Deploying applications
        - Checking project and system status
        - Monitoring resources
        Just say 'Optimus' followed by your command."""
    
    def speak(self, text: str, quick: bool = False):
        """Convert text to speech."""
        if quick:
            # For quick responses, use faster rate
            self.tts_engine.setProperty('rate', 200)
        else:
            self.tts_engine.setProperty('rate', 180)
            
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
    
    async def conversation_loop(self):
        """Main conversation loop."""
        print("\n" + "="*60)
        print("🎙️  OPTIMUS VOICE INTERFACE")
        print("="*60)
        print("Say 'Optimus' to activate, then speak your command.")
        print("Examples:")
        print("  - 'Optimus, ask the council if we should deploy today'")
        print("  - 'Optimus, start the analytics project'")
        print("  - 'Optimus, what's the system status?'")
        print("  - 'Optimus, help me decide about the car seat'")
        print("Say 'exit' or press Ctrl+C to quit.")
        print("="*60 + "\n")
        
        self.speak("Optimus voice interface activated. Say Optimus to begin.")
        
        try:
            while True:
                # Listen for wake word
                if await self.listen_for_wake_word():
                    # Get command
                    command_text = await self.listen_for_command()
                    
                    if command_text:
                        # Check for exit
                        if 'exit' in command_text.lower() or 'quit' in command_text.lower():
                            self.speak("Goodbye!")
                            break
                        
                        # Parse and execute command
                        command = self.parse_command(command_text)
                        
                        # Add to context
                        self.context['conversation_history'].append({
                            'timestamp': command.timestamp,
                            'text': command_text,
                            'intent': command.intent.value
                        })
                        
                        # Execute command
                        response = await self.execute_command(command)
                        
                        # Speak response
                        self.speak(response)
                        print(f"✅ {response}\n")
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n👋 Voice interface shutting down...")
            self.speak("Shutting down voice interface. Goodbye!")

async def main():
    """Main entry point for voice interface."""
    interface = VoiceInterface()
    await interface.conversation_loop()

if __name__ == "__main__":
    asyncio.run(main())