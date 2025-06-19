#!/usr/bin/env python3
"""
Voice Control Interface for AI Agent 3D Print System

This module provides voice command recognition and processing capabilities,
allowing users to control the 3D printing system hands-free using natural speech.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import re
from dataclasses import dataclass

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VoiceCommand:
    """Represents a recognized voice command"""
    command: str
    intent: str
    parameters: Dict[str, Any]
    confidence: float
    timestamp: datetime


class VoiceCommandProcessor:
    """Process and execute voice commands for the 3D printing system"""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.VoiceCommandProcessor")
        self.command_handlers: Dict[str, Callable] = {}
        self.intent_patterns = self._initialize_intent_patterns()
        self.is_listening = False
        self.command_history: List[VoiceCommand] = []
        
    def _initialize_intent_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize voice command intent patterns"""
        return {
            "print_request": [
                {
                    "pattern": r"print (?:a )?(.+)",
                    "parameters": ["object_description"]
                },
                {
                    "pattern": r"create (?:a )?(.+)",
                    "parameters": ["object_description"]
                },
                {
                    "pattern": r"make (?:me )?(?:a )?(.+)",
                    "parameters": ["object_description"]
                }
            ],
            "system_control": [
                {
                    "pattern": r"start (?:the )?system",
                    "parameters": []
                },
                {
                    "pattern": r"stop (?:the )?system",
                    "parameters": []
                },
                {
                    "pattern": r"pause (?:the )?print(?:ing)?",
                    "parameters": []
                },
                {
                    "pattern": r"resume (?:the )?print(?:ing)?",
                    "parameters": []
                }
            ],
            "status_inquiry": [
                {
                    "pattern": r"(?:what(?:'s| is) the )?status",
                    "parameters": []
                },
                {
                    "pattern": r"how (?:is|are) (?:the )?print(?:s|ing)?",
                    "parameters": []
                },
                {
                    "pattern": r"show (?:me )?(?:the )?progress",
                    "parameters": []
                }
            ],
            "navigation": [
                {
                    "pattern": r"go to (?:the )?(.+) (?:tab|section|page)",
                    "parameters": ["destination"]
                },
                {
                    "pattern": r"open (?:the )?(.+) (?:tab|section|page)",
                    "parameters": ["destination"]
                },
                {
                    "pattern": r"switch to (?:the )?(.+)",
                    "parameters": ["destination"]
                }
            ],
            "model_viewer": [
                {
                    "pattern": r"show (?:me )?(?:the )?(?:3d )?model",
                    "parameters": []
                },
                {
                    "pattern": r"rotate (?:the )?model",
                    "parameters": []
                },
                {
                    "pattern": r"zoom (?:in|out)(?: on (?:the )?model)?",
                    "parameters": ["direction"]
                },
                {
                    "pattern": r"reset (?:the )?view",
                    "parameters": []
                }
            ],
            "image_upload": [
                {
                    "pattern": r"upload (?:an? )?image",
                    "parameters": []
                },
                {
                    "pattern": r"convert (?:this )?image to 3d",
                    "parameters": []
                },
                {
                    "pattern": r"turn (?:this )?image into (?:a )?model",
                    "parameters": []
                }
            ],
            "settings": [
                {
                    "pattern": r"set (?:the )?quality to (.+)",
                    "parameters": ["quality_level"]
                },
                {
                    "pattern": r"change (?:the )?priority to (.+)",
                    "parameters": ["priority_level"]
                },
                {
                    "pattern": r"use (.+) style",
                    "parameters": ["style"]
                }
            ]
        }
    
    async def process_voice_input(self, text: str) -> Optional[VoiceCommand]:
        """Process voice input text and extract command"""
        try:
            text = text.lower().strip()
            self.logger.info(f"🎤 Processing voice input: '{text}'")
            
            # Find matching intent and extract parameters
            for intent, patterns in self.intent_patterns.items():
                for pattern_info in patterns:
                    pattern = pattern_info["pattern"]
                    param_names = pattern_info["parameters"]
                    
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        # Extract parameters
                        parameters = {}
                        for i, param_name in enumerate(param_names):
                            if i + 1 <= len(match.groups()):
                                parameters[param_name] = match.group(i + 1).strip()
                        
                        # Create voice command
                        command = VoiceCommand(
                            command=text,
                            intent=intent,
                            parameters=parameters,
                            confidence=0.85,  # Simulated confidence
                            timestamp=datetime.now()
                        )
                        
                        self.command_history.append(command)
                        self.logger.info(f"✅ Recognized intent: {intent} with params: {parameters}")
                        
                        return command
            
            # No pattern matched
            self.logger.warning(f"❓ No intent recognized for: '{text}'")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error processing voice input: {e}")
            return None
    
    def register_command_handler(self, intent: str, handler: Callable):
        """Register a handler function for a specific intent"""
        self.command_handlers[intent] = handler
        self.logger.info(f"📝 Registered handler for intent: {intent}")
    
    async def execute_command(self, command: VoiceCommand) -> Dict[str, Any]:
        """Execute a recognized voice command"""
        try:
            if command.intent in self.command_handlers:
                handler = self.command_handlers[command.intent]
                result = await handler(command)
                
                self.logger.info(f"✅ Executed command: {command.intent}")
                return {
                    "success": True,
                    "intent": command.intent,
                    "result": result,
                    "message": f"Command '{command.intent}' executed successfully"
                }
            else:
                self.logger.warning(f"❓ No handler for intent: {command.intent}")
                return {
                    "success": False,
                    "intent": command.intent,
                    "error": f"No handler registered for intent: {command.intent}",
                    "suggestion": self._suggest_alternative_command(command.intent)
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error executing command: {e}")
            return {
                "success": False,
                "intent": command.intent,
                "error": str(e)
            }
    
    def _suggest_alternative_command(self, intent: str) -> str:
        """Suggest alternative commands when intent is not recognized"""
        suggestions = {
            "print_request": "Try saying 'print a cube' or 'create a gear'",
            "system_control": "Try saying 'start system' or 'pause printing'",
            "status_inquiry": "Try saying 'show status' or 'how is the print'",
            "navigation": "Try saying 'go to 3D viewer' or 'open image upload'",
            "model_viewer": "Try saying 'show model' or 'rotate model'",
            "image_upload": "Try saying 'upload image' or 'convert image to 3D'",
            "settings": "Try saying 'set quality to high' or 'change priority to urgent'"
        }
        
        available_intents = list(self.command_handlers.keys())
        if available_intents:
            return f"Available commands: {', '.join(available_intents)}"
        
        return "No voice commands are currently available"
    
    async def start_listening(self):
        """Start voice command listening (simulated)"""
        self.is_listening = True
        self.logger.info("🎤 Voice control activated - listening for commands")
        
        # In a real implementation, this would start microphone capture
        # For demo, we'll just log that it's ready
        return {
            "status": "listening",
            "message": "Voice control is now active",
            "available_intents": list(self.intent_patterns.keys())
        }
    
    async def stop_listening(self):
        """Stop voice command listening"""
        self.is_listening = False
        self.logger.info("🎤 Voice control deactivated")
        
        return {
            "status": "stopped",
            "message": "Voice control has been stopped",
            "commands_processed": len(self.command_history)
        }
    
    def get_command_history(self) -> List[Dict[str, Any]]:
        """Get history of processed voice commands"""
        return [
            {
                "command": cmd.command,
                "intent": cmd.intent,
                "parameters": cmd.parameters,
                "confidence": cmd.confidence,
                "timestamp": cmd.timestamp.isoformat()
            }
            for cmd in self.command_history[-50:]  # Last 50 commands
        ]
    
    def get_voice_stats(self) -> Dict[str, Any]:
        """Get voice control usage statistics"""
        if not self.command_history:
            return {
                "total_commands": 0,
                "success_rate": 0,
                "most_common_intent": None,
                "average_confidence": 0
            }
        
        # Calculate statistics
        total_commands = len(self.command_history)
        intents = [cmd.intent for cmd in self.command_history]
        most_common = max(set(intents), key=intents.count) if intents else None
        avg_confidence = sum(cmd.confidence for cmd in self.command_history) / total_commands
        
        # Intent distribution
        intent_counts = {}
        for intent in intents:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        return {
            "total_commands": total_commands,
            "average_confidence": round(avg_confidence, 2),
            "most_common_intent": most_common,
            "intent_distribution": intent_counts,
            "is_listening": self.is_listening,
            "last_command_time": self.command_history[-1].timestamp.isoformat() if self.command_history else None
        }


class VoiceControlManager:
    """Main manager for voice control functionality"""
    
    def __init__(self, orchestrator=None):
        self.logger = get_logger(f"{__name__}.VoiceControlManager")
        self.processor = VoiceCommandProcessor()
        self.orchestrator = orchestrator
        self.setup_default_handlers()
        
    def setup_default_handlers(self):
        """Setup default command handlers"""
        
        async def handle_print_request(command: VoiceCommand):
            """Handle print request voice commands"""
            description = command.parameters.get("object_description", "")
            if description:
                self.logger.info(f"🖨️ Voice print request: {description}")
                # In real implementation, this would integrate with the print system
                return {
                    "action": "print_request_created",
                    "description": description,
                    "status": "queued"
                }
            return {"error": "No object description provided"}
        
        async def handle_system_control(command: VoiceCommand):
            """Handle system control voice commands"""
            original_command = command.command.lower()
            
            if "start" in original_command:
                return {"action": "system_started", "status": "active"}
            elif "stop" in original_command:
                return {"action": "system_stopped", "status": "inactive"}
            elif "pause" in original_command:
                return {"action": "printing_paused", "status": "paused"}
            elif "resume" in original_command:
                return {"action": "printing_resumed", "status": "active"}
            
            return {"error": "Unknown system control command"}
        
        async def handle_status_inquiry(command: VoiceCommand):
            """Handle status inquiry voice commands"""
            return {
                "action": "status_provided",
                "system_status": "operational",
                "active_jobs": 2,
                "queue_length": 3
            }
        
        async def handle_navigation(command: VoiceCommand):
            """Handle navigation voice commands"""
            destination = command.parameters.get("destination", "").lower()
            
            navigation_map = {
                "3d viewer": "3d-viewer",
                "image upload": "image-to-3d",
                "text request": "text-request",
                "viewer": "3d-viewer",
                "upload": "image-to-3d"
            }
            
            target = navigation_map.get(destination, destination)
            return {
                "action": "navigation",
                "target": target,
                "message": f"Navigating to {destination}"
            }
        
        async def handle_model_viewer(command: VoiceCommand):
            """Handle 3D model viewer voice commands"""
            original_command = command.command.lower()
            
            if "show" in original_command:
                return {"action": "show_model", "status": "displaying"}
            elif "rotate" in original_command:
                return {"action": "rotate_model", "status": "rotating"}
            elif "zoom" in original_command:
                direction = command.parameters.get("direction", "in")
                return {"action": "zoom_model", "direction": direction}
            elif "reset" in original_command:
                return {"action": "reset_view", "status": "reset"}
            
            return {"error": "Unknown viewer command"}
        
        async def handle_image_upload(command: VoiceCommand):
            """Handle image upload voice commands"""
            return {
                "action": "prompt_image_upload",
                "message": "Please select an image file to upload"
            }
        
        async def handle_settings(command: VoiceCommand):
            """Handle settings voice commands"""
            if "quality" in command.parameters:
                quality = command.parameters["quality_level"]
                return {"action": "quality_changed", "quality": quality}
            elif "priority" in command.parameters:
                priority = command.parameters["priority_level"]
                return {"action": "priority_changed", "priority": priority}
            elif "style" in command.parameters:
                style = command.parameters["style"]
                return {"action": "style_changed", "style": style}
            
            return {"error": "Unknown setting command"}
        
        # Register all handlers
        self.processor.register_command_handler("print_request", handle_print_request)
        self.processor.register_command_handler("system_control", handle_system_control)
        self.processor.register_command_handler("status_inquiry", handle_status_inquiry)
        self.processor.register_command_handler("navigation", handle_navigation)
        self.processor.register_command_handler("model_viewer", handle_model_viewer)
        self.processor.register_command_handler("image_upload", handle_image_upload)
        self.processor.register_command_handler("settings", handle_settings)
    
    async def process_voice_command(self, text: str) -> Dict[str, Any]:
        """Process a voice command from text input"""
        try:
            # Process the voice input
            command = await self.processor.process_voice_input(text)
            
            if command:
                # Execute the recognized command
                result = await self.processor.execute_command(command)
                return result
            else:
                return {
                    "success": False,
                    "error": "Command not recognized",
                    "suggestion": "Try commands like 'print a cube', 'show status', or 'go to 3D viewer'"
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error processing voice command: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def start_voice_control(self) -> Dict[str, Any]:
        """Start voice control system"""
        return await self.processor.start_listening()
    
    async def stop_voice_control(self) -> Dict[str, Any]:
        """Stop voice control system"""
        return await self.processor.stop_listening()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current voice control status"""
        return {
            "is_listening": self.processor.is_listening,
            "enabled": True,
            "available_commands": list(self.processor.intent_patterns.keys()),
            "command_count": len(self.processor.command_history)
        }
    
    async def start_listening(self) -> bool:
        """Start voice recognition"""
        try:
            await self.processor.start_listening()
            return True
        except Exception as e:
            self.logger.error(f"Failed to start listening: {e}")
            return False
    
    async def stop_listening(self) -> bool:
        """Stop voice recognition"""
        try:
            await self.processor.stop_listening()
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop listening: {e}")
            return False
    
    async def process_text_command(self, text: str, confidence_threshold: float = 0.7) -> VoiceCommand:
        """Process a text command and return structured result"""
        command = await self.processor.process_voice_input(text)
        if command and command.confidence >= confidence_threshold:
            # Execute the command
            result = await self.processor.execute_command(command)
            command.parameters.update(result)
        return command or VoiceCommand(
            command=text,
            intent="unknown",
            parameters={},
            confidence=0.0,
            timestamp=datetime.now()
        )
    
    async def process_audio_command(self, audio_data: str, confidence_threshold: float = 0.7) -> VoiceCommand:
        """Process audio data and return structured result"""
        # In a real implementation, this would convert audio to text first
        # For now, we'll simulate with a placeholder
        text = "Simulated audio transcription"
        return await self.process_text_command(text, confidence_threshold)
    
    async def get_command_history(self) -> List[VoiceCommand]:
        """Get recent command history"""
        return self.processor.command_history[:10]  # Return last 10 commands
