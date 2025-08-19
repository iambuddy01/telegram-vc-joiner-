import asyncio
import logging
import json
import os
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict, field
import aiofiles
import random
import re
import sys
import tempfile
import subprocess

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, 
    ChannelPrivateError, 
    ChatAdminRequiredError,
    FloodWaitError,
    PhoneNumberInvalidError,
    PhoneCodeInvalidError,
    PasswordHashInvalidError,
    UserDeactivatedError,
    UserRestrictedError,
    UserAlreadyParticipantError
)
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import InputPeerChannel, InputPeerChat, DocumentAttributeAudio, DocumentAttributeVideo
from telethon.tl.functions.phone import CreateGroupCallRequest, JoinGroupCallRequest
from telethon.tl.types import InputPeerUser, DataJSON

# PyTgCalls imports - FIXED
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import AudioPiped, VideoPiped
from pytgcalls.types.input_stream import AudioParameters, VideoParameters

# Try to import AudioVideoPiped for v0.9.7 video with audio support
try:
    from pytgcalls.types import AudioVideoPiped
    AUDIO_VIDEO_PIPED_AVAILABLE = True
except ImportError:
    AUDIO_VIDEO_PIPED_AVAILABLE = False
from pytgcalls.exceptions import (
    NoActiveGroupCall, 
    NotInGroupCallError
)

# Try to import additional exceptions if available
try:
    from pytgcalls.exceptions import GroupCallNotFound
except ImportError:
    # Create a dummy exception if not available
    class GroupCallNotFound(Exception):
        pass

# Try to import quality classes if available
try:
    from pytgcalls.types.input_stream.quality import (
        HighQualityAudio, MediumQualityAudio, LowQualityAudio,
        HighQualityVideo, MediumQualityVideo, LowQualityVideo
    )
    QUALITY_CLASSES_AVAILABLE = True
except ImportError:
    QUALITY_CLASSES_AVAILABLE = False

# Try to import update classes if available
try:
    from pytgcalls.types.update import Update
    from pytgcalls.types.update.stream_audio_ended import StreamAudioEnded
    from pytgcalls.types.update.stream_video_ended import StreamVideoEnded
    UPDATE_CLASSES_AVAILABLE = True
except ImportError:
    UPDATE_CLASSES_AVAILABLE = False

from dotenv import load_dotenv

load_dotenv()

