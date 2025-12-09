"""
Enhanced WebSocket Manager with connection management, event broadcasting,
and channel-based subscriptions for real-time updates.
"""

import json
import asyncio
import uuid
import weakref
from datetime import datetime, timedelta
from typing import Dict, Set, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from redis.asyncio import Redis

from ..config import get_settings, redis_manager, logger


class MessageType(str, Enum):
    """WebSocket message types."""
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    CONNECTION_ESTABLISHED = "connection_established"
    SUBSCRIPTION_CONFIRMED = "subscription_confirmed"
    SUBSCRIPTION_REMOVED = "subscription_removed"
    ERROR = "error"
    DATA = "data"
    NOTIFICATION = "notification"
    SYSTEM_UPDATE = "system_update"
    HEARTBEAT = "heartbeat"


class Channel(str, Enum):
    """Available subscription channels."""
    ORCHESTRATION = "orchestration"
    DEPLOYMENT = "deployment"
    RESOURCES = "resources"
    BACKUP = "backup"
    COUNCIL = "council"
    PROJECTS = "projects"
    RUNTIME = "runtime"
    METRICS = "metrics"
    SYSTEM = "system"
    DELIBERATION = "deliberation"


@dataclass
class ConnectionInfo:
    """WebSocket connection information."""
    connection_id: str
    websocket: WebSocket
    client_ip: str
    user_agent: str
    connected_at: datetime
    last_ping: datetime
    subscriptions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


class WebSocketMessage(BaseModel):
    """WebSocket message schema."""
    type: MessageType
    channel: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    message_id: Optional[str] = None


class WebSocketResponse(BaseModel):
    """WebSocket response schema."""
    type: MessageType
    data: Optional[Dict[str, Any]] = None
    timestamp: str
    message_id: Optional[str] = None
    error: Optional[str] = None


class MessageQueue:
    """Message queue for offline clients."""
    
    def __init__(self, redis_client: Redis, max_size: int = 1000):
        self.redis = redis_client
        self.max_size = max_size
    
    async def enqueue(self, connection_id: str, message: Dict[str, Any]):
        """Add message to queue."""
        try:
            queue_key = f"ws_queue:{connection_id}"
            message_json = json.dumps(message)
            
            pipe = self.redis.pipeline()
            pipe.lpush(queue_key, message_json)
            pipe.ltrim(queue_key, 0, self.max_size - 1)
            pipe.expire(queue_key, 3600)  # 1 hour TTL
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Failed to enqueue message: {e}")
    
    async def dequeue_all(self, connection_id: str) -> List[Dict[str, Any]]:
        """Get all queued messages."""
        try:
            queue_key = f"ws_queue:{connection_id}"
            messages = await self.redis.lrange(queue_key, 0, -1)
            await self.redis.delete(queue_key)
            
            return [json.loads(msg) for msg in reversed(messages)]
            
        except Exception as e:
            logger.error(f"Failed to dequeue messages: {e}")
            return []


class ChannelManager:
    """Channel-based subscription management."""
    
    def __init__(self):
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)  # channel -> connection_ids
        self.connection_channels: Dict[str, Set[str]] = defaultdict(set)  # connection_id -> channels
        self.channel_filters: Dict[str, Dict[str, Any]] = defaultdict(dict)  # channel -> filters
    
    def subscribe(self, connection_id: str, channel: str, filters: Dict[str, Any] = None):
        """Subscribe connection to channel."""
        self.subscriptions[channel].add(connection_id)
        self.connection_channels[connection_id].add(channel)
        
        if filters:
            filter_key = f"{channel}:{connection_id}"
            self.channel_filters[filter_key] = filters
    
    def unsubscribe(self, connection_id: str, channel: str):
        """Unsubscribe connection from channel."""
        self.subscriptions[channel].discard(connection_id)
        self.connection_channels[connection_id].discard(channel)
        
        filter_key = f"{channel}:{connection_id}"
        self.channel_filters.pop(filter_key, None)
    
    def unsubscribe_all(self, connection_id: str):
        """Unsubscribe connection from all channels."""
        channels = self.connection_channels[connection_id].copy()
        for channel in channels:
            self.unsubscribe(connection_id, channel)
    
    def get_subscribers(self, channel: str) -> Set[str]:
        """Get all subscribers for a channel."""
        return self.subscriptions[channel].copy()
    
    def get_channels(self, connection_id: str) -> Set[str]:
        """Get all channels for a connection."""
        return self.connection_channels[connection_id].copy()
    
    def should_send_message(self, connection_id: str, channel: str, data: Dict[str, Any]) -> bool:
        """Check if message should be sent based on filters."""
        filter_key = f"{channel}:{connection_id}"
        filters = self.channel_filters.get(filter_key)
        
        if not filters:
            return True
        
        # Apply filters (can be extended)
        for key, value in filters.items():
            if key in data and data[key] != value:
                return False
        
        return True