# Logging setup (moved here after imports)
def setup_logging():
    """Setup comprehensive logging"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler
    try:
        file_handler = logging.FileHandler('vc_bot_test.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ Could not setup file logging: {e}")
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# Log import status
if not QUALITY_CLASSES_AVAILABLE:
    logger.warning("⚠️ Quality classes not available in this PyTgCalls version - using fallback")
if not UPDATE_CLASSES_AVAILABLE:
    logger.warning("⚠️ Update classes not available in this PyTgCalls version - using basic handlers")
if not AUDIO_VIDEO_PIPED_AVAILABLE:
    logger.warning("⚠️ AudioVideoPiped not available - using fallback video method")
else:
    logger.info("✅ AudioVideoPiped available - enhanced video support enabled")

# Configuration with validation
def validate_config():
    """Validate required configuration"""
    required_vars = ['API_ID', 'API_HASH', 'BOT_TOKEN', 'OWNER_IDS']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    try:
        api_id = int(os.getenv('API_ID'))
        if api_id <= 0:
            raise ValueError("API_ID must be a positive integer")
    except ValueError:
        raise ValueError("API_ID must be a valid integer")
    
    owner_ids_str = os.getenv('OWNER_IDS', '')
    try:
        owner_ids = [int(x.strip()) for x in owner_ids_str.split(',') if x.strip()]
        if not owner_ids:
            raise ValueError("At least one OWNER_ID must be specified")
    except ValueError:
        raise ValueError("OWNER_IDS must be comma-separated integers")
    
    return {
        'API_ID': api_id,
        'API_HASH': os.getenv('API_HASH'),
        'BOT_TOKEN': os.getenv('BOT_TOKEN'),
        'OWNER_IDS': owner_ids
    }

# Validate configuration on startup
try:
    config = validate_config()
    API_ID = config['API_ID']
    API_HASH = config['API_HASH']
    BOT_TOKEN = config['BOT_TOKEN']
    OWNER_IDS = config['OWNER_IDS']
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    print("Please check your .env file and ensure all required variables are set.")
    sys.exit(1)

# Constants with safe defaults
JOIN_DELAY = max(1, int(os.getenv('JOIN_DELAY', '2')))
LEAVE_DELAY = max(1, int(os.getenv('LEAVE_DELAY', '1')))
MAX_VOLUME = min(300, max(1, int(os.getenv('MAX_VOLUME', '200'))))
VOICE_JOIN_DELAY = max(1, int(os.getenv('VOICE_JOIN_DELAY', '3')))
MAX_ACCOUNTS = int(os.getenv('MAX_ACCOUNTS', '50'))

# Bot initialization with error handling
try:
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
except Exception as e:
    logger.error(f"❌ Failed to initialize bot: {e}")
    sys.exit(1)

# Global variables
user_clients: Dict[str, Tuple[TelegramClient, str]] = {}
pytgcalls_clients: Dict[str, PyTgCalls] = {}
active_operations: Dict[str, Dict[str, Any]] = {}

# Data classes with v2.2.5 support
@dataclass
class VoiceSettings:
    volume: int = 100
    effects: str = "none"
    equalizer: str = "normal"
    is_video: bool = False
    audio_quality: str = "low"  # low, medium, high (default to low for CPU-limited systems)
    video_quality: str = "medium"  # low, medium, high
    audio_bitrate: int = 48000
    video_bitrate: int = 512
    framerate: int = 30
    width: int = 640
    height: int = 480
    
    def __post_init__(self):
        # Validate settings
        self.volume = max(1, min(MAX_VOLUME, self.volume))
        if self.effects not in ["none", "robot", "echo", "chipmunk", "deep", "underwater"]:
            self.effects = "none"
        if self.equalizer not in ["normal", "rock", "vocal", "electronic", "classical", "loud"]:
            self.equalizer = "normal"
        if self.audio_quality not in ["low", "medium", "high"]:
            self.audio_quality = "medium"
        if self.video_quality not in ["low", "medium", "high"]:
            self.video_quality = "medium"
        self.audio_bitrate = max(16000, min(320000, self.audio_bitrate))
        self.video_bitrate = max(128, min(8192, self.video_bitrate))
        self.framerate = max(15, min(60, self.framerate))

    def get_audio_parameters(self) -> AudioParameters:
        """
        Get audio parameters for PyTgCalls.
        Patch: Force 48000 Hz sample rate and stereo for best quality and compatibility.
        """
        if QUALITY_CLASSES_AVAILABLE:
            quality_map = {
                "low": LowQualityAudio(),
                "medium": MediumQualityAudio(),
                "high": HighQualityAudio()
            }
            # Patch: If possible, override sample rate and channels for high quality
            # (PyTgCalls quality classes may not expose this, so fallback below is safer)
            return quality_map.get(self.audio_quality, MediumQualityAudio())
        else:
            # Fallback to custom bitrates and force 48000 Hz, stereo
            bitrate_map = {
                "low": 64000,
                "medium": 128000,
                "high": 320000
            }
            return AudioParameters(
                bitrate=bitrate_map.get(self.audio_quality, 128000),
                sample_rate=48000,
                channels=2
            )
    
    def get_video_parameters(self) -> VideoParameters:
        """Get video parameters for PyTgCalls"""
        if QUALITY_CLASSES_AVAILABLE:
            quality_map = {
                "low": LowQualityVideo(),
                "medium": MediumQualityVideo(),
                "high": HighQualityVideo()
            }
            return quality_map.get(self.video_quality, MediumQualityVideo())
        else:
            # Fallback to custom resolutions
            resolution_map = {
                "low": (360, 240, 15),
                "medium": (640, 480, 30),
                "high": (1280, 720, 30)
            }
            width, height, fps = resolution_map.get(self.video_quality, (640, 480, 30))
            return VideoParameters(
                width=width,
                height=height,
                frame_rate=fps
            )
    
    def get_bitrate_for_quality(self, media_type: str) -> int:
        """Get bitrate based on quality setting"""
        if media_type == "audio":
            quality_map = {
                "low": 64000,
                "medium": 128000,
                "high": 320000
            }
            return quality_map.get(self.audio_quality, 128000)
        else:  # video
            quality_map = {
                "low": 256000,
                "medium": 512000,
                "high": 1024000
            }
            return quality_map.get(self.video_quality, 512000)

# Voice settings storage with thread safety
voice_settings: Dict[int, VoiceSettings] = {}

# Enhanced Voice chat manager with PyTgCalls v2.2.5
class VoiceChatManager:
    def __init__(self):
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self.playlist_queues: Dict[str, List[Dict[str, Any]]] = {}
    
    async def initialize_pytgcalls(self, client: TelegramClient, phone: str) -> PyTgCalls:
        """Initialize PyTgCalls for a client"""
        try:
            if phone in pytgcalls_clients:
                return pytgcalls_clients[phone]
            
            # Initialize PyTgCalls
            pytgcalls = PyTgCalls(client)
            
            # Register event handlers if available
            if UPDATE_CLASSES_AVAILABLE:
                @pytgcalls.on_stream_end()
                async def on_stream_end(client: PyTgCalls, update: Update):
                    """Handle stream end events"""
                    if isinstance(update, (StreamAudioEnded, StreamVideoEnded)):
                        await self._handle_stream_end(update.chat_id, phone)
                
                @pytgcalls.on_kicked()
                async def on_kicked(client: PyTgCalls, chat_id: int):
                    """Handle being kicked from voice chat"""
                    logger.warning(f"⚠️ Kicked from voice chat in {chat_id}")
                    await self._cleanup_call(str(chat_id))
                
                @pytgcalls.on_closed_voice_chat()
                async def on_closed(client: PyTgCalls, chat_id: int):
                    """Handle voice chat being closed"""
                    logger.info(f"🔇 Voice chat closed in {chat_id}")
                    await self._cleanup_call(str(chat_id))
            
            # Start PyTgCalls
            await pytgcalls.start()
            pytgcalls_clients[phone] = pytgcalls
            
            logger.info(f"✅ PyTgCalls initialized for {phone}")
            return pytgcalls
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PyTgCalls for {phone}:")
            logger.error(traceback.format_exc())
            raise
    
    async def _handle_stream_end(self, chat_id: int, phone: str):
        """Handle stream end and auto-play next in queue"""
        try:
            chat_id_str = str(chat_id)
            if chat_id_str in self.playlist_queues and self.playlist_queues[chat_id_str]:
                # Get next item from queue
                next_item = self.playlist_queues[chat_id_str].pop(0)
                settings = VoiceSettings(**next_item.get('settings', {}))
                
                logger.info(f"🎵 Auto-playing next: {next_item['file']}")
                await self.play_media(
                    chat_id, 
                    next_item['file'], 
                    settings, 
                    next_item.get('is_video', False)
                )
            else:
                # No more items in queue, mark as not playing
                if chat_id_str in self.active_calls:
                    self.active_calls[chat_id_str]["playing"] = False
                    logger.info(f"📻 Playlist finished for {chat_id}")
        except Exception as e:
            logger.error(f"❌ Error handling stream end:")
            logger.error(traceback.format_exc())
    
    async def _cleanup_call(self, chat_id_str: str):
        """Cleanup call data"""
        try:
            if chat_id_str in self.active_calls:
                del self.active_calls[chat_id_str]
            if chat_id_str in self.playlist_queues:
                del self.playlist_queues[chat_id_str]
        except Exception as e:
            logger.error(f"❌ Error cleaning up call:")
            logger.error(traceback.format_exc())
    
    async def _get_entity_from_dialogs(self, client: TelegramClient, original_chat_id: str):
        """Helper method to find entity from dialogs when user is already a participant"""
        try:
            logger.info(f"🔍 Searching for entity in user's dialogs for chat: {original_chat_id}")
            
            # Get recent dialogs
            async for dialog in client.iter_dialogs(limit=200):
                try:
                    entity = dialog.entity
                    # Skip if it's a user (not a group/channel)
                    if hasattr(entity, 'first_name'):  # User entity
                        continue
                        
                    # Check if this could be our target chat
                    if hasattr(entity, 'title'):
                        logger.debug(f"🔍 Checking dialog: {entity.title} (ID: {entity.id})")
                        
                        # For invite hash, we need to find the most recent group/supergroup
                        # since we can't directly match the hash to an entity
                        if (hasattr(entity, 'megagroup') and entity.megagroup) or \
                           (hasattr(entity, 'broadcast') and not entity.broadcast):
                            logger.info(f"🎯 Found potential target group: {entity.title}")
                            return entity
                        
                except Exception as e:
                    logger.debug(f"⚠️ Error checking dialog: {str(e)}")
                    continue
            
            logger.warning(f"⚠️ Could not find suitable entity in dialogs")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error searching dialogs:")
            logger.error(traceback.format_exc())
            return None

    async def _find_entity_in_dialogs(self, client: TelegramClient):
        """Find the most recent group/channel entity from dialogs"""
        try:
            dialogs = await client.get_dialogs(limit=20)
            
            # Look for the most recent group or channel
            for dialog in dialogs:
                entity = dialog.entity
                # Skip users, focus on groups and channels
                if hasattr(entity, 'title') and hasattr(entity, 'id'):
                    if hasattr(entity, 'megagroup') or hasattr(entity, 'broadcast'):
                        logger.info(f"🎯 Found potential target: {entity.title}")
                        return entity
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding entity in dialogs:")
            logger.error(traceback.format_exc())
            return None

    async def check_voice_chat(self, client: TelegramClient, chat_id: Union[int, str]) -> bool:
        """Check if voice chat is active in the chat with improved error handling"""
        try:
            # If we already have the entity resolved, use it directly
            if isinstance(chat_id, int):
                entity_id = chat_id
            else:
                # For string IDs, try to convert to int
                try:
                    entity_id = int(chat_id)
                except ValueError:
                    logger.error(f"❌ Invalid chat ID for voice chat check: {chat_id}")
                    return True  # Return True to allow join attempt
            
            logger.info(f"🔍 Checking voice chat status for entity_id: {entity_id}")
            
            try:
                # Get the full chat info to check for voice chat with timeout
                full_chat = await asyncio.wait_for(
                    client.get_entity(entity_id), 
                    timeout=10.0
                )
                
                logger.info(f"📊 Chat info - Type: {type(full_chat).__name__}")
                logger.info(f"📊 Chat attributes: {[attr for attr in dir(full_chat) if not attr.startswith('_')]}")
                
                # Check for active voice chat using multiple methods
                voice_chat_active = False
                
                # Method 1: Check call_active flag
                if hasattr(full_chat, 'call_active') and full_chat.call_active:
                    logger.info(f"✅ Active voice chat detected via call_active flag")
                    voice_chat_active = True
                
                # Method 2: Check call_not_empty flag  
                if hasattr(full_chat, 'call_not_empty') and full_chat.call_not_empty:
                    logger.info(f"✅ Non-empty voice chat detected via call_not_empty flag")
                    voice_chat_active = True
                
                # Method 3: Check for call object (legacy)
                if hasattr(full_chat, 'call') and full_chat.call:
                    logger.info(f"✅ Active voice chat confirmed with call object: {full_chat.call}")
                    voice_chat_active = True
                
                if voice_chat_active:
                    return True
                else:
                    logger.warning(f"⚠️ No active voice chat detected")
                    logger.info(f"📊 call_active: {getattr(full_chat, 'call_active', 'Not found')}")
                    logger.info(f"📊 call_not_empty: {getattr(full_chat, 'call_not_empty', 'Not found')}")
                    logger.info(f"📊 call object: {getattr(full_chat, 'call', 'Not found')}")
                    
                # Log additional info for debugging
                if hasattr(full_chat, 'default_banned_rights'):
                    rights = full_chat.default_banned_rights
                    logger.info(f"📊 Default banned rights: {rights}")
                
                # Check if it's a group/supergroup that could have voice chats
                if hasattr(full_chat, 'megagroup') and full_chat.megagroup:
                    logger.info(f"📢 Supergroup detected - voice chats are possible")
                    # For supergroups, we'll allow the join attempt even if no active call is detected
                    # This is because the voice chat might be in a state that's not properly detected
                    return True
                elif hasattr(full_chat, 'broadcast') and not full_chat.broadcast:
                    logger.info(f"📢 Group detected - voice chats are possible")
                    return True
                elif hasattr(full_chat, 'creator') or hasattr(full_chat, 'admin_rights'):
                    logger.info(f"📢 Admin rights detected - assuming voice chat capability")
                    return True
                else:
                    logger.warning(f"⚠️ Unable to determine voice chat capability")
                    return True  # Default to allowing join attempt
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏳ Timeout checking voice chat status in {entity_id}")
                return True  # Assume voice chat exists to allow join attempt
            except Exception as e:
                logger.warning(f"⚠️ Could not check voice chat status in {entity_id}:")
                logger.error(traceback.format_exc())
                return True  # Assume voice chat exists to allow join attempt
                    
        except Exception as e:
            logger.error(f"❌ Failed to check voice chat in {chat_id}:")
            logger.error(traceback.format_exc())
            return True  # Return True to allow join attempt anyway
    
    async def join_voice_chat(self, client: TelegramClient, chat_id: Union[int, str], phone: str) -> bool:
        """Join a voice chat using PyTgCalls v2.2.5 with improved error handling"""
        try:
            async with self._lock:
                # Normalize chat_id
                if isinstance(chat_id, str):
                    chat_id = chat_id.lstrip('+')
                
                # Check if already in voice chat
                chat_id_str = str(chat_id)
                if chat_id_str in self.active_calls:
                    logger.warning(f"⚠️ Already in voice chat in {chat_id}")
                    return True
                
                # Get or create PyTgCalls instance
                pytgcalls = await self.initialize_pytgcalls(client, phone)
                
                # Enhanced entity resolution with better error handling
                entity = None
                chat_id_int = None
                
                try:
                    # Try different methods to get the entity
                    if isinstance(chat_id, str):
                        # Check if it's an invite hash (no @ prefix, alphanumeric)
                        if re.match(r'^[A-Za-z0-9_-]{10,}$', chat_id) and not chat_id.startswith('@'):
                            logger.info(f"🔗 Detected invite hash: {chat_id[:10]}...")
                            try:
                                # Try to import chat invite (this also joins if not a member)
                                import_result = await client(ImportChatInviteRequest(chat_id))
                                entity = getattr(import_result, 'chat', import_result.chats[0] if hasattr(import_result, 'chats') else None)
                                logger.info(f"✅ Accessed chat via invite hash and joined")
                            except UserAlreadyParticipantError:
                                # User is already a member, get entity from dialogs
                                logger.info(f"✅ User already participant, searching in dialogs...")
                                entity = await self._get_entity_from_dialogs(client, chat_id)
                                
                                # If still not found, try alternative methods
                                if not entity:
                                    logger.info(f"🔄 Trying alternative entity resolution methods...")
                                    
                                    # Method 1: Try to get entity using different URL formats
                                    for url_format in [f"https://t.me/+{chat_id}", f"https://t.me/joinchat/{chat_id}"]:
                                        try:
                                            entity = await client.get_entity(url_format)
                                            logger.info(f"✅ Found entity using URL format: {url_format}")
                                            break
                                        except Exception as url_error:
                                            logger.debug(f"Failed URL format {url_format}: {url_error}")
                                            continue
                                    
                                    # Method 2: If still not found, get the most recent group from dialogs
                                    if not entity:
                                        logger.info(f"🔄 Getting most recent group from dialogs as fallback...")
                                        try:
                                            dialogs = await client.get_dialogs(limit=100)
                                            for dialog in dialogs:
                                                dialog_entity = dialog.entity
                                                # Look for groups/supergroups (not users or channels)
                                                if (hasattr(dialog_entity, 'megagroup') and dialog_entity.megagroup) or \
                                                   (hasattr(dialog_entity, 'broadcast') and not dialog_entity.broadcast and hasattr(dialog_entity, 'title')):
                                                    entity = dialog_entity
                                                    logger.info(f"✅ Using fallback entity: {getattr(entity, 'title', 'Unknown')}")
                                                    break
                                        except Exception as dialog_error:
                                            logger.error(f"❌ Error in dialog fallback: {dialog_error}")
                                
                                if not entity:
                                    logger.warning(f"⚠️ Could not resolve entity for invite hash after all attempts")
                                                
                        # Handle username format
                        elif chat_id.startswith('@'):
                            try:
                                entity = await client.get_entity(chat_id)
                                logger.info(f"✅ Found entity by username: {chat_id}")
                            except Exception as e:
                                logger.error(f"❌ Failed to get entity by username {chat_id}: {e}")
                                return False
                        
                        # Handle t.me links
                        elif 't.me/' in chat_id:
                            try:
                                if '/joinchat/' in chat_id or '/+' in chat_id:
                                    # Extract invite hash from URL
                                    invite_hash = chat_id.split('/')[-1].replace('+', '')
                                    import_result = await client(ImportChatInviteRequest(invite_hash))
                                    entity = getattr(import_result, 'chat', import_result.chats[0] if hasattr(import_result, 'chats') else None)
                                else:
                                    # Extract username from URL
                                    username = chat_id.split('/')[-1]
                                    entity = await client.get_entity(f"@{username}")
                                logger.info(f"✅ Found entity from t.me link")
                            except UserAlreadyParticipantError:
                                # Handle already participant case
                                logger.info(f"✅ User already participant in chat from link")
                                entity = await self._get_entity_from_dialogs(client, chat_id)
                            except Exception as e:
                                logger.error(f"❌ Failed to get entity from link {chat_id}:")
                                logger.error(traceback.format_exc())
                                return False
                        
                        # Try as numeric string
                        else:
                            try:
                                numeric_id = int(chat_id)
                                entity = await client.get_entity(numeric_id)
                                logger.info(f"✅ Found entity by numeric ID")
                            except ValueError:
                                logger.error(f"❌ Invalid chat ID format: {chat_id}")
                                return False
                            except Exception as e:
                                logger.error(f"❌ Failed to get entity by ID {chat_id}:")
                                logger.error(traceback.format_exc())
                                return False
                                
                    # Handle integer chat_id
                    else:
                        try:
                            entity = await client.get_entity(chat_id)
                            logger.info(f"✅ Found entity by integer ID")
                        except Exception as e:
                            logger.error(f"❌ Failed to get entity by integer ID {chat_id}:")
                            logger.error(traceback.format_exc())
                            return False
                    
                    # Validate entity
                    if not entity:
                        logger.error(f"❌ Could not resolve chat entity for {chat_id}")
                        return False
                    
                    chat_id_int = entity.id if hasattr(entity, 'id') else int(chat_id)
                    logger.info(f"✅ Successfully resolved entity: {getattr(entity, 'title', chat_id_int)}")
                    
                except Exception as entity_error:
                    logger.error(f"❌ Entity resolution failed for {chat_id}:")
                    logger.error(traceback.format_exc())
                    
                    # Try fallback method for invite hashes
                    if isinstance(chat_id, str) and re.match(r'^[A-Za-z0-9_-]{10,}$', chat_id):
                        logger.info(f"🔄 Trying fallback method for invite hash...")
                        try:
                            # Search through dialogs to find a matching chat
                            entity = await self._find_entity_in_dialogs(client)
                            if entity:
                                chat_id_int = entity.id
                                logger.info(f"✅ Found entity via fallback method")
                            else:
                                logger.error(f"❌ Fallback method failed")
                                return False
                        except Exception as fallback_error:
                            logger.error(f"❌ Fallback method error:")
                            logger.error(traceback.format_exc())
                            return False
                    else:
                        return False
                
                # Check if this is a broadcast channel (which can't have voice chats)
                if hasattr(entity, 'broadcast') and entity.broadcast:
                    logger.error(f"❌ This is a broadcast channel, not a group - voice chats are not supported")
                    logger.info(f"💡 Voice chats only work in groups and supergroups, not broadcast channels")
                    return False
                
                # Check if there's an active voice chat with better logging
                logger.info(f"🔍 Checking for active voice chat in {getattr(entity, 'title', chat_id_int)}")
                try:
                    voice_chat_active = await self.check_voice_chat(client, chat_id_int)
                    if not voice_chat_active:
                        logger.warning(f"⚠️ No active voice chat detected in {getattr(entity, 'title', chat_id)}")
                        logger.info(f"🔄 Will still attempt to join - sometimes detection isn't perfect...")
                        
                        # Try to create a voice chat if we have admin rights
                        if hasattr(entity, 'admin_rights') and entity.admin_rights and hasattr(entity.admin_rights, 'manage_call') and entity.admin_rights.manage_call:
                            logger.info(f"🎤 Bot has voice chat management rights, attempting to start voice chat...")
                            try:
                                from telethon.tl.functions.phone import CreateGroupCallRequest
                                await client(CreateGroupCallRequest(
                                    peer=entity,
                                    random_id=random.randint(1000000, 9999999)
                                ))
                                logger.info(f"✅ Successfully created voice chat")
                                await asyncio.sleep(2)  # Wait for voice chat to initialize
                            except Exception as create_error:
                                logger.warning(f"⚠️ Could not create voice chat:")
                                logger.debug(traceback.format_exc())
                                logger.info(f"🔄 Proceeding with join attempt anyway...")
                        elif hasattr(entity, 'creator') and entity.creator:
                            logger.info(f"🎤 Bot is group creator, attempting to start voice chat...")
                            try:
                                from telethon.tl.functions.phone import CreateGroupCallRequest
                                await client(CreateGroupCallRequest(
                                    peer=entity,
                                    random_id=random.randint(1000000, 9999999)
                                ))
                                logger.info(f"✅ Successfully created voice chat")
                                await asyncio.sleep(2)  # Wait for voice chat to initialize
                            except Exception as create_error:
                                logger.warning(f"⚠️ Could not create voice chat:")
                                logger.debug(traceback.format_exc())
                                logger.info(f"🔄 Proceeding with join attempt anyway...")
                        
                except Exception as check_error:
                    logger.warning(f"⚠️ Could not check voice chat status:")
                    logger.error(traceback.format_exc())
                    logger.info(f"🔄 Proceeding with join attempt...")
                
                # Join voice chat with PyTgCalls with retry logic
                logger.info(f"🎤 Attempting to join voice chat with PyTgCalls...")
                
                # Check if silence file exists
                silence_path = Path("silence.mp3")
                if not silence_path.exists():
                    logger.warning(f"⚠️ silence.mp3 not found, creating it...")
                    await create_silence_file()
                    if not silence_path.exists():
                        logger.error(f"❌ Failed to create silence.mp3 file")
                        return False
                
                # Retry logic for joining voice chat
                max_retries = 3
                retry_delay = 3
                
                for attempt in range(max_retries):
                    try:
                        logger.info(f"🔄 Join attempt {attempt + 1}/{max_retries}")
                        
                        # Create a silent audio stream to join
                        if QUALITY_CLASSES_AVAILABLE:
                            stream = AudioPiped(
                                "silence.mp3",
                                audio_parameters=MediumQualityAudio()
                            )
                        else:
                            stream = AudioPiped(
                                "silence.mp3",
                                audio_parameters=AudioParameters(bitrate=128000)
                            )
                        
                        logger.info(f"📡 Calling pytgcalls.join_group_call for chat_id: {chat_id_int}")
                        
                        # Add timeout to prevent hanging
                        join_task = pytgcalls.join_group_call(
                            chat_id=chat_id_int,
                            stream=stream
                        )
                        
                        await asyncio.wait_for(join_task, timeout=30.0)
                        logger.info(f"✅ PyTgCalls join_group_call completed successfully")
                        
                        # If we get here, join was successful - record the call
                        me = await client.get_me()
                        self.active_calls[chat_id_str] = {
                            "phone": phone,
                            "joined_at": time.time(),
                            "playing": False,
                            "client": client,
                            "pytgcalls": pytgcalls,
                            "entity_id": chat_id_int,
                            "user_id": me.id,
                            "user_name": f"{me.first_name} {me.last_name or ''}".strip(),
                            "current_stream": stream,
                            "stream_type": "audio",
                            "chat_title": getattr(entity, 'title', 'Unknown Chat')
                        }
                        
                        # Initialize playlist queue
                        self.playlist_queues[chat_id_str] = []
                        
                        logger.info(f"✅ Joined voice chat in {getattr(entity, 'title', chat_id)} with {phone}")
                        return True
                        
                    except NoActiveGroupCall as no_call_error:
                        logger.warning(f"⚠️ No active group call (attempt {attempt + 1}): {no_call_error}")
                        if attempt < max_retries - 1:
                            logger.info(f"🔄 Retrying in {retry_delay} seconds... Voice chat might be starting")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            logger.error(f"❌ No active group call in {getattr(entity, 'title', chat_id)} after {max_retries} attempts")
                            
                            # Try to create voice chat as a last resort if we have admin rights
                            can_create = False
                            if hasattr(entity, 'admin_rights') and entity.admin_rights and hasattr(entity.admin_rights, 'manage_call') and entity.admin_rights.manage_call:
                                can_create = True
                                logger.info(f"🎤 Bot has voice chat management rights")
                            elif hasattr(entity, 'creator') and entity.creator:
                                can_create = True
                                logger.info(f"🎤 Bot is group creator")
                            
                            if can_create:
                                logger.info(f"🎤 Attempting to create voice chat as last resort...")
                                try:
                                    from telethon.tl.functions.phone import CreateGroupCallRequest
                                    await client(CreateGroupCallRequest(
                                        peer=entity,
                                        random_id=random.randint(1000000, 9999999)
                                    ))
                                    logger.info(f"✅ Created voice chat, retrying join...")
                                    await asyncio.sleep(3)
                                    
                                    # One more attempt after creating
                                    await pytgcalls.join_group_call(
                                        chat_id=chat_id_int,
                                        stream=stream
                                    )
                                    
                                    # Record successful call
                                    me = await client.get_me()
                                    self.active_calls[chat_id_str] = {
                                        "phone": phone,
                                        "joined_at": time.time(),
                                        "playing": False,
                                        "client": client,
                                        "pytgcalls": pytgcalls,
                                        "entity_id": chat_id_int,
                                        "user_id": me.id,
                                        "user_name": f"{me.first_name} {me.last_name or ''}".strip(),
                                        "current_stream": stream,
                                        "stream_type": "audio",
                                        "chat_title": getattr(entity, 'title', 'Unknown Chat')
                                    }
                                    self.playlist_queues[chat_id_str] = []
                                    logger.info(f"✅ Successfully joined after creating voice chat!")
                                    return True
                                    
                                except Exception as create_join_error:
                                    logger.warning(f"⚠️ Failed to create and join voice chat:")
                                    logger.debug(traceback.format_exc())
                            else:
                                logger.info(f"⚠️ Bot doesn't have permissions to create voice chats")
                            
                            logger.info(f"💡 **How to Fix 'No Active Group Call' Error:**")
                            logger.info(f"💡 1. **Manual Method:**")
                            logger.info(f"     • Open the group in Telegram")
                            logger.info(f"     • Tap the group name at the top")
                            logger.info(f"     • Tap 'Start Voice Chat' button")
                            logger.info(f"     • Leave the voice chat running")
                            logger.info(f"     • Then retry with the bot")
                            logger.info(f"💡 2. **Check Permissions:**")
                            logger.info(f"     • Bot needs admin rights with 'Manage Voice Chats'")
                            logger.info(f"     • Or someone else must start the voice chat first")
                            logger.info(f"💡 3. **Verify Group Type:**")
                            logger.info(f"     • Voice chats work in groups and supergroups")
                            logger.info(f"     • Channels need to be groups, not broadcast channels")
                            logger.info(f"💡 4. **Test with Known Working Group:**")
                            logger.info(f"     • Try a group where voice chat is already active")
                            logger.info(f"     • This will confirm PyTgCalls is working properly")
                            return False
                    
                    except GroupCallNotFound as not_found_error:
                        logger.warning(f"⚠️ Group call not found (attempt {attempt + 1}): {not_found_error}")
                        if attempt < max_retries - 1:
                            logger.info(f"🔄 Retrying in {retry_delay} seconds... Voice chat might be initializing")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            logger.error(f"❌ Group call not found in {getattr(entity, 'title', chat_id)} after {max_retries} attempts")
                            logger.info(f"💡 Tip: Make sure someone has started a voice chat in the group")
                            return False
                    
                    except asyncio.TimeoutError:
                        logger.warning(f"⏰ Timeout joining voice chat (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            logger.info(f"🔄 Retrying in {retry_delay} seconds... Network might be slow")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            logger.error(f"⏰ Timeout joining voice chat in {getattr(entity, 'title', chat_id)} after {max_retries} attempts")
                            logger.info(f"🔄 This might be due to network issues or PyTgCalls hanging")
                            return False
                    
                    except Exception as e:
                        if "already joined" in str(e).lower():
                            logger.info(f"✅ Already joined voice chat in {getattr(entity, 'title', chat_id)}")
                            # Still record the call as active
                            me = await client.get_me()
                            self.active_calls[chat_id_str] = {
                                "phone": phone,
                                "joined_at": time.time(),
                                "playing": False,
                                "client": client,
                                "pytgcalls": pytgcalls,
                                "entity_id": chat_id_int,
                                "user_id": me.id,
                                "user_name": f"{me.first_name} {me.last_name or ''}".strip(),
                                "current_stream": stream,
                                "stream_type": "audio",
                                "chat_title": getattr(entity, 'title', 'Unknown Chat')
                            }
                            self.playlist_queues[chat_id_str] = []
                            return True
                        else:
                            logger.error(f"❌ Unexpected error in join attempt {attempt + 1}:")
                            logger.error(traceback.format_exc())
                            if attempt < max_retries - 1:
                                logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                continue
                            else:
                                logger.error(f"❌ Failed to join voice chat after {max_retries} attempts")
                                return False
                    
                    except Exception as join_error:
                        logger.error(f"❌ Unexpected error in join attempt {attempt + 1}:")
                        logger.error(traceback.format_exc())
                        if attempt < max_retries - 1:
                            logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            logger.error(f"❌ Failed to join voice chat after {max_retries} attempts")
                            return False
                    
        except Exception as e:
            logger.error(f"❌ Failed to join voice chat in {chat_id}:")
            logger.error(traceback.format_exc())
            return False
    
    async def leave_voice_chat(self, chat_id: Union[int, str]) -> bool:
        """Leave a voice chat using PyTgCalls v2.2.5"""
        try:
            async with self._lock:
                chat_id_str = str(chat_id)
                
                if chat_id_str not in self.active_calls:
                    logger.warning(f"⚠️ Not in voice chat in {chat_id}")
                    return False
                
                call_info = self.active_calls[chat_id_str]
                pytgcalls = call_info.get("pytgcalls")
                chat_id_int = call_info.get("entity_id", int(chat_id))
                
                if pytgcalls:
                    try:
                        await pytgcalls.leave_group_call(chat_id_int)
                        logger.info(f"✅ Left voice chat in {chat_id}")
                    except NotInGroupCallError:
                        logger.warning(f"⚠️ Not in group call in {chat_id}")
                    except Exception as e:
                        logger.error(f"❌ Error leaving voice chat: {e}")
                
                # Clean up
                await self._cleanup_call(chat_id_str)
                return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to leave voice chat in {chat_id}: {e}")
            return False
    
    async def play_media(self, chat_id: Union[int, str], file_path: str, settings: VoiceSettings, is_video: bool = False) -> bool:
        """Play audio or video in a voice chat using PyTgCalls with fixed video streaming"""
        try:
            async with self._lock:
                chat_id_str = str(chat_id)
                
                # Check if file exists
                if not Path(file_path).exists():
                    logger.error(f"❌ Media file not found: {file_path}")
                    return False
                
                if chat_id_str not in self.active_calls:
                    logger.warning(f"⚠️ Not in voice chat in {chat_id}")
                    return False
                
                call_info = self.active_calls[chat_id_str]
                pytgcalls = call_info.get("pytgcalls")
                chat_id_int = call_info.get("entity_id", int(chat_id))
                
                if not pytgcalls:
                    logger.error(f"❌ PyTgCalls not available for {chat_id}")
                    return False
                
                try:
                    # Create appropriate stream based on media type
                    if is_video:
                        logger.info(f"🎬 Creating video stream with audio...")
                        
                        # For PyTgCalls v0.9.7, use AudioVideoPiped for proper video+audio support
                        if AUDIO_VIDEO_PIPED_AVAILABLE and QUALITY_CLASSES_AVAILABLE:
                            # Use AudioVideoPiped with quality settings
                            stream = AudioVideoPiped(
                                file_path,
                                audio_parameters=settings.get_audio_parameters(),
                                video_parameters=settings.get_video_parameters()
                            )
                            logger.info(f"✅ Using AudioVideoPiped with quality parameters")
                        elif AUDIO_VIDEO_PIPED_AVAILABLE:
                            # Use AudioVideoPiped without quality settings
                            stream = AudioVideoPiped(file_path)
                            logger.info(f"✅ Using AudioVideoPiped (basic)")
                        else:
                            # Fallback: Use VideoPiped + separate audio handling
                            logger.warning(f"⚠️ AudioVideoPiped not available, using fallback method")
                            # Create video stream
                            video_stream = VideoPiped(file_path)
                            # Create audio stream from same file
                            audio_stream = AudioPiped(
                                path=file_path,
                                audio_parameters=settings.get_audio_parameters()
                            )
                            
                            # Use video stream as primary, but we'll need special handling
                            stream = video_stream
                            logger.info(f"✅ Using VideoPiped + AudioPiped fallback")
                        
                        stream_type = "video_with_audio"
                        
                        # Change stream
                        await pytgcalls.change_stream(
                            chat_id=chat_id_int,
                            stream=stream
                        )
                        
                        logger.info(f"✅ Video stream with audio configured for v0.9.7")
                        
                    else:
                        # Audio stream only
                        # Patch: Auto-convert to mono, 36kHz, 64kbps MP3 for best CPU performance.
                        def convert_audio_for_playback(input_path: str) -> str:
                            """
                            Convert input audio to mono, 36kHz, 64kbps MP3 for CPU-friendly playback.
                            Returns path to temp file. Cleans up temp file after playback.
                            """
                            temp_dir = tempfile.gettempdir()
                            base = Path(input_path).stem
                            out_path = os.path.join(temp_dir, f"{base}_vcbot_36k64k.mp3")
                            ffmpeg_cmd = [
                                "ffmpeg", "-y", "-i", input_path,
                                "-ac", "1", "-ar", "36000", "-b:a", "64k",
                                out_path
                            ]
                            try:
                                logger.info(f"🔄 Converting audio for playback: {' '.join(ffmpeg_cmd)}")
                                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                                if result.returncode != 0:
                                    logger.error(f"❌ FFmpeg conversion failed: {result.stderr}")
                                    return input_path  # fallback to original
                                if not os.path.exists(out_path) or os.path.getsize(out_path) < 1000:
                                    logger.error("❌ Converted file missing or too small, using original")
                                    return input_path
                                logger.info(f"✅ Audio converted for playback: {out_path}")
                                return out_path
                            except Exception as e:
                                logger.error(f"❌ Exception during audio conversion: {e}")
                                return input_path

                        converted_path = convert_audio_for_playback(file_path)
                        stream = AudioPiped(
                            path=converted_path,
                            audio_parameters=AudioParameters(
                                bitrate=settings.get_bitrate_for_quality("audio")
                            )
                        )
                        stream_type = "audio"
                        
                        # Change stream
                        await pytgcalls.change_stream(
                            chat_id=chat_id_int,
                            stream=stream
                        )
                    
                    # Update call info
                    self.active_calls[chat_id_str].update({
                        "playing": True,
                        "file": file_path,
                        "volume": settings.volume,
                        "effects": settings.effects,
                        "is_video": is_video,
                        "started_at": time.time(),
                        "current_stream": stream,
                        "stream_type": stream_type,
                        "audio_quality": settings.audio_quality,
                        "video_quality": settings.video_quality
                    })
                    
                    logger.info(f"✅ Playing {'video with audio' if is_video else 'audio'} in {chat_id}")
                    logger.info("⚠️ If you still experience glitches, your system may be overloaded. Try lowering audio quality or closing other apps.")
                    logger.info("💡 For best results on weak CPUs, pre-convert your audio to mono, 36kHz, 64kbps MP3 using:")
                    logger.info("   ffmpeg -i input.mp3 -ac 1 -ar 36000 -b:a 64k output.mp3")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Failed to play media:")
                    logger.error(traceback.format_exc())
                    logger.error("⚠️ If you see CPU_OVERLOAD_DETECTED in logs, try lowering audio quality or using mono/low bitrate.")
                    return False
        except Exception as e:
            logger.error(f"❌ Failed to play media in {chat_id}:")
            logger.error(traceback.format_exc())
            return False
    
    async def stop_media(self, chat_id: Union[int, str]) -> bool:
        """Stop media in a voice chat"""
        try:
            async with self._lock:
                chat_id_str = str(chat_id)
                
                if chat_id_str not in self.active_calls:
                    logger.warning(f"⚠️ Not in voice chat in {chat_id}")
                    return False
                
                call_info = self.active_calls[chat_id_str]
                pytgcalls = call_info.get("pytgcalls")
                chat_id_int = call_info.get("entity_id", int(chat_id))
                
                if pytgcalls:
                    try:
                        # Create silence stream to effectively stop media
                        if QUALITY_CLASSES_AVAILABLE:
                            silence_stream = AudioPiped(
                                path="silence.mp3",
                                audio_parameters=MediumQualityAudio()
                            )
                        else:
                            silence_stream = AudioPiped(
                                path="silence.mp3",
                                audio_parameters=AudioParameters(bitrate=128000)
                            )
                        
                        await pytgcalls.change_stream(
                            chat_id=chat_id_int,
                            stream=silence_stream
                        )
                        
                        self.active_calls[chat_id_str].update({
                            "playing": False,
                            "current_stream": silence_stream,
                            "stream_type": "audio"
                        })
                        self.active_calls[chat_id_str].pop("file", None)
                        
                        # Clear playlist queue
                        if chat_id_str in self.playlist_queues:
                            self.playlist_queues[chat_id_str].clear()
                        
                        logger.info(f"✅ Stopped media in {chat_id}")
                        return True
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to stop media: {e}")
                        return False
                else:
                    logger.warning(f"⚠️ PyTgCalls not available for {chat_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Failed to stop media in {chat_id}: {e}")
            return False
    
    async def pause_media(self, chat_id: Union[int, str]) -> bool:
        """Pause media in a voice chat"""
        try:
            async with self._lock:
                chat_id_str = str(chat_id)
                
                if chat_id_str not in self.active_calls:
                    logger.warning(f"⚠️ Not in voice chat in {chat_id}")
                    return False
                
                call_info = self.active_calls[chat_id_str]
                pytgcalls = call_info.get("pytgcalls")
                chat_id_int = call_info.get("entity_id", int(chat_id))
                
                if pytgcalls:
                    try:
                        await pytgcalls.pause_stream(chat_id_int)
                        self.active_calls[chat_id_str]["playing"] = False
                        logger.info(f"✅ Paused media in {chat_id}")
                        return True
                    except Exception as e:
                        logger.error(f"❌ Failed to pause media:")
                        logger.error(traceback.format_exc())
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Failed to pause media in {chat_id}:")
            logger.error(traceback.format_exc())
            return False
    
    async def resume_media(self, chat_id: Union[int, str]) -> bool:
        """Resume media in a voice chat"""
        try:
            async with self._lock:
                chat_id_str = str(chat_id)
                
                if chat_id_str not in self.active_calls:
                    logger.warning(f"⚠️ Not in voice chat in {chat_id}")
                    return False
                
                call_info = self.active_calls[chat_id_str]
                pytgcalls = call_info.get("pytgcalls")
                chat_id_int = call_info.get("entity_id", int(chat_id))
                
                if pytgcalls:
                    try:
                        await pytgcalls.resume_stream(chat_id_int)
                        self.active_calls[chat_id_str]["playing"] = True
                        logger.info(f"✅ Resumed media in {chat_id}")
                        return True
                    except Exception as e:
                        logger.error(f"❌ Failed to resume media:")
                        logger.error(traceback.format_exc())
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Failed to resume media in {chat_id}:")
            logger.error(traceback.format_exc())
            return False
    
    async def set_volume(self, chat_id: Union[int, str], volume: int) -> bool:
        """Set volume for a voice chat - v2.2.5"""
        try:
            async with self._lock:
                chat_id_str = str(chat_id)
                
                if chat_id_str not in self.active_calls:
                    logger.warning(f"⚠️ Not in voice chat in {chat_id}")
                    return False
                
                call_info = self.active_calls[chat_id_str]
                pytgcalls = call_info.get("pytgcalls")
                chat_id_int = call_info.get("entity_id", int(chat_id))
                
                if pytgcalls:
                    try:
                        # Volume in PyTgCalls v2.2.5 is 0-200
                        pytgcalls_volume = min(200, max(0, volume))
                        await pytgcalls.change_volume_call(chat_id_int, pytgcalls_volume)
                        self.active_calls[chat_id_str]["volume"] = volume
                        logger.info(f"✅ Set volume to {volume}% in {chat_id}")
                        return True
                    except Exception as e:
                        logger.error(f"❌ Failed to set volume:")
                        logger.error(traceback.format_exc())
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Failed to set volume in {chat_id}:")
            logger.error(traceback.format_exc())
            return False
    
    async def add_to_queue(self, chat_id: Union[int, str], file_path: str, settings: VoiceSettings, is_video: bool = False) -> bool:
        """Add media to playlist queue - NEW in v2.2.5"""
        try:
            chat_id_str = str(chat_id)
            
            if not Path(file_path).exists():
                logger.error(f"❌ Media file not found: {file_path}")
                return False
            
            if chat_id_str not in self.playlist_queues:
                self.playlist_queues[chat_id_str] = []
            
            queue_item = {
                "file": file_path,
                "settings": asdict(settings),
                "is_video": is_video,
                "added_at": time.time()
            }
            
            self.playlist_queues[chat_id_str].append(queue_item)
            
            logger.info(f"✅ Added to queue: {file_path} for {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add to queue:")
            logger.error(traceback.format_exc())
            return False
    
    async def skip_current(self, chat_id: Union[int, str]) -> bool:
        """Skip current track and play next in queue - NEW in v2.2.5"""
        try:
            chat_id_str = str(chat_id)
            
            if chat_id_str in self.playlist_queues and self.playlist_queues[chat_id_str]:
                # Simulate stream end to trigger next track
                await self._handle_stream_end(int(chat_id), self.active_calls[chat_id_str].get("phone", ""))
                return True
            else:
                # Just stop current track
                return await self.stop_media(chat_id)
                
        except Exception as e:
            logger.error(f"❌ Failed to skip track:")
            logger.error(traceback.format_exc())
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get voice chat status with v2.2.5 features"""
        return {
            "active_calls": len(self.active_calls),
            "calls": dict(self.active_calls),
            "total_queued": sum(len(queue) for queue in self.playlist_queues.values()),
            "queue_info": {chat_id: len(queue) for chat_id, queue in self.playlist_queues.items()}
        }
    
    async def cleanup_client(self, phone: str):
        """Cleanup PyTgCalls client"""
        try:
            if phone in pytgcalls_clients:
                pytgcalls = pytgcalls_clients[phone]
                # Leave all calls for this client
                for chat_id, call_info in list(self.active_calls.items()):
                    if call_info.get("phone") == phone:
                        await self.leave_voice_chat(chat_id)
                
                # Stop pytgcalls
                try:
                    await pytgcalls.stop()
                except:
                    pass
                
                del pytgcalls_clients[phone]
                logger.info(f"✅ Cleaned up PyTgCalls for {phone}")
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up PyTgCalls for {phone}:")
            logger.error(traceback.format_exc())

# Initialize voice chat manager
voice_manager = VoiceChatManager()

# Create silence file for joining voice chats
async def create_silence_file():
    """Create a silence audio file for voice chat operations"""
    silence_path = Path("silence.mp3")
    if silence_path.exists():
        logger.info("✅ silence.mp3 already exists")
        return
        
    try:
        logger.info("🔧 Creating silence.mp3 file...")
        
        # Try to create using ffmpeg first
        try:
            import subprocess
            result = subprocess.run([
                "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", 
                "-t", "1", "-c:a", "libmp3lame", "-b:a", "128k", "-y", str(silence_path)
            ], check=True, capture_output=True, text=True)
            
            if silence_path.exists() and silence_path.stat().st_size > 0:
                logger.info("✅ Created silence.mp3 using ffmpeg")
                return
            else:
                raise Exception("FFmpeg created empty file")
                
        except (subprocess.CalledProcessError, FileNotFoundError, Exception) as ffmpeg_error:
            logger.warning(f"⚠️ FFmpeg method failed: {ffmpeg_error}")
            
            # Fallback: Create a minimal MP3 file manually
            logger.info("🔄 Creating basic silence file as fallback...")
            
            # This is a minimal MP3 header for a 1-second silent file
            # MP3 header + silent frames
            mp3_data = bytearray([
                # MP3 Header - Layer 3, 44.1kHz, 128kbps, Stereo
                0xFF, 0xFB, 0x90, 0x00,  # Sync word + header
                0x00, 0x00, 0x00, 0x00,  # CRC + padding
            ])
            
            # Add silent frames (about 1 second worth)
            silent_frame = bytes([0x00] * 417)  # Standard MP3 frame size for 128kbps
            for _ in range(38):  # Approximately 1 second at 44.1kHz
                mp3_data.extend(silent_frame)
            
            with open(silence_path, 'wb') as f:
                f.write(mp3_data)
            
            if silence_path.exists() and silence_path.stat().st_size > 0:
                logger.info("✅ Created basic silence.mp3 file")
            else:
                raise Exception("Failed to create silence file")
                
    except Exception as e:
        logger.error(f"❌ Failed to create silence.mp3: {e}")
        
        # Last resort: create a very basic file
        try:
            with open(silence_path, 'wb') as f:
                # Write minimal data that might work
                f.write(b'\xff\xfb\x90\x00' + b'\x00' * 2000)
            logger.warning("⚠️ Created minimal silence file - may not work properly")
        except Exception as final_error:
            logger.error(f"❌ Complete failure creating silence file: {final_error}")
            raise