class EnhancedWebSocketManager:
    """Enhanced WebSocket connection and message management."""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.connections: Dict[str, ConnectionInfo] = {}
        self.redis = redis_client or redis_manager.client
        self.message_queue = MessageQueue(self.redis)
        self.channel_manager = ChannelManager()
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 300  # 5 minutes
        self._setup_handlers()
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "disconnections": 0,
            "errors": 0
        }
    
    def _setup_handlers(self):
        """Setup message handlers."""
        self.message_handlers = {
            MessageType.PING: self._handle_ping,
            MessageType.SUBSCRIBE: self._handle_subscribe,
            MessageType.UNSUBSCRIBE: self._handle_unsubscribe,
            MessageType.HEARTBEAT: self._handle_heartbeat
        }
    
    async def connect(self, websocket: WebSocket, client_ip: str = None, user_agent: str = None) -> str:
        """Accept new WebSocket connection."""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        now = datetime.now()
        
        connection_info = ConnectionInfo(
            connection_id=connection_id,
            websocket=websocket,
            client_ip=client_ip or "unknown",
            user_agent=user_agent or "unknown",
            connected_at=now,
            last_ping=now
        )
        
        self.connections[connection_id] = connection_info
        self.stats["total_connections"] += 1
        self.stats["active_connections"] += 1
        
        # Send connection confirmation
        await self.send_to_connection(connection_id, {
            "type": MessageType.CONNECTION_ESTABLISHED,
            "data": {
                "connection_id": connection_id,
                "timestamp": now.isoformat()
            }
        })
        
        # Send queued messages if any
        queued_messages = await self.message_queue.dequeue_all(connection_id)
        for message in queued_messages:
            await self.send_to_connection(connection_id, message)
        
        logger.info(f"WebSocket connected: {connection_id} from {client_ip}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect WebSocket."""
        if connection_id in self.connections:
            connection_info = self.connections[connection_id]
            connection_info.is_active = False
            
            # Unsubscribe from all channels
            self.channel_manager.unsubscribe_all(connection_id)
            
            # Close WebSocket if still open
            try:
                if not connection_info.websocket.client_state.closed:
                    await connection_info.websocket.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket {connection_id}: {e}")
            
            del self.connections[connection_id]
            self.stats["active_connections"] -= 1
            self.stats["disconnections"] += 1
            
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific connection."""
        connection_info = self.connections.get(connection_id)
        if not connection_info or not connection_info.is_active:
            # Queue message for offline connection
            await self.message_queue.enqueue(connection_id, message)
            return False
        
        try:
            # Ensure message has required fields
            response = WebSocketResponse(
                type=message.get("type", MessageType.DATA),
                data=message.get("data"),
                timestamp=datetime.now().isoformat(),
                message_id=message.get("message_id", str(uuid.uuid4())),
                error=message.get("error")
            )
            
            await connection_info.websocket.send_text(response.model_dump_json())
            self.stats["messages_sent"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error sending to connection {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False
    
    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any], exclude: Set[str] = None):
        """Broadcast message to all subscribers of a channel."""
        exclude = exclude or set()
        subscribers = self.channel_manager.get_subscribers(channel)
        successful_sends = 0
        
        for connection_id in subscribers:
            if connection_id in exclude:
                continue
                
            # Check filters
            data = message.get("data", {})
            if not self.channel_manager.should_send_message(connection_id, channel, data):
                continue
            
            if await self.send_to_connection(connection_id, message):
                successful_sends += 1
        
        logger.debug(f"Broadcasted to channel {channel}: {successful_sends}/{len(subscribers)} successful")
        return successful_sends
    
    async def broadcast_global(self, message: Dict[str, Any], exclude: Set[str] = None):
        """Broadcast message to all connections."""
        exclude = exclude or set()
        successful_sends = 0
        
        for connection_id, connection_info in self.connections.items():
            if connection_id in exclude or not connection_info.is_active:
                continue
                
            if await self.send_to_connection(connection_id, message):
                successful_sends += 1
        
        logger.debug(f"Global broadcast: {successful_sends}/{len(self.connections)} successful")
        return successful_sends
    
    async def handle_message(self, connection_id: str, message_data: str):
        """Handle incoming WebSocket message."""
        try:
            message_dict = json.loads(message_data)
            message = WebSocketMessage(**message_dict)
            self.stats["messages_received"] += 1
            
            # Update last activity
            if connection_id in self.connections:
                self.connections[connection_id].last_ping = datetime.now()
            
            # Route to appropriate handler
            handler = self.message_handlers.get(message.type)
            if handler:
                await handler(connection_id, message)
            else:
                logger.warning(f"Unknown message type: {message.type}")
                await self.send_to_connection(connection_id, {
                    "type": MessageType.ERROR,
                    "error": f"Unknown message type: {message.type}"
                })
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from connection {connection_id}: {message_data}")
            await self.send_to_connection(connection_id, {
                "type": MessageType.ERROR,
                "error": "Invalid JSON format"
            })
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            self.stats["errors"] += 1
            await self.send_to_connection(connection_id, {
                "type": MessageType.ERROR,
                "error": "Message processing error"
            })
    
    async def _handle_ping(self, connection_id: str, message: WebSocketMessage):
        """Handle ping message."""
        await self.send_to_connection(connection_id, {
            "type": MessageType.PONG,
            "data": {"timestamp": datetime.now().isoformat()}
        })
    
    async def _handle_subscribe(self, connection_id: str, message: WebSocketMessage):
        """Handle channel subscription."""
        channel = message.channel
        if not channel:
            await self.send_to_connection(connection_id, {
                "type": MessageType.ERROR,
                "error": "Channel is required for subscription"
            })
            return
        
        try:
            # Validate channel
            Channel(channel)  # This will raise ValueError if invalid
            
            # Subscribe to channel
            filters = message.data.get("filters") if message.data else None
            self.channel_manager.subscribe(connection_id, channel, filters)
            
            await self.send_to_connection(connection_id, {
                "type": MessageType.SUBSCRIPTION_CONFIRMED,
                "data": {
                    "channel": channel,
                    "filters": filters
                }
            })
            
            logger.debug(f"Connection {connection_id} subscribed to {channel}")
            
        except ValueError:
            await self.send_to_connection(connection_id, {
                "type": MessageType.ERROR,
                "error": f"Invalid channel: {channel}"
            })
    
    async def _handle_unsubscribe(self, connection_id: str, message: WebSocketMessage):
        """Handle channel unsubscription."""
        channel = message.channel
        if not channel:
            await self.send_to_connection(connection_id, {
                "type": MessageType.ERROR,
                "error": "Channel is required for unsubscription"
            })
            return
        
        self.channel_manager.unsubscribe(connection_id, channel)
        
        await self.send_to_connection(connection_id, {
            "type": MessageType.SUBSCRIPTION_REMOVED,
            "data": {"channel": channel}
        })
        
        logger.debug(f"Connection {connection_id} unsubscribed from {channel}")
    
    async def _handle_heartbeat(self, connection_id: str, message: WebSocketMessage):
        """Handle heartbeat message."""
        if connection_id in self.connections:
            self.connections[connection_id].last_ping = datetime.now()
    
    async def cleanup_stale_connections(self):
        """Clean up stale connections."""
        now = datetime.now()
        stale_connections = []
        
        for connection_id, connection_info in self.connections.items():
            if (now - connection_info.last_ping).total_seconds() > self.connection_timeout:
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            logger.info(f"Cleaning up stale connection: {connection_id}")
            await self.disconnect(connection_id)
        
        return len(stale_connections)
    
    async def send_heartbeat(self):
        """Send heartbeat to all connections."""
        message = {
            "type": MessageType.HEARTBEAT,
            "data": {"timestamp": datetime.now().isoformat()}
        }
        
        return await self.broadcast_global(message)
    
    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection information."""
        return self.connections.get(connection_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket statistics."""
        now = datetime.now()
        
        # Calculate channel statistics
        channel_stats = {}
        for channel in Channel:
            subscribers = self.channel_manager.get_subscribers(channel.value)
            channel_stats[channel.value] = len(subscribers)
        
        # Calculate connection age statistics
        connection_ages = []
        for connection_info in self.connections.values():
            age = (now - connection_info.connected_at).total_seconds()
            connection_ages.append(age)
        
        avg_age = sum(connection_ages) / len(connection_ages) if connection_ages else 0
        
        return {
            **self.stats,
            "channel_subscribers": channel_stats,
            "average_connection_age": avg_age,
            "oldest_connection": max(connection_ages) if connection_ages else 0,
            "newest_connection": min(connection_ages) if connection_ages else 0
        }


# Global WebSocket manager instance
websocket_manager = EnhancedWebSocketManager()


# Convenience functions for broadcasting
async def broadcast_orchestration_update(data: Dict[str, Any]):
    """Broadcast orchestration update."""
    await websocket_manager.broadcast_to_channel(Channel.ORCHESTRATION, {
        "type": MessageType.DATA,
        "data": data
    })


async def broadcast_deployment_update(data: Dict[str, Any]):
    """Broadcast deployment update."""
    await websocket_manager.broadcast_to_channel(Channel.DEPLOYMENT, {
        "type": MessageType.DATA,
        "data": data
    })


async def broadcast_resource_update(data: Dict[str, Any]):
    """Broadcast resource update."""
    await websocket_manager.broadcast_to_channel(Channel.RESOURCES, {
        "type": MessageType.DATA,
        "data": data
    })


async def broadcast_system_notification(message: str, level: str = "info"):
    """Broadcast system notification."""
    await websocket_manager.broadcast_to_channel(Channel.SYSTEM, {
        "type": MessageType.NOTIFICATION,
        "data": {
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        }
    })


# Background tasks for WebSocket management
async def websocket_cleanup_task():
    """Background task for cleaning up stale connections."""
    while True:
        try:
            await websocket_manager.cleanup_stale_connections()
            await asyncio.sleep(60)  # Run every minute
        except Exception as e:
            logger.error(f"Error in WebSocket cleanup task: {e}")
            await asyncio.sleep(60)


async def websocket_heartbeat_task():
    """Background task for sending heartbeats."""
    while True:
        try:
            await websocket_manager.send_heartbeat()
            await asyncio.sleep(websocket_manager.heartbeat_interval)
        except Exception as e:
            logger.error(f"Error in WebSocket heartbeat task: {e}")
            await asyncio.sleep(30)