# FSM States
class AccountStates(StatesGroup):
    phone = State()
    otp = State()
    password = State()

class RemoveAccountStates(StatesGroup):
    select_account = State()
    confirm = State()

class VoiceChatStates(StatesGroup):
    target_chat = State()
    account_selection = State()
    media_file = State()
    volume_setting = State()

class MemberManagementStates(StatesGroup):
    target_group = State()
    account_selection = State()
    account_count = State()
    confirm_action = State()

class MediaStates(StatesGroup):
    target_chat = State()
    media_file = State()

class QualityStates(StatesGroup):
    audio_quality = State()
    video_quality = State()

# Utility functions
def normalize_phone(phone: str) -> str:
    """Normalize phone number"""
    if not phone:
        raise ValueError("Phone number cannot be empty")
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Remove + and ensure we have only digits
    digits_only = re.sub(r'[^\d]', '', cleaned)
    
    if len(digits_only) < 10:
        raise ValueError("Phone number is too short")
    
    return digits_only

def is_owner(user_id: int) -> bool:
    """Check if user is owner"""
    return user_id in OWNER_IDS

async def safe_file_operation(file_path: str, operation: str, data: Any = None) -> Any:
    """Safely perform file operations with error handling"""
    try:
        if operation == "write":
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
            return True
        elif operation == "read":
            if not Path(file_path).exists():
                return {}
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content) if content.strip() else {}
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error in {file_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"❌ File operation error ({operation}) in {file_path}: {e}")
        return {} if operation == "read" else False

async def save_users():
    """Save user sessions with error handling"""
    try:
        data = {}
        for phone, (client, session_string) in user_clients.items():
            data[phone] = session_string
        
        success = await safe_file_operation('users_test.json', 'write', data)
        if success:
            logger.info(f"✅ Saved {len(data)} user sessions")
        else:
            logger.error("❌ Failed to save user sessions")
    except Exception as e:
        logger.error(f"❌ Error saving users:")
        logger.error(traceback.format_exc())

async def load_users():
    """Load user sessions with comprehensive error handling"""
    try:
        data = await safe_file_operation('users_test.json', 'read')
        if not data:
            logger.info("📂 No existing user data found")
            return
        
        loaded_count = 0
        failed_count = 0
        
        for phone, session_string in data.items():
            try:
                if not session_string or not isinstance(session_string, str):
                    logger.warning(f"⚠️ Invalid session data for {phone}")
                    failed_count += 1
                    continue
                
                client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
                await client.connect()
                
                if await client.is_user_authorized():
                    user_clients[phone] = (client, session_string)
                    loaded_count += 1
                    logger.info(f"✅ Loaded account: {phone}")
                else:
                    logger.warning(f"⚠️ Session expired for {phone}")
                    await client.disconnect()
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Failed to load account {phone}:")
                logger.error(traceback.format_exc())
                failed_count += 1
                
        logger.info(f"📊 Loaded {loaded_count} accounts, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"❌ Error loading users:")
        logger.error(traceback.format_exc())

def save_voice_settings():
    """Save voice settings with error handling"""
    try:
        data = {}
        for chat_id, settings in voice_settings.items():
            data[str(chat_id)] = asdict(settings)
        
        with open('voice_settings_test.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Saved voice settings for {len(voice_settings)} chats")
    except Exception as e:
        logger.error(f"❌ Failed to save voice settings:")
        logger.error(traceback.format_exc())

def load_voice_settings():
    """Load voice settings with error handling"""
    try:
        if not Path('voice_settings_test.json').exists():
            logger.info("📂 No existing voice settings found")
            voice_settings[0] = VoiceSettings()
            return
        
        with open('voice_settings_test.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for chat_id, settings in data.items():
            try:
                voice_settings[int(chat_id)] = VoiceSettings(**settings)
            except (TypeError, ValueError) as e:
                logger.warning(f"⚠️ Invalid voice settings for chat {chat_id}: {e}")
                voice_settings[int(chat_id)] = VoiceSettings()
        
        logger.info(f"✅ Loaded voice settings for {len(voice_settings)} chats")
        
    except Exception as e:
        logger.error(f"❌ Failed to load voice settings:")
        logger.error(traceback.format_exc())
        # Set default settings
        voice_settings[0] = VoiceSettings()

def get_voice_settings(chat_id: int) -> VoiceSettings:
    """Get voice settings for a chat"""
    if chat_id not in voice_settings:
        voice_settings[chat_id] = VoiceSettings()
    
    return voice_settings[chat_id]

# Updated extract_chat_id function with better invite hash handling
async def extract_chat_id(chat_input: str) -> Optional[Union[str, int]]:
    """Extract chat ID from various formats with improved validation"""
    if not chat_input or not chat_input.strip():
        return None
    
    chat_input = chat_input.strip()
    
    try:
        # Handle usernames (must start with @)
        if chat_input.startswith('@'):
            username = chat_input[1:]
            if re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', username):
                return chat_input
            else:
                logger.warning(f"⚠️ Invalid username format: {chat_input}")
                return None
        
        # Handle t.me links
        if 'https://t.me/' in chat_input or 'http://t.me/' in chat_input or 't.me/' in chat_input:
            try:
                # Remove protocol if present
                url_part = chat_input.replace('https://', '').replace('http://', '')
                
                if '/joinchat/' in url_part or '/+' in url_part:
                    # Private invite link
                    if '/joinchat/' in url_part:
                        invite_hash = url_part.split('/joinchat/')[-1]
                    else:  # /+ format
                        invite_hash = url_part.split('/+')[-1]
                    
                    # Clean up any URL parameters
                    invite_hash = invite_hash.split('?')[0].split('#')[0]
                    
                    if len(invite_hash) >= 10 and re.match(r'^[a-zA-Z0-9_-]+$', invite_hash):
                        logger.info(f"🔗 Extracted invite hash: {invite_hash[:10]}...")
                        return invite_hash
                    else:
                        logger.warning(f"⚠️ Invalid invite hash in URL: {chat_input}")
                        return None
                else:
                    # Public username link
                    username = url_part.split('/')[-1].split('?')[0].split('#')[0]
                    if username and re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', username):
                        return f'@{username}'
                    else:
                        logger.warning(f"⚠️ Invalid username in URL: {chat_input}")
                        return None
            except (ValueError, IndexError) as e:
                logger.error(f"❌ Error parsing t.me URL '{chat_input}':")
                logger.error(traceback.format_exc())
                return None
        
        # Handle direct invite hashes (no URL, just the hash)
        # Remove leading + if present
        clean_input = chat_input.lstrip('+')
        
        # Check if it looks like an invite hash (alphanumeric, 10+ chars, not all digits)
        if (re.match(r'^[a-zA-Z0-9_-]{10,50}$', clean_input) and 
            not clean_input.isdigit() and 
            any(c.isalpha() for c in clean_input)):
            logger.info(f"🔗 Detected direct invite hash: {clean_input[:10]}...")
            return clean_input
        
        # Handle numeric IDs (negative for supergroups, positive for channels)
        if clean_input.lstrip('-').isdigit():
            chat_id = int(clean_input)
            # Basic validation: Telegram chat IDs are usually quite large
            if abs(chat_id) > 1000000:
                logger.info(f"🔢 Detected numeric chat ID: {chat_id}")
                return chat_id
            else:
                logger.warning(f"⚠️ Chat ID seems too small: {chat_id}")
                return chat_id  # Return anyway, let Telegram handle validation
        
        # If nothing matches, it might be a malformed input
        logger.warning(f"⚠️ Could not parse chat input: '{chat_input}'")
        logger.info(f"💡 Supported formats: @username, -1001234567890, https://t.me/joinchat/xyz, xyz123")
        return None
                
    except (ValueError, IndexError) as e:
        logger.error(f"❌ Error parsing chat input '{chat_input}':")
        logger.error(traceback.format_exc())
        return None

async def is_user_participant(client: TelegramClient, chat_id: Union[str, int]) -> bool:
    """Check if user is already a participant in the chat"""
    try:
        logger.info(f"🔍 Checking if user is participant in: {chat_id}")
        
        # For invite hashes, we need to check differently
        if isinstance(chat_id, str) and re.match(r'^[A-Za-z0-9_-]{10,}$', chat_id):
            logger.info(f"🔗 Checking participation for invite hash: {chat_id[:10]}...")
            
            # Try to import the chat invite to check participation status
            try:
                # This will throw UserAlreadyParticipantError if already a member
                await client(ImportChatInviteRequest(chat_id))
                # If we get here, we just joined (weren't a participant before)
                logger.info(f"✅ Successfully joined chat via invite hash")
                return True
            except UserAlreadyParticipantError:
                # We're already a participant
                logger.info(f"✅ User is already a participant (via invite hash)")
                return True
            except (ChannelPrivateError, ChatAdminRequiredError):
                logger.info(f"❌ Cannot access chat (private or admin required)")
                return False
            except Exception as e:
                logger.warning(f"⚠️ Error checking participation via invite: {e}")
                # Fallback: check if we have any groups in dialogs
                try:
                    async for dialog in client.iter_dialogs(limit=50):
                        entity = dialog.entity
                        if hasattr(entity, 'title') and hasattr(entity, 'id'):
                            if (hasattr(entity, 'megagroup') and entity.megagroup) or \
                               (hasattr(entity, 'broadcast') and not entity.broadcast):
                                logger.info(f"✅ Found group in dialogs, assuming participation possible")
                                return True
                except:
                    pass
                return False
        else:
            # For usernames and numeric IDs, try direct access
            try:
                entity = await client.get_entity(chat_id)
                logger.info(f"✅ Can access entity directly: {getattr(entity, 'title', chat_id)}")
                return True  # If we can get the entity, we're likely a participant
            except (ChannelPrivateError, ChatAdminRequiredError):
                logger.info(f"❌ Cannot access entity (private or admin required)")
                return False  # We're not a participant
            except Exception as e:
                logger.warning(f"⚠️ Error accessing entity: {e}")
                return False  # Unknown error, assume not participant
                
    except Exception as e:
        logger.error(f"❌ Participant check error for {chat_id}:")
        logger.error(traceback.format_exc())
        return False

async def safe_telegram_operation(operation_func, *args, **kwargs):
    """Safely execute Telegram operations with comprehensive error handling"""
    max_retries = 3
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            return await operation_func(*args, **kwargs)
            
        except FloodWaitError as e:
            if attempt < max_retries - 1:
                wait_time = min(e.seconds, 300)  # Cap at 5 minutes
                logger.warning(f"⏳ Flood wait: {wait_time}s, attempt {attempt + 1}")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise
                
        except (UserDeactivatedError, UserRestrictedError) as e:
            logger.error(f"❌ User account issue: {e}")
            raise
            
        except ChannelPrivateError:
            logger.error("❌ Channel is private or doesn't exist")
            raise
            
        except ChatAdminRequiredError:
            logger.error("❌ Admin rights required for this operation")
            raise
            
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"⚠️ Operation failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
                continue
            else:
                raise

async def join_chat(client: TelegramClient, chat_id: Union[str, int]) -> bool:
    """Join a chat with improved membership checking"""
    try:
        logger.info(f"🚀 Attempting to join chat: {chat_id}")
        
        # For invite hashes, the is_user_participant function will handle joining
        # if not already a participant
        if isinstance(chat_id, str) and re.match(r'^[A-Za-z0-9_-]{10,}$', chat_id):
            logger.info(f"🔗 Processing invite hash join...")
            participation_result = await is_user_participant(client, chat_id)
            if participation_result:
                logger.info(f"✅ Successfully joined/already in chat via invite hash")
                return True
            else:
                logger.error(f"❌ Failed to join via invite hash")
                return False
        
        # For other formats, check participation first
        if await is_user_participant(client, chat_id):
            logger.info(f"✅ User is already a participant in {chat_id}")
            return True
        
        # If not a participant, try to join
        async def _join_operation():
            if isinstance(chat_id, str):
                if chat_id.startswith('@'):
                    logger.info(f"🔍 Joining public channel: {chat_id}")
                    await client(JoinChannelRequest(chat_id))
                else:
                    logger.info(f"🔍 Joining via invite link: {chat_id[:20]}...")
                    await client(ImportChatInviteRequest(chat_id))
            else:
                logger.info(f"🔍 Joining chat with ID: {chat_id}")
                entity = await client.get_entity(chat_id)
                await client(JoinChannelRequest(entity))
        
        await safe_telegram_operation(_join_operation)
        logger.info(f"✅ Successfully joined chat {chat_id}")
        
        # Verify we can access the chat now
        try:
            entity = await client.get_entity(chat_id)
            logger.info(f"✅ Confirmed access to chat: {getattr(entity, 'title', chat_id)}")
        except Exception as verify_error:
            logger.warning(f"⚠️ Joined but cannot verify access: {verify_error}")
        
        return True
        
    except ChannelPrivateError:
        logger.error(f"❌ Channel/group is private or doesn't exist: {chat_id}")
        return False
    except ChatAdminRequiredError:
        logger.error(f"❌ Admin rights required to join: {chat_id}")
        return False
    except FloodWaitError as e:
        logger.error(f"❌ Rate limited for {e.seconds} seconds: {chat_id}")
        return False
    except UserAlreadyParticipantError:
        logger.info(f"✅ User is already a participant in chat: {chat_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to join chat {chat_id}: {e}")
        logger.error(traceback.format_exc())
        return False

async def leave_chat(client: TelegramClient, chat_id: Union[str, int]) -> bool:
    """Leave a chat with comprehensive error handling"""
    try:
        async def _leave_operation():
            entity = await client.get_entity(chat_id)
            await client(LeaveChannelRequest(entity))
        
        await safe_telegram_operation(_leave_operation)
        logger.info(f"✅ Successfully left chat {chat_id}")
        return True
        
    except ChannelPrivateError:
        logger.error(f"❌ Cannot leave - channel/group is private or doesn't exist: {chat_id}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to leave chat {chat_id}: {e}")
        return False

# Enhanced keyboard functions with error handling
async def safe_edit_message(message, text: str, reply_markup=None, parse_mode="Markdown"):
    """Safely edit message with error handling"""
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.debug("Message content unchanged, skipping edit")
        else:
            logger.error(f"❌ Telegram error editing message: {e}")
            raise
    except Exception as e:
        logger.error(f"❌ Error editing message: {e}")
        raise

async def create_main_menu(user_id: int) -> InlineKeyboardMarkup:
    """Create main menu keyboard"""
    if not is_owner(user_id):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Access Denied", callback_data="access_denied")]
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Account Management", callback_data="account_management"),
            InlineKeyboardButton(text="👥 Member Management", callback_data="member_management")
        ],
        [
            InlineKeyboardButton(text="🎤 Voice Chat", callback_data="voice_chat"),
            InlineKeyboardButton(text="📊 Status", callback_data="vc_status")
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings", callback_data="settings"),
            InlineKeyboardButton(text="❓ Help", callback_data="help")
        ]
    ])

async def create_account_menu() -> InlineKeyboardMarkup:
    """Create account management menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Add Account", callback_data="add_account"),
            InlineKeyboardButton(text="➖ Remove Account", callback_data="remove_account")
        ],
        [
            InlineKeyboardButton(text="📋 List Accounts", callback_data="list_accounts"),
            InlineKeyboardButton(text="🔄 Refresh Sessions", callback_data="refresh_sessions")
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
    ])

async def create_member_menu() -> InlineKeyboardMarkup:
    """Create member management menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Mega Join", callback_data="mega_join"),
            InlineKeyboardButton(text="🚪 Mega Leave", callback_data="mega_leave")
        ],
        [
            InlineKeyboardButton(text="👤 Individual Join", callback_data="individual_join"),
            InlineKeyboardButton(text="👤 Individual Leave", callback_data="individual_leave")
        ],
        [
            InlineKeyboardButton(text="🔢 Multi Join", callback_data="multi_join"),
            InlineKeyboardButton(text="🔢 Multi Leave", callback_data="multi_leave")
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
    ])

async def create_voice_menu() -> InlineKeyboardMarkup:
    """Create voice chat menu with v2.2.5 features"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎤 Join Voice Chat", callback_data="join_voice"),
            InlineKeyboardButton(text="🔇 Leave Voice Chat", callback_data="leave_voice")
        ],
        [
            InlineKeyboardButton(text="🎵 Play Audio", callback_data="play_audio"),
            InlineKeyboardButton(text="🎬 Play Video", callback_data="play_video")
        ],
        [
            InlineKeyboardButton(text="▶️ Resume", callback_data="resume_media"),
            InlineKeyboardButton(text="⏸️ Pause", callback_data="pause_media")
        ],
        [
            InlineKeyboardButton(text="⏹️ Stop", callback_data="stop_media"),
            InlineKeyboardButton(text="⏭️ Skip", callback_data="skip_media")
        ],
        [
            InlineKeyboardButton(text="🎚️ Volume Control", callback_data="volume_control"),
            InlineKeyboardButton(text="🎛️ Audio Quality", callback_data="audio_quality")
        ],
        [
            InlineKeyboardButton(text="📺 Video Quality", callback_data="video_quality"),
            InlineKeyboardButton(text="📋 Playlist Queue", callback_data="queue_status")
        ],
        [
            InlineKeyboardButton(text="📊 Voice Status", callback_data="voice_status"),
            InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")
        ]
    ])

async def create_quality_menu(quality_type: str, current_chat_id: int = 0) -> InlineKeyboardMarkup:
    """Create quality selection menu for v2.2.5"""
    current_settings = get_voice_settings(current_chat_id)
    current_quality = getattr(current_settings, f"{quality_type}_quality", "medium")
    
    qualities = {
        "low": "🔉 Low Quality",
        "medium": "🔊 Medium Quality", 
        "high": "🔊 High Quality"
    }
    
    keyboard = []
    for quality_id, quality_name in qualities.items():
        if quality_id == current_quality:
            quality_name += " ✓"
        keyboard.append([InlineKeyboardButton(
            text=quality_name, 
            callback_data=f"{quality_type}_quality_{quality_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def create_volume_menu(current_chat_id: int = 0) -> InlineKeyboardMarkup:
    """Create volume control menu"""
    current_volume = get_voice_settings(current_chat_id).volume
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔈 25%", callback_data="vol_25"),
            InlineKeyboardButton(text="🔉 50%", callback_data="vol_50"),
            InlineKeyboardButton(text="🔊 100%", callback_data="vol_100")
        ],
        [
            InlineKeyboardButton(text="📢 150%", callback_data="vol_150"),
            InlineKeyboardButton(text="🚨 200%", callback_data="vol_200"),
            InlineKeyboardButton(text="🎛️ Custom", callback_data="vol_custom")
        ],
        [
            InlineKeyboardButton(text=f"Current: {current_volume}%", callback_data="vol_current")
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")]
    ])

async def create_voice_account_selection_keyboard(chat_id: Union[str, int]) -> InlineKeyboardMarkup:
    """Create keyboard for voice chat account selection"""
    keyboard = []
    
    # Add individual accounts
    for phone, (client, _) in user_clients.items():
        try:
            if await client.is_user_authorized():
                me = await client.get_me()
                name = f"{me.first_name} {me.last_name or ''}".strip()
                btn_text = f"🎤 {name[:15]} (+{phone[-4:]})"
            else:
                btn_text = f"❌ +{phone[:2]}••••{phone[-2:]} (Unauthorized)"
        except:
            btn_text = f"⚠️ +{phone[:2]}••••{phone[-2:]} (Error)"
        
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"voice_join_{phone}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Enhanced Command handlers with proper error handling
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    """Start command handler"""
    try:
        if not is_owner(message.from_user.id):
            await message.reply("❌ Access denied. This bot is private.")
            return
        
        keyboard = await create_main_menu(message.from_user.id)
        status = voice_manager.get_status()
        
        feature_text = ""
        if QUALITY_CLASSES_AVAILABLE:
            feature_text += "• Enhanced audio/video quality control\n"
        if AUDIO_VIDEO_PIPED_AVAILABLE:
            feature_text += "• Proper video+audio streaming (AudioVideoPiped)\n"
        if UPDATE_CLASSES_AVAILABLE:
            feature_text += "• Automatic playlist queue management\n"
        feature_text += "• Advanced stream handling\n• Better error recovery"
        
        await message.reply(
            f"🧪 **Test Voice Chat Bot with PyTgCalls**\n\n"
            f"👋 Welcome, {message.from_user.first_name}!\n\n"
            f"📱 Active Accounts: `{len(user_clients)}`\n"
            f"🎵 Active Voice Calls: `{status['active_calls']}`\n"
            f"🔧 PyTgCalls Clients: `{len(pytgcalls_clients)}`\n"
            f"📋 Total Queued: `{status['total_queued']}`\n\n"
            f"🆕 **Available Features:**\n"
            f"{feature_text}\n\n"
            f"🧪 **Test Mode Active!**\n"
            f"Select an option:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Error in start command:")
        logger.error(traceback.format_exc())
        await message.reply("❌ An error occurred. Please try again.")

# Test command for debugging
@dp.message(F.text == "/test")
async def cmd_test(message: types.Message):
    """Test command for debugging"""
    try:
        if not is_owner(message.from_user.id):
            await message.reply("❌ Access denied.")
            return
        
        logger.info(f"🧪 Test command executed by user {message.from_user.id}")
        
        test_info = f"🧪 **System Test Results**\n\n"
        test_info += f"📱 User Clients: `{len(user_clients)}`\n"
        test_info += f"🔧 PyTgCalls Clients: `{len(pytgcalls_clients)}`\n"
        test_info += f"👑 Owner IDs: `{len(OWNER_IDS)}`\n"
        test_info += f"🎤 Active Calls: `{len(voice_manager.active_calls)}`\n\n"
        
        test_info += f"**Available Accounts:**\n"
        for phone, (client, _) in user_clients.items():
            try:
                if await client.is_user_authorized():
                    me = await client.get_me()
                    test_info += f"✅ +{phone[-4:]}: {me.first_name}\n"
                else:
                    test_info += f"❌ +{phone[-4:]}: Not authorized\n"
            except Exception as e:
                test_info += f"⚠️ +{phone[-4:]}: Error - {str(e)[:30]}\n"
        
        test_info += f"\n**Feature Status:**\n"
        test_info += f"{'✅' if QUALITY_CLASSES_AVAILABLE else '❌'} Quality Classes\n"
        test_info += f"{'✅' if AUDIO_VIDEO_PIPED_AVAILABLE else '❌'} AudioVideoPiped\n"
        test_info += f"{'✅' if UPDATE_CLASSES_AVAILABLE else '❌'} Update Classes\n"
        
        # Test keyboard creation
        try:
            keyboard = await create_voice_menu()
            test_info += f"✅ Voice Menu Keyboard: OK\n"
        except Exception as e:
            test_info += f"❌ Voice Menu Keyboard: {str(e)[:30]}\n"
        
        # Test voice chat manager
        try:
            status = voice_manager.get_status()
            test_info += f"✅ Voice Manager: OK\n"
            test_info += f"📊 Active calls: {status['active_calls']}\n"
            test_info += f"📋 Total queued: {status['total_queued']}\n"
        except Exception as e:
            test_info += f"❌ Voice Manager: {str(e)[:30]}\n"
        
        await message.reply(test_info)
        logger.info(f"✅ Test command completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error in test command:")
        logger.error(traceback.format_exc())
        await message.reply("❌ Test failed - check logs")

# Account Management Handlers
@dp.callback_query(F.data == "account_management")
async def callback_account_management(callback: CallbackQuery):
    """Handle account management menu"""
    try:
        keyboard = await create_account_menu()
        
        await safe_edit_message(
            callback.message,
            f"👥 **Account Management**\n\n"
            f"📱 Active Accounts: `{len(user_clients)}`\n"
            f"🔐 Max Accounts: `{MAX_ACCOUNTS}`\n"
            f"🔧 PyTgCalls Instances: `{len(pytgcalls_clients)}`\n\n"
            f"Select an option:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"❌ Error in account management:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "add_account")
async def callback_add_account(callback: CallbackQuery, state: FSMContext):
    """Start account addition process"""
    try:
        if len(user_clients) >= MAX_ACCOUNTS:
            await callback.answer(f"❌ Maximum {MAX_ACCOUNTS} accounts allowed", show_alert=True)
            return
        
        await state.set_state(AccountStates.phone)
        await safe_edit_message(
            callback.message,
            "📱 **Add New Account**\n\n"
            "Enter the phone number (with country code):\n\n"
            "Example: `+1234567890`\n\n"
            "⚠️ **Important:**\n"
            "• Use your actual phone number\n"
            "• Include country code\n"
            "• Make sure SMS/calls are enabled\n"
            "• Account will be initialized with PyTgCalls"
        )
    except Exception as e:
        logger.error(f"❌ Error starting add account:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.message(AccountStates.phone)
async def process_phone_number(message: types.Message, state: FSMContext):
    """Process phone number for account addition"""
    try:
        phone_input = message.text.strip()
        
        try:
            phone = normalize_phone(phone_input)
        except ValueError as e:
            await message.reply(f"❌ Invalid phone number: {e}")
            return
        
        if phone in user_clients:
            await message.reply("❌ This phone number is already added.")
            return
        
        # Store phone and proceed to OTP
        await state.update_data(phone=phone)
        
        # Initialize Telegram client
        try:
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            
            # Send OTP
            result = await client.send_code_request(f"+{phone}")
            phone_code_hash = result.phone_code_hash
            
            await state.update_data(
                client=client,
                phone_code_hash=phone_code_hash
            )
            
            await state.set_state(AccountStates.otp)
            await message.reply(
                f"📱 **OTP Sent**\n\n"
                f"📞 Phone: `+{phone}`\n\n"
                f"Please enter the verification code you received:"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to send OTP:")
            logger.error(traceback.format_exc())
            await message.reply(f"❌ Failed to send OTP: {e}")
            await state.clear()
            
    except Exception as e:
        logger.error(f"❌ Error processing phone number:")
        logger.error(traceback.format_exc())
        await message.reply("❌ An error occurred while processing the phone number.")
        await state.clear()

@dp.message(AccountStates.otp)
async def process_otp(message: types.Message, state: FSMContext):
    """Process OTP for account verification"""
    try:
        data = await state.get_data()
        client = data.get('client')
        phone = data.get('phone')
        phone_code_hash = data.get('phone_code_hash')
        otp = message.text.strip()
        
        if not all([client, phone, phone_code_hash]):
            await message.reply("❌ Session expired. Please start again.")
            await state.clear()
            return
        
        try:
            # Sign in with OTP
            result = await client.sign_in(
                phone=f"+{phone}",
                code=otp,
                phone_code_hash=phone_code_hash
            )
            
            # Get session string
            session_string = client.session.save()
            
            # Store user client
            user_clients[phone] = (client, session_string)
            
            # Save to file
            await save_users()
            
            await message.reply(
                f"✅ **Account Added Successfully**\n\n"
                f"📞 Phone: `+{phone}`\n"
                f"👤 Name: `{result.first_name} {result.last_name or ''}`\n"
                f"🆔 ID: `{result.id}`\n\n"
                f"🔧 PyTgCalls will be initialized when needed.",
                reply_markup=await create_account_menu()
            )
            
            await state.clear()
            
        except SessionPasswordNeededError:
            await state.set_state(AccountStates.password)
            await message.reply(
                "🔒 **Two-Factor Authentication**\n\n"
                "Please enter your 2FA password:"
            )
            
        except PhoneCodeInvalidError:
            await message.reply("❌ Invalid verification code. Please try again.")
            
        except Exception as e:
            logger.error(f"❌ Failed to sign in:")
            logger.error(traceback.format_exc())
            await message.reply(f"❌ Failed to sign in: {e}")
            await client.disconnect()
            await state.clear()
            
    except Exception as e:
        logger.error(f"❌ Error processing OTP:")
        logger.error(traceback.format_exc())
        await message.reply("❌ An error occurred while processing the OTP.")
        await state.clear()

@dp.message(AccountStates.password)
async def process_password(message: types.Message, state: FSMContext):
    """Process 2FA password"""
    try:
        data = await state.get_data()
        client = data.get('client')
        phone = data.get('phone')
        password = message.text.strip()
        
        if not all([client, phone]):
            await message.reply("❌ Session expired. Please start again.")
            await state.clear()
            return
        
        try:
            # Delete the password message for security
            await message.delete()
            
            # Sign in with password
            result = await client.sign_in(password=password)
            
            # Get session string
            session_string = client.session.save()
            
            # Store user client
            user_clients[phone] = (client, session_string)
            
            # Save to file
            await save_users()
            
            await bot.send_message(
                message.chat.id,
                f"✅ **Account Added Successfully**\n\n"
                f"📞 Phone: `+{phone}`\n"
                f"👤 Name: `{result.first_name} {result.last_name or ''}`\n"
                f"🆔 ID: `{result.id}`\n\n"
                f"🔧 PyTgCalls will be initialized when needed.",
                reply_markup=await create_account_menu(),
                parse_mode="Markdown"
            )
            
            await state.clear()
            
        except PasswordHashInvalidError:
            await bot.send_message(
                message.chat.id,
                "❌ Invalid 2FA password. Please try again."
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to sign in with password:")
            logger.error(traceback.format_exc())
            await bot.send_message(
                message.chat.id,
                f"❌ Failed to sign in: {e}"
            )
            await client.disconnect()
            await state.clear()
            
    except Exception as e:
        logger.error(f"❌ Error processing password:")
        logger.error(traceback.format_exc())
        await bot.send_message(
            message.chat.id,
            "❌ An error occurred while processing the password."
        )
        await state.clear()

# Voice Chat Handlers with v2.2.5 features
@dp.callback_query(F.data == "voice_chat")
async def callback_voice_chat(callback: CallbackQuery):
    """Handle voice chat menu"""
    try:
        logger.info(f"🎤 Voice chat menu requested by user {callback.from_user.id}")
        
        keyboard = await create_voice_menu()
        status = voice_manager.get_status()
        
        await safe_edit_message(
            callback.message,
            f"🎤 **Voice Chat Control (Test Mode)**\n\n"
            f"🎵 Active Voice Calls: `{status['active_calls']}`\n"
            f"🔧 PyTgCalls Clients: `{len(pytgcalls_clients)}`\n"
            f"📱 Available Accounts: `{len(user_clients)}`\n"
            f"📋 Total Queued Items: `{status['total_queued']}`\n\n"
            f"🆕 **Enhanced Features:**\n"
            f"• Quality control available\n"
            f"• {'Proper video+audio streaming' if AUDIO_VIDEO_PIPED_AVAILABLE else 'Basic video streaming'}\n"
            f"• {'Auto-playlist management' if UPDATE_CLASSES_AVAILABLE else 'Manual playlist control'}\n"
            f"• Advanced stream handling\n\n"
            f"🧪 **Test Mode Active!**\n"
            f"Select an option:",
            reply_markup=keyboard
        )
        
        logger.info(f"✅ Voice chat menu displayed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error in voice chat menu:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "join_voice")
async def callback_join_voice(callback: CallbackQuery, state: FSMContext):
    """Handle voice chat join"""
    try:
        logger.info(f"🎤 Join voice chat button clicked by user {callback.from_user.id}")
        
        if not user_clients:
            await callback.answer("❌ No accounts available. Add accounts first.", show_alert=True)
            return
        
        # Clear any existing state
        await state.clear()
        
        # Set the new state
        await state.set_state(VoiceChatStates.target_chat)
        
        await safe_edit_message(
            callback.message,
            "🎤 **Join Voice Chat (Test Mode)**\n\n"
            "Please enter the chat ID, username, or invite link:\n\n"
            "**Supported formats:**\n"
            "• Username: `@username`\n"
            "• Chat ID: `-1001234567890`\n"
            "• Invite link: `https://t.me/joinchat/xyz`\n"
            "• Invite hash: `DMMisTI75YE3YzlI` (just the hash)\n\n"
            "**Example:**\n"
            "`DMMisTI75YE3YzlI`\n\n"
            "🆕 **Enhanced Features:**\n"
            "• Auto-reconnection on disconnect\n"
            "• Enhanced error handling\n"
            "• Better stream quality detection\n\n"
            "🧪 **Test Mode:** Full debugging enabled\n"
            "💡 **Tip:** Copy the same invite hash you used before!"
        )
        
        logger.info(f"✅ Join voice chat prompt sent, state set to target_chat")
        
    except Exception as e:
        logger.error(f"❌ Error in join voice:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.message(VoiceChatStates.target_chat)
async def process_voice_chat_target(message: types.Message, state: FSMContext):
    """Process target chat for voice chat operations"""
    try:
        logger.info(f"📝 Processing voice chat target input: {message.text}")
        
        chat_input = message.text.strip()
        chat_id = await extract_chat_id(chat_input)
        
        if not chat_id:
            await message.reply("❌ Invalid chat format. Please try again with a valid format:\n\n"
                              "Examples:\n"
                              "• `@username`\n"
                              "• `-1001234567890`\n" 
                              "• `https://t.me/joinchat/xyz`\n"
                              "• `DMMisTI75YE3YzlI` (invite hash)")
            return
        
        logger.info(f"✅ Successfully parsed chat_id: {chat_id}")
        
        await state.update_data(target_chat=chat_id)
        await state.set_state(VoiceChatStates.account_selection)
        
        # Create account selection keyboard
        keyboard = await create_voice_account_selection_keyboard(chat_id)
        
        await message.reply(
            f"🎯 **Target Chat:** `{chat_id}`\n\n"
            f"🆕 **PyTgCalls Ready (Test Mode)**\n"
            f"📱 **Available Accounts:** {len(user_clients)}\n"
            f"🧪 **Test Mode:** Enhanced debugging enabled\n\n"
            f"Select an account to join the voice chat:",
            reply_markup=keyboard
        )
        
        logger.info(f"✅ Account selection keyboard sent")
        
    except Exception as e:
        logger.error(f"❌ Error processing voice chat target:")
        logger.error(traceback.format_exc())
        await message.reply("❌ An error occurred while processing the chat.")
        await state.clear()

@dp.callback_query(F.data.startswith("voice_join_"))
async def callback_voice_join_account(callback: CallbackQuery, state: FSMContext):
    """Handle voice chat join with specific account - FIXED VERSION"""
    try:
        phone = callback.data.replace("voice_join_", "")
        logger.info(f"🎤 Attempting to join voice chat with account: +{phone[-4:]}")
        
        data = await state.get_data()
        chat_id = data.get("target_chat")
        
        if not chat_id:
            await callback.answer("❌ No target chat set. Please start over.", show_alert=True)
            await state.clear()
            return
        
        if phone not in user_clients:
            await callback.answer("❌ Account not found", show_alert=True)
            return
        
        client, session_string = user_clients[phone]
        
        # Check if client is authorized
        try:
            if not await client.is_user_authorized():
                await callback.answer("❌ Account not authorized", show_alert=True)
                return
        except Exception as auth_error:
            logger.error(f"❌ Error checking authorization:")
            logger.error(traceback.format_exc())
            await callback.answer("❌ Account connection error", show_alert=True)
            return
        
        # Initial status message
        await callback.message.edit_text(
            f"⏳ **Joining Voice Chat (Test Mode)**\n\n"
            f"🎯 Chat: `{chat_id}`\n"
            f"📱 Account: `+{phone[-4:]}`\n"
            f"🔧 Step 1/4: Initializing PyTgCalls...\n\n"
            f"🧪 Test Mode: Full debugging enabled\n"
            f"Please wait..."
        )
        
        try:
            # Update progress
            await callback.message.edit_text(
                f"⏳ **Joining Voice Chat (Test Mode)**\n\n"
                f"🎯 Chat: `{chat_id}`\n"
                f"📱 Account: `+{phone[-4:]}`\n"
                f"🔧 Step 2/4: Resolving chat entity...\n\n"
                f"🧪 Test Mode: Enhanced entity resolution\n"
                f"Please wait..."
            )
            
            # Update progress
            await callback.message.edit_text(
                f"⏳ **Joining Voice Chat (Test Mode)**\n\n"
                f"🎯 Chat: `{chat_id}`\n"
                f"📱 Account: `+{phone[-4:]}`\n"
                f"🔧 Step 3/4: Checking voice chat status...\n\n"
                f"🧪 Test Mode: Advanced voice chat detection\n"
                f"Please wait..."
            )
            
            # Update progress
            await callback.message.edit_text(
                f"⏳ **Joining Voice Chat (Test Mode)**\n\n"
                f"🎯 Chat: `{chat_id}`\n"
                f"📱 Account: `+{phone[-4:]}`\n"
                f"🔧 Step 4/4: Connecting to voice chat...\n\n"
                f"🧪 Test Mode: Using exact same method as main.py\n"
                f"This may take up to 60 seconds..."
            )
            
            logger.info(f"🚀 Starting voice chat join process...")
            
            # Join voice chat with timeout - USING EXACT SAME METHOD AS MAIN.PY
            join_task = voice_manager.join_voice_chat(client, chat_id, phone)
            success = await asyncio.wait_for(join_task, timeout=60.0)
            
            logger.info(f"🎯 Voice chat join result: {success}")
            
            if success:
                await callback.message.edit_text(
                    f"✅ **Successfully Joined Voice Chat (Test Mode)**\n\n"
                    f"🎯 Chat: `{chat_id}`\n"
                    f"📱 Account: `+{phone[-4:]}`\n"
                    f"🎤 PyTgCalls connected\n"
                    f"📋 Playlist queue ready\n"
                    f"🎵 Ready to play high-quality media\n\n"
                    f"🧪 **Test Mode Success!** Same method as main.py worked\n"
                    f"Use the voice chat controls to play audio/video.",
                    reply_markup=await create_voice_menu()
                )
            else:
                # Check if this was a broadcast channel error
                try:
                    entity = await client.get_entity(chat_id)
                    if hasattr(entity, 'broadcast') and entity.broadcast:
                        error_text = (
                            f"❌ **Cannot Join Voice Chat (Test Mode)**\n\n"
                            f"🎯 Chat: `{chat_id}`\n"
                            f"📱 Account: `+{phone[-4:]}`\n\n"
                            f"**Issue:** This is a broadcast channel\n\n"
                            f"**Solution:**\n"
                            f"Voice chats only work in:\n"
                            f"• Regular groups\n"
                            f"• Supergroups\n\n"
                            f"They do NOT work in broadcast channels.\n"
                            f"Please use a group or supergroup instead."
                        )
                        help_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 Back to Voice Menu", callback_data="voice_chat")]
                        ])
                    else:
                        error_text = (
                            f"❌ **Failed to Join Voice Chat (Test Mode)**\n\n"
                            f"🎯 Chat: `{chat_id}`\n"
                            f"📱 Account: `+{phone[-4:]}`\n\n"
                            f"**Most Common Issue:**\n"
                            f"No active voice chat found in the group.\n\n"
                            f"**Quick Fix:**\n"
                            f"1. Open Telegram on your phone\n"
                            f"2. Go to the group\n"
                            f"3. Tap group name → Start Voice Chat\n"
                            f"4. Leave it running and try again\n\n"
                            f"🧪 **Test Mode:** Using same logic as working main.py"
                        )
                        help_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="📋 How to Start Voice Chat", callback_data="how_to_start_vc")],
                            [InlineKeyboardButton(text="🔄 Try Again", callback_data="join_voice")],
                            [InlineKeyboardButton(text="🔙 Back to Voice Menu", callback_data="voice_chat")]
                        ])
                except:
                    error_text = (
                        f"❌ **Failed to Join Voice Chat (Test Mode)**\n\n"
                        f"🎯 Chat: `{chat_id}`\n"
                        f"📱 Account: `+{phone[-4:]}`\n\n"
                        f"**Most Common Issue:**\n"
                        f"No active voice chat found in the group.\n\n"
                        f"**Quick Fix:**\n"
                        f"1. Open Telegram on your phone\n"
                        f"2. Go to the group\n"
                        f"3. Tap group name → Start Voice Chat\n"
                        f"4. Leave it running and try again\n\n"
                        f"🧪 **Test Mode:** Check logs for detailed error info"
                    )
                    help_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📋 How to Start Voice Chat", callback_data="how_to_start_vc")],
                        [InlineKeyboardButton(text="🔄 Try Again", callback_data="join_voice")],
                        [InlineKeyboardButton(text="🔙 Back to Voice Menu", callback_data="voice_chat")]
                    ])
                
                await callback.message.edit_text(error_text, reply_markup=help_keyboard)
        
        except asyncio.TimeoutError:
            logger.error(f"⏰ Voice chat join timeout after 60 seconds")
            await callback.message.edit_text(
                f"⏰ **Voice Chat Join Timeout (Test Mode)**\n\n"
                f"🎯 Chat: `{chat_id}`\n"
                f"📱 Account: `+{phone[-4:]}`\n\n"
                f"The operation took longer than 60 seconds.\n\n"
                f"**Possible causes:**\n"
                f"• PyTgCalls is hanging\n"
                f"• Network connectivity issues\n"
                f"• Telegram server problems\n"
                f"• No active voice chat in group\n\n"
                f"🧪 **Test Mode:** Check vc_bot_test.log for details\n"
                f"💡 **Try:** Start voice chat manually first",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 How to Start Voice Chat", callback_data="how_to_start_vc")],
                    [InlineKeyboardButton(text="🔄 Try Again", callback_data="join_voice")],
                    [InlineKeyboardButton(text="🔙 Back to Voice Menu", callback_data="voice_chat")]
                ])
            )
        
        except Exception as e:
            logger.error(f"❌ Unexpected error in voice join:")
            logger.error(traceback.format_exc())
            await callback.message.edit_text(
                f"❌ **Unexpected Error (Test Mode)**\n\n"
                f"🎯 Chat: `{chat_id}`\n"
                f"📱 Account: `+{phone[-4:]}`\n\n"
                f"Error: `{str(e)[:100]}...`\n\n"
                f"🧪 **Test Mode:** Full error details in vc_bot_test.log\n"
                f"Check the logs for more details.",
                reply_markup=await create_voice_menu()
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Error in voice join callback:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)
        await state.clear()

# Voice Chat Control Handlers (same as main.py)
@dp.callback_query(F.data == "leave_voice")
async def callback_leave_voice(callback: CallbackQuery):
    """Handle leave voice chat"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat", show_alert=True)
            return
        
        # Get the first active call (for simplicity)
        chat_id = list(status['calls'].keys())[0]
        success = await voice_manager.leave_voice_chat(chat_id)
        
        if success:
            await callback.answer("✅ Left voice chat successfully", show_alert=True)
            # Update the menu
            keyboard = await create_voice_menu()
            await safe_edit_message(
                callback.message,
                f"🔇 **Left Voice Chat Successfully (Test Mode)**\n\n"
                f"🎯 Chat: `{chat_id}`\n\n"
                f"🧪 Test Mode: Voice chat left using same method as main.py\n"
                f"You can join another voice chat anytime.",
                reply_markup=keyboard
            )
        else:
            await callback.answer("❌ Failed to leave voice chat", show_alert=True)
            
    except Exception as e:
        logger.error(f"❌ Error in leave voice:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "play_audio")
async def callback_play_audio(callback: CallbackQuery, state: FSMContext):
    """Handle play audio"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat. Join a voice chat first.", show_alert=True)
            return
        
        await state.set_state(MediaStates.media_file)
        await safe_edit_message(
            callback.message,
            "🎵 **Play Audio File (Test Mode)**\n\n"
            "Please send an audio file or enter a file path:\n\n"
            "**Supported formats:**\n"
            "• MP3, WAV, FLAC, OGG\n"
            "• M4A, AAC, WMA\n"
            "• Any audio format supported by FFmpeg\n\n"
            "**You can:**\n"
            "• Upload an audio file directly\n"
            "• Send a file path (e.g., `/path/to/music.mp3`)\n"
            "• Send a URL to an audio file\n\n"
            "🧪 **Test Mode:** Same media handling as main.py"
        )
    except Exception as e:
        logger.error(f"❌ Error in play audio:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "play_video")
async def callback_play_video(callback: CallbackQuery, state: FSMContext):
    """Handle play video"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat. Join a voice chat first.", show_alert=True)
            return
        
        await state.set_state(MediaStates.media_file)
        await state.update_data(is_video=True)
        await safe_edit_message(
            callback.message,
            "🎬 **Play Video File (Test Mode)**\n\n"
            "Please send a video file or enter a file path:\n\n"
            "**Supported formats:**\n"
            "• MP4, AVI, MKV, MOV\n"
            "• FLV, WEBM, 3GP\n"
            "• Any video format supported by FFmpeg\n\n"
            "**You can:**\n"
            "• Upload a video file directly\n"
            "• Send a file path (e.g., `/path/to/video.mp4`)\n"
            "• Send a URL to a video file\n\n"
            "🧪 **Test Mode:** Same video handling as main.py\n"
            "**Note:** Video will be shared with all voice chat participants."
        )
    except Exception as e:
        logger.error(f"❌ Error in play video:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.message(MediaStates.media_file)
async def process_media_file(message: types.Message, state: FSMContext):
    """Process media file for playback"""
    try:
        data = await state.get_data()
        is_video = data.get('is_video', False)
        
        # Get active call
        status = voice_manager.get_status()
        if not status['active_calls']:
            await message.reply("❌ Not in any voice chat. Join a voice chat first.")
            await state.clear()
            return
        
        chat_id = list(status['calls'].keys())[0]
        
        # Get the actual entity_id (integer) from the call info instead of using the string chat_id
        call_info = status['calls'][chat_id]
        entity_id = call_info.get('entity_id', 0)  # Use entity_id for voice settings
        
        file_path = None
        
        # Handle file upload
        if message.document:
            file_info = await bot.get_file(message.document.file_id)
            file_path = f"media/{message.document.file_name}"
            
            # Create media directory if it doesn't exist
            Path("media").mkdir(exist_ok=True)
            
            await bot.download_file(file_info.file_path, file_path)
            await message.reply(f"✅ Downloaded: {message.document.file_name}")
            
        elif message.audio:
            file_info = await bot.get_file(message.audio.file_id)
            file_name = message.audio.file_name or f"audio_{message.audio.file_id}.mp3"
            file_path = f"media/{file_name}"
            
            Path("media").mkdir(exist_ok=True)
            await bot.download_file(file_info.file_path, file_path)
            await message.reply(f"✅ Downloaded: {file_name}")
            
        elif message.video:
            file_info = await bot.get_file(message.video.file_id)
            file_name = message.video.file_name or f"video_{message.video.file_id}.mp4"
            file_path = f"media/{file_name}"
            
            Path("media").mkdir(exist_ok=True)
            await bot.download_file(file_info.file_path, file_path)
            await message.reply(f"✅ Downloaded: {file_name}")
            
        elif message.text:
            file_path = message.text.strip()
            
        if not file_path:
            await message.reply("❌ Please send a valid file or file path.")
            return
        
        # Check if file exists
        if not Path(file_path).exists():
            await message.reply(f"❌ File not found: {file_path}")
            return
        
        # Get voice settings using entity_id (integer) instead of chat_id (string)
        settings = get_voice_settings(entity_id)
        
        # Play the media
        success = await voice_manager.play_media(chat_id, file_path, settings, is_video)
        
        if success:
            media_type = "video" if is_video else "audio"
            await message.reply(
                f"✅ **{'🎬' if is_video else '🎵'} Playing {media_type.title()} (Test Mode)**\n\n"
                f"📁 File: `{Path(file_path).name}`\n"
                f"🎯 Chat: `{chat_id}`\n"
                f"🔊 Volume: `{settings.volume}%`\n"
                f"🎛️ Quality: `{settings.video_quality if is_video else settings.audio_quality}`\n"
                f"🆔 Entity ID: `{entity_id}`\n\n"
                f"🧪 **Test Mode:** Same media playback as main.py",
                reply_markup=await create_voice_menu()
            )
        else:
            await message.reply(f"❌ Failed to play {file_path}")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Error processing media file:")
        logger.error(traceback.format_exc())
        await message.reply("❌ An error occurred while processing the media file.")
        await state.clear()

@dp.callback_query(F.data == "resume_media")
async def callback_resume_media(callback: CallbackQuery):
    """Handle resume media"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat", show_alert=True)
            return
        
        chat_id = list(status['calls'].keys())[0]
        success = await voice_manager.resume_media(chat_id)
        
        if success:
            await callback.answer("▶️ Resumed playback", show_alert=True)
        else:
            await callback.answer("❌ Failed to resume media", show_alert=True)
            
    except Exception as e:
        logger.error(f"❌ Error in resume media:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "pause_media")
async def callback_pause_media(callback: CallbackQuery):
    """Handle pause media"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat", show_alert=True)
            return
        
        chat_id = list(status['calls'].keys())[0]
        success = await voice_manager.pause_media(chat_id)
        
        if success:
            await callback.answer("⏸️ Paused playback", show_alert=True)
        else:
            await callback.answer("❌ Failed to pause media", show_alert=True)
            
    except Exception as e:
        logger.error(f"❌ Error in pause media:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "stop_media")
async def callback_stop_media(callback: CallbackQuery):
    """Handle stop media"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat", show_alert=True)
            return
        
        chat_id = list(status['calls'].keys())[0]
        success = await voice_manager.stop_media(chat_id)
        
        if success:
            await callback.answer("⏹️ Stopped playback", show_alert=True)
        else:
            await callback.answer("❌ Failed to stop media", show_alert=True)
            
    except Exception as e:
        logger.error(f"❌ Error in stop media:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "skip_media")
async def callback_skip_media(callback: CallbackQuery):
    """Handle skip media"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat", show_alert=True)
            return
        
        chat_id = list(status['calls'].keys())[0]
        success = await voice_manager.skip_current(chat_id)
        
        if success:
            await callback.answer("⏭️ Skipped to next track", show_alert=True)
        else:
            await callback.answer("❌ Failed to skip track", show_alert=True)
            
    except Exception as e:
        logger.error(f"❌ Error in skip media:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "volume_control")
async def callback_volume_control(callback: CallbackQuery):
    """Handle volume control"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat", show_alert=True)
            return
        
        chat_id = list(status['calls'].keys())[0]
        keyboard = await create_volume_menu(int(chat_id))
        
        await safe_edit_message(
            callback.message,
            f"🎚️ **Volume Control (Test Mode)**\n\n"
            f"🎯 Chat: `{chat_id}`\n"
            f"🔊 Current Volume: `{get_voice_settings(int(chat_id)).volume}%`\n\n"
            f"🧪 **Test Mode:** Same volume control as main.py\n"
            f"Select a volume level:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"❌ Error in volume control:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data.startswith("vol_"))
async def callback_volume_set(callback: CallbackQuery):
    """Handle volume setting"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat", show_alert=True)
            return
        
        chat_id = list(status['calls'].keys())[0]
        volume_action = callback.data.replace("vol_", "")
        
        if volume_action == "custom":
            await callback.answer("Custom volume - please type a number between 1-200", show_alert=True)
            return
        elif volume_action == "current":
            current_vol = get_voice_settings(int(chat_id)).volume
            await callback.answer(f"Current volume: {current_vol}%", show_alert=True)
            return
        
        try:
            volume = int(volume_action)
            success = await voice_manager.set_volume(chat_id, volume)
            
            if success:
                # Update settings
                settings = get_voice_settings(int(chat_id))
                settings.volume = volume
                save_voice_settings()
                
                await callback.answer(f"🔊 Volume set to {volume}%", show_alert=True)
            else:
                await callback.answer("❌ Failed to set volume", show_alert=True)
                
        except ValueError:
            await callback.answer("❌ Invalid volume value", show_alert=True)
            
    except Exception as e:
        logger.error(f"❌ Error setting volume:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "audio_quality")
async def callback_audio_quality(callback: CallbackQuery):
    """Handle audio quality selection"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat", show_alert=True)
            return
        
        chat_id = list(status['calls'].keys())[0]
        keyboard = await create_quality_menu("audio", int(chat_id))
        
        current_quality = get_voice_settings(int(chat_id)).audio_quality
        
        await safe_edit_message(
            callback.message,
            f"🎛️ **Audio Quality Settings (Test Mode)**\n\n"
            f"🎯 Chat: `{chat_id}`\n"
            f"🔊 Current Quality: `{current_quality.title()}`\n\n"
            f"**Quality Levels:**\n"
            f"🔉 **Low:** 64 kbps - Good for voice\n"
            f"🔊 **Medium:** 128 kbps - Balanced quality\n"
            f"🔊 **High:** 320 kbps - Best quality\n\n"
            f"🧪 **Test Mode:** Same quality system as main.py\n"
            f"Select audio quality:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"❌ Error in audio quality:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "video_quality")
async def callback_video_quality(callback: CallbackQuery):
    """Handle video quality selection"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat", show_alert=True)
            return
        
        chat_id = list(status['calls'].keys())[0]
        keyboard = await create_quality_menu("video", int(chat_id))
        
        current_quality = get_voice_settings(int(chat_id)).video_quality
        
        await safe_edit_message(
            callback.message,
            f"📺 **Video Quality Settings (Test Mode)**\n\n"
            f"🎯 Chat: `{chat_id}`\n"
            f"📹 Current Quality: `{current_quality.title()}`\n\n"
            f"**Quality Levels:**\n"
            f"📱 **Low:** 360p @ 15fps - Mobile friendly\n"
            f"💻 **Medium:** 480p @ 30fps - Balanced\n"
            f"🖥️ **High:** 720p @ 30fps - Best quality\n\n"
            f"🧪 **Test Mode:** Same video system as main.py\n"
            f"Select video quality:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"❌ Error in video quality:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data.startswith(("audio_quality_", "video_quality_")))
async def callback_quality_set(callback: CallbackQuery):
    """Handle quality setting"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat", show_alert=True)
            return
        
        chat_id = list(status['calls'].keys())[0]
        
        if callback.data.startswith("audio_quality_"):
            quality_type = "audio"
            quality_level = callback.data.replace("audio_quality_", "")
        else:
            quality_type = "video"
            quality_level = callback.data.replace("video_quality_", "")
        
        # Update settings
        settings = get_voice_settings(int(chat_id))
        if quality_type == "audio":
            settings.audio_quality = quality_level
        else:
            settings.video_quality = quality_level
        
        save_voice_settings()
        
        await callback.answer(f"✅ {quality_type.title()} quality set to {quality_level}", show_alert=True)
        
        # Return to voice menu
        keyboard = await create_voice_menu()
        await safe_edit_message(
            callback.message,
            f"✅ **Quality Updated (Test Mode)**\n\n"
            f"🎯 Chat: `{chat_id}`\n"
            f"🎛️ {quality_type.title()} Quality: `{quality_level.title()}`\n\n"
            f"🧪 **Test Mode:** Quality applied using main.py method\n"
            f"New quality will apply to next media played.",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Error setting quality:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "queue_status")
async def callback_queue_status(callback: CallbackQuery):
    """Handle playlist queue status"""
    try:
        status = voice_manager.get_status()
        if not status['active_calls']:
            await callback.answer("❌ Not in any voice chat", show_alert=True)
            return
        
        chat_id = list(status['calls'].keys())[0]
        queue_info = status.get('queue_info', {})
        queue_count = queue_info.get(chat_id, 0)
        
        queue_text = f"📋 **Playlist Queue Status (Test Mode)**\n\n"
        queue_text += f"🎯 Chat: `{chat_id}`\n"
        queue_text += f"📝 Items in Queue: `{queue_count}`\n\n"
        
        if queue_count > 0:
            queue_text += f"🎵 **Next tracks will play automatically**\n"
            queue_text += f"⏭️ Use Skip button to go to next track\n"
            queue_text += f"⏹️ Use Stop to clear the queue\n\n"
        else:
            queue_text += f"📭 **Queue is empty**\n"
            queue_text += f"🎵 Add more audio/video files to queue\n\n"
        
        # Get current playing info
        call_info = status['calls'].get(chat_id, {})
        if call_info.get('playing'):
            current_file = call_info.get('file', 'Unknown')
            queue_text += f"▶️ **Currently Playing:**\n"
            queue_text += f"📁 `{Path(current_file).name if current_file != 'Unknown' else current_file}`\n\n"
        else:
            queue_text += f"⏸️ **No media currently playing**\n\n"
        
        queue_text += f"🧪 **Test Mode:** Same playlist system as main.py"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="queue_status")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")]
        ])
        
        await safe_edit_message(callback.message, queue_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Error in queue status:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "voice_status")
async def callback_voice_status(callback: CallbackQuery):
    """Handle voice status"""
    try:
        status = voice_manager.get_status()
        
        status_text = f"📊 **Voice Chat Status (Test Mode)**\n\n"
        status_text += f"🎤 **Active Calls:** `{status['active_calls']}`\n"
        status_text += f"📋 **Total Queued:** `{status['total_queued']}`\n"
        status_text += f"🔧 **PyTgCalls Clients:** `{len(pytgcalls_clients)}`\n"
        status_text += f"📱 **Available Accounts:** `{len(user_clients)}`\n\n"
        
        if status['active_calls'] > 0:
            status_text += f"🎯 **Active Voice Chats:**\n"
            for chat_id, call_info in status['calls'].items():
                chat_title = call_info.get('chat_title', 'Unknown Chat')
                user_name = call_info.get('user_name', 'Unknown User')
                playing = "🎵 Playing" if call_info.get('playing') else "⏸️ Idle"
                
                status_text += f"• **{chat_title}**\n"
                status_text += f"  👤 {user_name}\n"
                status_text += f"  📊 {playing}\n"
                
                if call_info.get('file'):
                    file_name = Path(call_info['file']).name
                    status_text += f"  📁 {file_name}\n"
                
                queue_count = status['queue_info'].get(chat_id, 0)
                if queue_count > 0:
                    status_text += f"  📋 Queue: {queue_count} items\n"
                
                status_text += "\n"
        else:
            status_text += f"📭 **No active voice chats**\n"
            status_text += f"Use 'Join Voice Chat' to start.\n\n"
        
        # System status
        status_text += f"🖥️ **System Status (Test Mode):**\n"
        if QUALITY_CLASSES_AVAILABLE:
            status_text += f"✅ Enhanced quality control\n"
        if AUDIO_VIDEO_PIPED_AVAILABLE:
            status_text += f"✅ Proper video+audio streaming\n"
        if UPDATE_CLASSES_AVAILABLE:
            status_text += f"✅ Auto-playlist management\n"
        status_text += f"✅ Advanced stream handling\n"
        status_text += f"🧪 Using exact same VoiceChatManager as main.py\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="voice_status")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")]
        ])
        
        await safe_edit_message(callback.message, status_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Error in voice status:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

# Help callback handler
@dp.callback_query(F.data == "how_to_start_vc")
async def callback_how_to_start_vc(callback: CallbackQuery):
    """Show instructions for starting voice chat"""
    try:
        help_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Try Joining Again", callback_data="join_voice")],
            [InlineKeyboardButton(text="🔙 Back to Voice Menu", callback_data="voice_chat")]
        ])
        
        await safe_edit_message(
            callback.message,
            f"📋 **How to Start a Voice Chat (Test Mode)**\n\n"
            f"**Method 1: Mobile App**\n"
            f"1️⃣ Open Telegram on your phone\n"
            f"2️⃣ Go to the target group\n"
            f"3️⃣ Tap the group name at the top\n"
            f"4️⃣ Tap **'Start Voice Chat'** button\n"
            f"5️⃣ The voice chat is now active!\n\n"
            f"**Method 2: Desktop App**\n"
            f"1️⃣ Open Telegram Desktop\n"
            f"2️⃣ Go to the target group\n"
            f"3️⃣ Click the **phone icon** in the top bar\n"
            f"4️⃣ Click **'Start Voice Chat'**\n\n"
            f"**Important Notes:**\n"
            f"• Keep the voice chat running (don't end it)\n"
            f"• You can mute yourself if needed\n"
            f"• The bot will join the existing voice chat\n"
            f"• Works in groups and supergroups only\n\n"
            f"**If you have admin rights:**\n"
            f"The bot may be able to start voice chats automatically.\n"
            f"Give the bot **'Manage Voice Chats'** permission.\n\n"
            f"🧪 **Test Mode:** Uses same detection logic as main.py\n\n"
            f"After starting the voice chat, try joining with the bot again!",
            reply_markup=help_keyboard
        )
    except Exception as e:
        logger.error(f"❌ Error in help callback:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

# Navigation handlers
@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Return to main menu"""
    try:
        keyboard = await create_main_menu(callback.from_user.id)
        status = voice_manager.get_status()
        
        await safe_edit_message(
            callback.message,
            f"🧪 **Test Voice Chat Bot with PyTgCalls**\n\n"
            f"📱 Active Accounts: `{len(user_clients)}`\n"
            f"🎵 Active Voice Calls: `{status['active_calls']}`\n"
            f"🔧 PyTgCalls Clients: `{len(pytgcalls_clients)}`\n"
            f"📋 Total Queued: `{status['total_queued']}`\n\n"
            f"🧪 **Test Mode Active!**\n"
            f"🆕 **Enhanced Features Active!**\n\n"
            f"Select an option:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"❌ Error in main menu:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

# List accounts callback
@dp.callback_query(F.data == "list_accounts")
async def callback_list_accounts(callback: CallbackQuery):
    """List all accounts"""
    try:
        if not user_clients:
            await callback.answer("❌ No accounts added yet", show_alert=True)
            return
        
        account_text = f"📋 **Account List (Test Mode)**\n\n"
        account_text += f"📱 **Total Accounts:** `{len(user_clients)}`\n\n"
        
        for i, (phone, (client, _)) in enumerate(user_clients.items(), 1):
            try:
                if await client.is_user_authorized():
                    me = await client.get_me()
                    name = f"{me.first_name} {me.last_name or ''}".strip()
                    account_text += f"{i}. ✅ **{name}**\n"
                    account_text += f"   📞 +{phone[-4:]} (Authorized)\n"
                    account_text += f"   🆔 {me.id}\n"
                else:
                    account_text += f"{i}. ❌ **+{phone[:2]}••••{phone[-2:]}**\n"
                    account_text += f"   📞 Not authorized\n"
            except Exception as e:
                account_text += f"{i}. ⚠️ **+{phone[:2]}••••{phone[-2:]}**\n"
                account_text += f"   📞 Error: {str(e)[:30]}\n"
            
            account_text += "\n"
        
        account_text += f"🧪 **Test Mode:** Using same client management as main.py"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="list_accounts")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="account_management")]
        ])
        
        await safe_edit_message(callback.message, account_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Error listing accounts:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

# Status callback
@dp.callback_query(F.data == "vc_status")
async def callback_vc_status(callback: CallbackQuery):
    """Show overall status"""
    try:
        status = voice_manager.get_status()
        
        status_text = f"📊 **Overall Bot Status (Test Mode)**\n\n"
        status_text += f"🤖 **Bot Information:**\n"
        status_text += f"• Running: ✅ Active\n"
        status_text += f"• Mode: 🧪 Test Mode\n"
        status_text += f"• Log File: `vc_bot_test.log`\n\n"
        
        status_text += f"📱 **Accounts:**\n"
        status_text += f"• Total: `{len(user_clients)}`\n"
        status_text += f"• Max Allowed: `{MAX_ACCOUNTS}`\n\n"
        
        status_text += f"🎤 **Voice Chats:**\n"
        status_text += f"• Active Calls: `{status['active_calls']}`\n"
        status_text += f"• PyTgCalls Clients: `{len(pytgcalls_clients)}`\n"
        status_text += f"• Total Queued: `{status['total_queued']}`\n\n"
        
        status_text += f"🔧 **Features:**\n"
        status_text += f"• Quality Classes: {'✅' if QUALITY_CLASSES_AVAILABLE else '❌'}\n"
        status_text += f"• AudioVideoPiped: {'✅' if AUDIO_VIDEO_PIPED_AVAILABLE else '❌'}\n"
        status_text += f"• Update Classes: {'✅' if UPDATE_CLASSES_AVAILABLE else '❌'}\n"
        status_text += f"• Stream Handling: ✅ Advanced\n\n"
        
        status_text += f"🧪 **Test Mode Features:**\n"
        status_text += f"• Enhanced Debugging: ✅\n"
        status_text += f"• Detailed Logging: ✅\n"
        status_text += f"• Same Logic as main.py: ✅\n"
        status_text += f"• Test File Names: ✅"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="vc_status")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
        ])
        
        await safe_edit_message(callback.message, status_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Error in vc status:")
        logger.error(traceback.format_exc())
        await callback.answer("❌ An error occurred", show_alert=True)

# Enhanced startup and shutdown functions
async def on_startup():
    """Enhanced startup function with PyTgCalls"""
    try:
        logger.info("🧪 Starting Test Voice Chat Bot with PyTgCalls...")
        
        # Check PyTgCalls features
        if QUALITY_CLASSES_AVAILABLE:
            logger.info("✅ Quality classes available - Enhanced features enabled")
        else:
            logger.info("⚠️ Using fallback quality settings")
        
        if AUDIO_VIDEO_PIPED_AVAILABLE:
            logger.info("✅ AudioVideoPiped available - Proper video+audio support")
        else:
            logger.info("⚠️ AudioVideoPiped not available - Using fallback video method")
            
        if UPDATE_CLASSES_AVAILABLE:
            logger.info("✅ Update event handlers available")
        else:
            logger.info("⚠️ Basic event handling mode")
        
        # Create necessary directories
        for directory in ["media", "logs"]:
            Path(directory).mkdir(exist_ok=True)
        
        # Create silence file for voice operations
        await create_silence_file()
        
        # Load data (using test file names)
        await load_users()
        load_voice_settings()
        
        # Test bot connection
        bot_info = await bot.get_me()
        logger.info(f"✅ Test Bot connected: @{bot_info.username}")
        
        logger.info(f"✅ Test Bot started successfully!")
        logger.info(f"📱 Loaded {len(user_clients)} accounts")
        logger.info(f"🎵 Loaded voice settings for {len(voice_settings)} chats")
        logger.info(f"👑 Authorized owners: {len(OWNER_IDS)}")
        logger.info(f"🔧 PyTgCalls ready for initialization")
        logger.info(f"🧪 Test Mode: Using exact same VoiceChatManager as main.py")
        
    except Exception as e:
        logger.error(f"❌ Test startup failed:")
        logger.error(traceback.format_exc())
        raise

async def on_shutdown():
    """Enhanced shutdown function with PyTgCalls cleanup"""
    try:
        logger.info("🛑 Shutting down Test Bot...")
        
        # Leave all voice chats and cleanup PyTgCalls
        status = voice_manager.get_status()
        for chat_id in list(status['calls'].keys()):
            try:
                await voice_manager.leave_voice_chat(chat_id)
            except Exception as e:
                logger.error(f"❌ Error leaving voice chat {chat_id}:")
                logger.error(traceback.format_exc())
        
        # Cleanup all PyTgCalls clients
        for phone in list(pytgcalls_clients.keys()):
            try:
                await voice_manager.cleanup_client(phone)
            except Exception as e:
                logger.error(f"❌ Error cleaning up PyTgCalls for {phone}:")
                logger.error(traceback.format_exc())
        
        # Disconnect all Telegram clients
        disconnect_count = 0
        for phone, (client, _) in user_clients.items():
            try:
                if client.is_connected():
                    await client.disconnect()
                    disconnect_count += 1
                logger.info(f"✅ Disconnected {phone}")
            except Exception as e:
                logger.error(f"❌ Failed to disconnect {phone}:")
                logger.error(traceback.format_exc())
        
        # Save data (using test file names)
        await save_users()
        save_voice_settings()
        
        logger.info(f"✅ Test shutdown complete ({disconnect_count} clients disconnected)")
        
    except Exception as e:
        logger.error(f"❌ Test shutdown error:")
        logger.error(traceback.format_exc())

# Main function
async def main():
    """Main function with comprehensive error handling"""
    try:
        await on_startup()
        logger.info("🧪 Test Bot is running with PyTgCalls... Press Ctrl+C to stop")
        await dp.start_polling(bot, skip_updates=True)
        
    except KeyboardInterrupt:
        logger.info("🛑 Test Bot stopped by user (Ctrl+C)")
        
    except Exception as e:
        logger.error(f"❌ Fatal error in test bot:")
        logger.error(traceback.format_exc())
        
    finally:
        await on_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test Bot stopped")
    except Exception as e:
        print(f"❌ Critical error in test bot:")
        print(traceback.format_exc())
        sys.exit(1)
