from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from pydub import AudioSegment
from pydub.effects import normalize, low_pass_filter, high_pass_filter
import math
#!/usr/bin/env python3
"""
Modern Voice Chat Bot with PyTgCalls 2.2.5, Telethon 1.40.0, and Aiogram 3.15.0
Updated for latest stable versions with performance optimizations and enhanced error handling.
Auto-installation of missing dependencies included.
"""

import subprocess
import sys
import os

# Auto-installation logic for dependencies
def install_package(package_name: str, version: str = None):
    """Install a package using pip"""
    try:
        if version:
            package = f"{package_name}=={version}"
        else:
            package = package_name
        print(f"📦 Installing {package}...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", package,
            "--upgrade", "--no-cache-dir"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def check_and_install_dependencies():
    """Check and install all required dependencies"""
    print("🔍 Checking dependencies...")
    
    # Core dependencies with specific versions
    core_dependencies = {
        'telethon': '1.40.0',
        'aiogram': '3.15.0',
        'py-tgcalls': '2.2.5',
        'aiofiles': '24.1.0',
        'python-dotenv': '1.0.1',
    }
    
    # Performance dependencies (recommended)
    performance_dependencies = {
        'orjson': '3.10.12',
        'cryptg': '0.4.0',
        'psutil': '6.1.0',
        'Pillow': '10.4.0',
    }
    
    # Special handling for aiohttp with speedups
    special_dependencies = {
        'aiohttp[speedups]': '3.10.10',
        'ffmpeg-python': '0.2.0',
    }
    
    failed_installs = []
    
    # Install core dependencies
    for package, version in core_dependencies.items():
        try:
            if package == 'py-tgcalls':
                # Special handling for py-tgcalls import check
                import pytgcalls
            elif package == 'python-dotenv':
                import dotenv
            else:
                __import__(package.replace('-', '_'))
            print(f"✅ {package} is already installed")
        except ImportError:
            print(f"⚠️ {package} not found, installing...")
            if not install_package(package, version):
                failed_installs.append(f"{package}=={version}")
    
    # Install performance dependencies (optional, won't fail startup)
    for package, version in performance_dependencies.items():
        try:
            if package == 'orjson':
                import orjson
            elif package == 'cryptg':
                import cryptg
            elif package == 'psutil':
                import psutil
            elif package == 'Pillow':
                import PIL
            print(f"✅ {package} is already installed")
        except ImportError:
            print(f"⚠️ Optional dependency {package} not found, installing...")
            install_package(package, version)  # Don't track failures for optional deps
    
    # Install special dependencies
    for package, version in special_dependencies.items():
        try:
            if 'aiohttp' in package:
                import aiohttp
            elif 'ffmpeg-python' in package:
                import ffmpeg
            print(f"✅ {package.split('[')[0]} is already installed")
        except ImportError:
            print(f"⚠️ {package} not found, installing...")
            if not install_package(package, version):
                if 'aiohttp' in package:
                    failed_installs.append(f"{package}=={version}")
    
    if failed_installs:
        print(f"❌ Failed to install critical dependencies: {', '.join(failed_installs)}")
        print(f"💡 Please install manually: pip install {' '.join(failed_installs)}")
        sys.exit(1)
    
    print("✅ All dependencies are ready!")

# Run dependency check before any imports
check_and_install_dependencies()

# Now import everything after ensuring dependencies are available
import asyncio
import logging
import time
import traceback
import tempfile
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict

# Performance imports - Added for optimization
try:
    import orjson as json
    JSON_PERFORMANCE = True
except ImportError:
    import json
    JSON_PERFORMANCE = False

import aiofiles
from datetime import datetime

# Aiogram 3.15.0 imports - Updated for latest version
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandObject

# Telethon 1.40.0 imports - Updated with latest API
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

# PyTgCalls 2.2.5 imports - NEW API (≥2.0.0) with proper modern classes
from pytgcalls import PyTgCalls
from pytgcalls.types import CallConfig, GroupCallConfig

# Import correct type hint for py-tgcalls 2.2.5
from pytgcalls.types import GroupCallConfig
GROUPCALL_TYPE_AVAILABLE = True
import logging
logging.info("✅ GroupCallConfig is now being used.")

# NOTE: py-tgcalls 2.2.5 removed specific exceptions like NoActiveGroupCall
# We now use generic Exception/RuntimeError handling and Telethon API checks

# PyTgCalls v2.2.6 does NOT support input_stream API
INPUT_STREAM_AVAILABLE = False  # v2.2.6 does not support input_stream

try:
    QUALITY_CLASSES_AVAILABLE = True
    print("✅ Quality classes available")
except ImportError:
    QUALITY_CLASSES_AVAILABLE = False
    print("⚠️ Quality classes not available, using fallback")

# NEW API: Stream events
try:
    # Removed old stream event imports as they are no longer needed
    STREAM_EVENTS_AVAILABLE = True
    print("✅ Stream event handlers available")
except ImportError:
    STREAM_EVENTS_AVAILABLE = False
    print("⚠️ Stream event handlers not available, using basic mode")
    # Fallback dummy classes
    class StreamAudioEnded:
        pass
    class StreamVideoEnded:
        pass

# Legacy fallback - AudioParameters/VideoParameters may still exist for compatibility
try:
    # ---- pytgcalls (MarshalX) ----
    # GroupCallFactory and GroupCallType not available in v2.2.6
    # Types exported by pytgcalls/types/__init__.py (safe to import even if you don’t use all)
    from pytgcalls.types import (
        Update,
        GroupCallParticipant,            # wrappers for events/participants
        JoinedGroupCallParticipant,
        LeftGroupCallParticipant,
        AudioQuality,                    # quality enums (optional use)
        VideoQuality,                    # quality enums (optional use)
    )
    LEGACY_PARAMETERS_AVAILABLE = True
except ImportError:
    LEGACY_PARAMETERS_AVAILABLE = False
    # Create dummy classes
    class AudioParameters:
        def __init__(self, bitrate=128000):
            self.bitrate = bitrate
    class VideoParameters:
        def __init__(self, width=640, height=480, frame_rate=30):
            self.width = width
            self.height = height
            self.frame_rate = frame_rate

# Environment variables with enhanced dotenv support
from dotenv import load_dotenv

# Load environment variables from multiple sources for flexibility
load_dotenv()  # Load from .env
load_dotenv('.env.local')  # Load from .env.local (override)

# Performance optimization imports
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Enhanced logging setup with performance monitoring
def setup_enhanced_logging():
    """Setup comprehensive logging with performance monitoring"""
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Enhanced formatter with more context
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - '
        '%(message)s - [%(process)d:%(thread)d]'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler with rotation
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            'logs/vc_bot.log', 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ Could not setup file logging: {e}")
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # Performance logger if psutil is available
    if PSUTIL_AVAILABLE:
        perf_handler = logging.FileHandler('logs/performance.log', encoding='utf-8')
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(detailed_formatter)
        
        perf_logger = logging.getLogger('performance')
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)
    
    return logger

logger = setup_enhanced_logging()

# Enhanced configuration validation with better error messages
def validate_and_load_config():
    """Enhanced configuration validation with detailed error reporting"""
    config_errors = []
    warnings = []
    
    # Required environment variables
    required_vars = {
        'API_ID': 'Telegram API ID (get from https://my.telegram.org)',
        'API_HASH': 'Telegram API Hash (get from https://my.telegram.org)', 
        'BOT_TOKEN': 'Telegram Bot Token (get from @BotFather)',
        'OWNER_IDS': 'Comma-separated list of owner user IDs'
    }
    
    config = {}
    
    # Validate required variables
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            config_errors.append(f"Missing {var}: {description}")
        else:
            config[var] = value
    
    if config_errors:
        error_msg = "❌ Configuration Error:\n" + "\n".join(f"  • {err}" for err in config_errors)
        error_msg += f"\n\n💡 Create a .env file with the required variables."
        raise ValueError(error_msg)
    
    # Validate API_ID
    try:
        api_id = int(config['API_ID'])
        if api_id <= 0:
            raise ValueError("API_ID must be a positive integer")
        config['API_ID'] = api_id
    except ValueError:
        raise ValueError("API_ID must be a valid positive integer")
    
    # Validate OWNER_IDS
    try:
        owner_ids_str = config['OWNER_IDS']
        owner_ids = [int(x.strip()) for x in owner_ids_str.split(',') if x.strip()]
        if not owner_ids:
            raise ValueError("At least one OWNER_ID must be specified")
        config['OWNER_IDS'] = owner_ids
    except ValueError:
        raise ValueError("OWNER_IDS must be comma-separated positive integers")
    
    # Optional configuration with defaults
    optional_config = {
        'JOIN_DELAY': (2, int, "Delay between joins in seconds"),
        'LEAVE_DELAY': (1, int, "Delay between leaves in seconds"),
        'MAX_VOLUME': (600, int, "Maximum volume level (1-600)"),
        'VOICE_JOIN_DELAY': (3, int, "Delay before joining voice chat"),
        'MAX_ACCOUNTS': (50, int, "Maximum number of accounts"),
        'FFMPEG_PATH': ('ffmpeg', str, "Path to FFmpeg binary"),
        'SESSION_STRING_ENCRYPTION': (True, bool, "Encrypt session strings"),
    }
    
    for key, (default, type_func, description) in optional_config.items():
        try:
            env_value = os.getenv(key)
            if env_value:
                if type_func == bool:
                    config[key] = env_value.lower() in ('true', '1', 'yes', 'on')
                else:
                    config[key] = type_func(env_value)
            else:
                config[key] = default
                warnings.append(f"Using default {key}: {default}")
        except (ValueError, TypeError):
            warnings.append(f"Invalid {key}, using default: {default}")
            config[key] = default
    
    # Validate ranges
    config['JOIN_DELAY'] = max(1, config['JOIN_DELAY'])
    config['LEAVE_DELAY'] = max(1, config['LEAVE_DELAY'])
    config['MAX_VOLUME'] = max(1, min(600, config['MAX_VOLUME']))
    config['VOICE_JOIN_DELAY'] = max(1, config['VOICE_JOIN_DELAY'])
    config['MAX_ACCOUNTS'] = max(1, min(100, config['MAX_ACCOUNTS']))
    
    # Log warnings
    for warning in warnings:
        logger.warning(f"⚠️ {warning}")
    
    # Log loaded configuration (without sensitive data)
    logger.info("✅ Configuration loaded successfully")
    logger.info(f"📱 Max accounts: {config['MAX_ACCOUNTS']}")
    logger.info(f"👑 Authorized owners: {len(config['OWNER_IDS'])}")
    logger.info(f"🎚️ Max volume: {config['MAX_VOLUME']}%")
    
    # Check for performance features
    if JSON_PERFORMANCE:
        logger.info("⚡ orjson available for enhanced JSON performance")
    if AIOHTTP_AVAILABLE:
        logger.info("⚡ aiohttp available with speedups")
    if PSUTIL_AVAILABLE:
        logger.info("⚡ psutil available for performance monitoring")
    
    return config

# Load and validate configuration
try:
    CONFIG = validate_and_load_config()
    API_ID = CONFIG['API_ID']
    API_HASH = CONFIG['API_HASH']
    BOT_TOKEN = CONFIG['BOT_TOKEN']
    OWNER_IDS = CONFIG['OWNER_IDS']
    JOIN_DELAY = CONFIG['JOIN_DELAY']
    LEAVE_DELAY = CONFIG['LEAVE_DELAY']
    MAX_VOLUME = CONFIG['MAX_VOLUME']
    VOICE_JOIN_DELAY = CONFIG['VOICE_JOIN_DELAY']
    MAX_ACCOUNTS = CONFIG['MAX_ACCOUNTS']
    FFMPEG_PATH = CONFIG['FFMPEG_PATH']
except ValueError as e:
    logger.error(str(e))
    sys.exit(1)

# FFmpeg setup for Heroku deployment
def setup_ffmpeg_environment():
    """Setup FFmpeg environment and check availability"""
    global FFMPEG_PATH
    
    # Common FFmpeg installation paths on Heroku
    heroku_paths = [
        "/app/.apt/usr/bin/ffmpeg",
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg"
    ]
    
    # Check if current FFMPEG_PATH works
    try:
        result = subprocess.run([FFMPEG_PATH, '-version'], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info(f"✅ FFmpeg found at: {FFMPEG_PATH}")
            # Also check for ffprobe
            ffprobe_path = FFMPEG_PATH.replace('ffmpeg', 'ffprobe')
            try:
                probe_result = subprocess.run([ffprobe_path, '-version'], 
                                            capture_output=True, text=True, timeout=5)
                if probe_result.returncode == 0:
                    logger.info(f"✅ FFprobe found at: {ffprobe_path}")
                    os.environ['FFPROBE_BINARY'] = ffprobe_path
                else:
                    logger.warning("⚠️ FFprobe not found with FFmpeg")
            except:
                logger.warning("⚠️ Could not verify FFprobe availability")
            return
    except:
        pass
    
    # If default path doesn't work, try Heroku paths
    for path in heroku_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            try:
                result = subprocess.run([path, '-version'], 
                                       capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    FFMPEG_PATH = path
                    logger.info(f"✅ FFmpeg found at Heroku path: {path}")
                    
                    # Update config and environment
                    CONFIG['FFMPEG_PATH'] = path
                    os.environ['FFMPEG_BINARY'] = path
                    
                    # Check for ffprobe in same directory
                    ffprobe_path = path.replace('ffmpeg', 'ffprobe')
                    if os.path.exists(ffprobe_path):
                        logger.info(f"✅ FFprobe found at: {ffprobe_path}")
                        os.environ['FFPROBE_BINARY'] = ffprobe_path
                    return
            except:
                continue
    
    # If no FFmpeg found, log warning
    logger.warning("⚠️ FFmpeg not found in expected locations. Voice features may not work.")
    logger.warning("   Available paths checked:")
    for path in heroku_paths:
        exists = "✅" if os.path.exists(path) else "❌"
        logger.warning(f"   {exists} {path}")

# Setup FFmpeg environment
setup_ffmpeg_environment()

# Enhanced bot initialization with error handling
try:
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    logger.info("✅ Bot and Dispatcher initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize bot: {e}")
    sys.exit(1)

# Global storage with thread-safe operations
user_clients: Dict[str, Tuple[TelegramClient, str]] = {}
pytgcalls_clients: Dict[str, Any] = {}  # Now stores GroupCall instances or equivalent from PyTgCalls
active_operations: Dict[str, Dict[str, Any]] = {}

# Log successful auto-installation
print("🎵 Voice Chat Bot dependencies loaded successfully!")
print(f"📦 Telethon: 1.40.0")
print(f"📦 py-tgcalls: 2.2.5 (GroupCallFactory API)")
print(f"📦 Aiogram: 3.15.0")
print(f"📦 Enhanced features: InputStreams={INPUT_STREAM_AVAILABLE}, Quality={QUALITY_CLASSES_AVAILABLE}, StreamEvents={STREAM_EVENTS_AVAILABLE}")

# Enhanced voice settings dataclass with validation
@dataclass
class VoiceSettings:
    """Enhanced voice settings with validation and performance optimization"""
    volume: int = MAX_VOLUME
    effects: str = "none"
    equalizer: str = "normal"
    is_video: bool = False
    audio_quality: str = "high"  # low, medium, high
    video_quality: str = "high"  # low, medium, high
    audio_bitrate: int = 128000
    video_bitrate: int = 512000
    framerate: int = 30
    width: int = 640
    height: int = 480
    # New fields for enhanced functionality
    noise_reduction: bool = True
    echo_cancellation: bool = True
    auto_gain_control: bool = True
    
    def __post_init__(self):
        """Validate and normalize settings"""
        # Validate volume
        self.volume = max(1, min(MAX_VOLUME, self.volume))
        
        # Validate effects
        valid_effects = ["none", "robot", "echo", "chipmunk", "deep", "underwater"]
        if self.effects not in valid_effects:
            logger.warning(f"Invalid effect '{self.effects}', using 'none'")
            self.effects = "none"
        
        # Validate equalizer
        valid_equalizers = ["normal", "rock", "vocal", "electronic", "classical", "loud"]
        if self.equalizer not in valid_equalizers:
            logger.warning(f"Invalid equalizer '{self.equalizer}', using 'normal'")
            self.equalizer = "normal"
        
        # Validate quality settings
        valid_qualities = ["low", "medium", "high"]
        if self.audio_quality not in valid_qualities:
            logger.warning(f"Invalid audio quality '{self.audio_quality}', using 'medium'")
            self.audio_quality = "medium"
        if self.video_quality not in valid_qualities:
            logger.warning(f"Invalid video quality '{self.video_quality}', using 'medium'")
            self.video_quality = "medium"
        
        # Validate bitrates
        self.audio_bitrate = max(16000, min(320000, self.audio_bitrate))
        self.video_bitrate = max(128, min(8192, self.video_bitrate))
        self.framerate = max(15, min(60, self.framerate))
        
        # Validate resolution
        self.width = max(320, min(1920, self.width))
        self.height = max(240, min(1080, self.height))

    def get_audio_quality(self):
        """Get audio quality for PyTgCalls 2.2.6 (legacy only)"""
        bitrate_map = {
            "low": 64000,
            "medium": 128000,
            "high": 320000
        }
        return AudioParameters(
            bitrate=bitrate_map.get(self.audio_quality, 128000)
        )

    def get_video_quality(self):
        """Get video quality for PyTgCalls 2.2.6 (legacy only)"""
        resolution_map = {
            "low": (480, 360, 24),
            "medium": (854, 480, 30),
            "high": (1280, 720, 30)
        }
        width, height, fps = resolution_map.get(self.video_quality, (854, 480, 30))
        return VideoParameters(
            width=width,
            height=height,
            frame_rate=fps
        )

    # Keep legacy methods for backward compatibility
    def get_audio_parameters(self):
        """Legacy method - redirects to get_audio_quality()"""
        return self.get_audio_quality()

    def get_video_parameters(self):
        """Legacy method - redirects to get_video_quality()"""
        return self.get_video_quality()

# Thread-safe voice settings storage
voice_settings: Dict[int, VoiceSettings] = {}
voice_settings_lock = asyncio.Lock()

# Enhanced Voice Chat Manager with PyTgCalls 2.2.5 and improved error handling
class EnhancedVoiceChatManager:
    # Playback state per chat
    playback_state: Dict[str, Dict[str, any]] = {}

    # --- Enhanced Audio Processing with Pydub ---
    MAX_UI_VOLUME = 600          # Increased to 600% for maximum boost
    MAX_BOOST_MULT = 30.0        # Maximum boost multiplier for very high volume (keep sane headroom)

    def ui_percent_to_gain_mult(self, percent: int) -> float:
        """
        Enhanced multiplier mapping for maximum perceived loudness
        600% -> 60x pre-gain for extreme loudness
        """
        p = max(1, min(int(percent), self.MAX_UI_VOLUME))
        if p >= 600:
            return 60.0  # Maximum extreme boost
        elif p >= 500:
            return 48.0  # Very high boost
        elif p >= 400:
            return 36.0  # High boost
        elif p >= 300:
            return 24.0  # Medium-high boost
        elif p >= 200:
            return 12.0  # Medium boost
        else:
            # Progressive scaling for lower values
            return 1.0 + (p - 100) * (11.0 / 100.0)

    def build_extreme_loudness_chain(self, mult: float) -> str:
        """
        Build filter chain optimized for MAXIMUM perceived loudness
        Target: RMS ≈ -3.0 dBFS, Peak = 0.0 dBFS at 600% (much louder)
        """
        # Stage 1: Pre-processing with higher initial gain
        pre_stage = f"volume={mult}:precision=fixed,highpass=f=40:poles=2,lowpass=f=18000:poles=2,"
        
        if mult >= 55.0:  # 600% territory - MAXIMUM EXTREME LOUDNESS
            return pre_stage + (
                # Stage 1: Aggressive pre-compression to handle extreme gains
                "acompressor=threshold=-35dB:ratio=30:knee=10:attack=0.5:release=30:makeup=18,"
                
                # Stage 2: Multi-band dynamic processing simulation
                "acompressor=threshold=-30dB:ratio=25:knee=8:attack=0.5:release=40:makeup=15,"
                "acompressor=threshold=-25dB:ratio=20:knee=6:attack=0.5:release=50:makeup=12,"
                
                # Stage 3: Adaptive normalization with very tight parameters for density
                "dynaudnorm=f=500:g=35:n=1:p=0.98:m=3:s=1:r=0.9:b=1,"
                
                # Stage 4: Heavy multi-stage compression for broadcast loudness
                "acompressor=threshold=-20dB:ratio=15:knee=4:attack=0.3:release=35:makeup=10,"
                "acompressor=threshold=-15dB:ratio=10:knee=3:attack=0.3:release=25:makeup=6,"
                
                # Stage 5: Loudness normalization targeting very high levels
                "loudnorm=I=-3:TP=-0.05:LRA=1.5:dual_mono=true:linear=true:print_format=json,"
                
                # Stage 6: Final density compression and peak control
                "acompressor=threshold=-8dB:ratio=8:knee=2:attack=0.2:release=15:makeup=3,"
                
                # Stage 7: Hard limiting with minimal headroom
                "alimiter=limit=0.999:attack=0.5:release=3:asc=true,"
                
                # Stage 8: EQ optimization for maximum perceived loudness
                "equalizer=f=60:width_type=o:width=2.0:g=3.0,"     # Sub-bass boost
                "equalizer=f=200:width_type=o:width=1.5:g=2.5,"    # Low-mid warmth
                "equalizer=f=1000:width_type=o:width=1.0:g=1.5,"   # Mid presence
                "equalizer=f=3500:width_type=o:width=0.8:g=6.0,"   # High presence boost
                "equalizer=f=8000:width_type=o:width=1.0:g=-1.0,"  # Tame harsh highs slightly
                "equalizer=f=12000:width_type=o:width=1.5:g=1.0,"  # Air boost
                
                # Stage 9: Final processing
                "aresample=48000:resampler=soxr:precision=28"
            )
        
        elif mult >= 45.0:  # 500% territory - ULTRA EXTREME LOUD
            return pre_stage + (
                "acompressor=threshold=-32dB:ratio=25:knee=8:attack=0.7:release=40:makeup=16,"
                "acompressor=threshold=-28dB:ratio=20:knee=6:attack=0.7:release=50:makeup=14,"
                "dynaudnorm=f=400:g=32:n=1:p=0.9:m=4:s=2,"
                "acompressor=threshold=-22dB:ratio=12:knee=4:attack=0.5:release=40:makeup=8,"
                "loudnorm=I=-4:TP=-0.1:LRA=2:dual_mono=true:linear=true,"
                "acompressor=threshold=-10dB:ratio=6:knee=2:attack=0.3:release=20:makeup=2.5,"
                "alimiter=limit=0.998:attack=0.7:release=5,"
                "equalizer=f=3500:width_type=o:width=0.9:g=5.5,"
                "equalizer=f=8000:width_type=o:width=1.1:g=-0.8,"
                "aresample=48000:resampler=soxr"
            )
        
        elif mult >= 32.0:  # 400% territory - VERY EXTREME LOUD
            return pre_stage + (
                "acompressor=threshold=-28dB:ratio=18:knee=7:attack=1:release=60:makeup=14,"
                "dynaudnorm=f=300:g=28:n=1:p=0.8:m=6:s=3,"
                "acompressor=threshold=-18dB:ratio=10:knee=4:attack=1:release=50:makeup=6,"
                "loudnorm=I=-6:TP=-0.2:LRA=3:dual_mono=true:linear=true,"
                "alimiter=limit=0.995:attack=1:release=8,"
                "equalizer=f=3500:width_type=o:width=1.0:g=4.5,"
                "aresample=48000"
            )
        
        else:  # Normal to loud range
            return pre_stage + (
                "dynaudnorm=f=200:g=20:n=1:p=0.7:m=8:s=5,"
                "acompressor=threshold=-20dB:ratio=10:knee=4:attack=2:release=80:makeup=10,"
                "loudnorm=I=-10:TP=-1.0:LRA=5:dual_mono=true:linear=true,"
                "alimiter=limit=0.98,"
                "equalizer=f=3500:width_type=o:width=1.2:g=3.0,"
                "aresample=48000"
            )

    async def enhance_audio_with_pydub(self, input_path: str, output_path: str, volume_percent: int = 200) -> bool:
        """
        Enhanced audio processing using pydub for maximum volume and quality
        Applies multiple enhancement techniques for the best sound
        """
        try:
            logger.info(f"🎵 Enhancing audio with pydub: {input_path} -> {output_path} at {volume_percent}%")
            
            # Load audio file
            audio = AudioSegment.from_file(input_path)
            
            # Calculate volume multiplier
            volume_mult = self._ui_to_multiplier(volume_percent)
            
            # Apply multiple enhancement stages
            enhanced_audio = audio
            
            # 1. Normalize audio to consistent level
            enhanced_audio = normalize(enhanced_audio)
            
            # 2. Apply volume boost
            if volume_mult != 1.0:
                # dB gain from multiplier (correct formula)
                gain_db = 20.0 * math.log10(max(1e-6, volume_mult))
                # cap pre-compressor gain so it doesn't clip before processing
                gain_db = min(gain_db, 18.0)
                enhanced_audio = enhanced_audio + gain_db
            
            # 3. Apply dynamic range compression for consistent loudness
            # Simulate compression by limiting peaks and boosting overall level
            peak_dB = enhanced_audio.max_dBFS
            target_peak = -3.0  # Target peak level in dB
            
            if peak_dB < target_peak:
                # Boost to target level
                boost_needed = target_peak - peak_dB
                enhanced_audio = enhanced_audio + boost_needed
            
            # 4. Apply EQ enhancements for better voice clarity
            # Boost frequencies important for voice (1-4kHz)
            try:
                # High-pass filter to remove rumble
                enhanced_audio = high_pass_filter(enhanced_audio, 80)
                
                # Low-pass filter to remove harsh highs
                enhanced_audio = low_pass_filter(enhanced_audio, 15000)
                
                # Boost presence frequencies (2-4kHz) for clarity
                # This is a simplified EQ boost - pydub doesn't have direct parametric EQ
                # We'll overlay a boosted version of the audio in the target range
                presence_boost = enhanced_audio.high_pass_filter(2000).low_pass_filter(4000) + 3
                enhanced_audio = enhanced_audio.overlay(presence_boost)
                
            except Exception as eq_error:
                logger.warning(f"⚠️ EQ processing failed: {eq_error}")
            
            # 5. Apply final normalization and peak limiting
            enhanced_audio = normalize(enhanced_audio)
            
            # Ensure we don't exceed maximum digital level
            max_peak = enhanced_audio.max_dBFS
            if max_peak > -1.0:  # If too close to 0dBFS
                reduction_needed = max_peak + 1.0
                enhanced_audio = enhanced_audio - reduction_needed
            
            # 6. Export: 48 kHz, 2ch, highest VBR (sounds better than fixed 256k)
            enhanced_audio.export(
                output_path,
                format="mp3",
                bitrate="320k",
                parameters=["-ar", "48000", "-ac", "2", "-acodec", "libmp3lame", "-q:a", "0"]
            )
            
            logger.info(f"✅ Audio enhancement completed. Volume: {volume_percent}%, Output: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pydub audio enhancement failed: {e}")
            logger.error(traceback.format_exc())
            return False

    async def process_audio_with_enhancement(self, input_path: str, volume_percent: int = 200) -> str:
        """
        Process audio file with enhanced volume and quality using pydub
        Returns path to the enhanced audio file
        """
        try:
            input_file = Path(input_path)
            if not input_file.exists():
                logger.error(f"❌ Input file not found: {input_path}")
                return input_path
            
            # Generate output path
            output_path = input_file.parent / f"enhanced_{input_file.name}"
            
            # Try pydub enhancement first
            pydub_success = await self.enhance_audio_with_pydub(
                str(input_file), str(output_path), volume_percent
            )
            
            if pydub_success:
                logger.info(f"✅ Used pydub enhancement: {output_path}")
                return str(output_path)
            
            # Fallback to ffmpeg if pydub fails
            logger.warning("⚠️ Pydub failed, falling back to ffmpeg processing")
            return await self._process_audio_ffmpeg_fallback(str(input_file), volume_percent)
            
        except Exception as e:
            logger.error(f"❌ Audio processing failed: {e}")
            return input_path  # Return original path if all processing fails

    async def _process_audio_ffmpeg_fallback(self, input_path: str, volume_percent: int) -> str:
        """
        Fallback ffmpeg processing when pydub is not available or fails
        """
        try:
            input_file = Path(input_path)
            output_path = input_file.parent / f"ffmpeg_enhanced_{input_file.name}"
            
            mult = self._ui_to_multiplier(volume_percent)
            af_chain = self.build_filter_chain(mult)
            
            cmd = [
                FFMPEG_PATH, "-y",
                "-i", str(input_path),
                "-af", af_chain,
                "-ar", "48000",
                "-ac", "2",
                "-acodec", "libmp3lame",
                "-q:a", "0",     # Best quality
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ FFMPEG fallback processing completed: {output_path}")
                return str(output_path)
            else:
                logger.error(f"❌ FFMPEG fallback failed: {result.stderr}")
                return input_path
                
        except Exception as e:
            logger.error(f"❌ FFMPEG fallback processing error: {e}")
            return input_path
    # ----------------------------------------------------------------

    async def process_audio_for_maximum_loudness(self, input_path: str, output_path: str, volume_percent: int) -> bool:
        """
        Process audio using the extreme loudness chain
        Optimized for maximum perceived loudness while maintaining quality
        """
        try:
            logger.info(f"Processing audio for maximum loudness: {volume_percent}%")
            
            mult = self.ui_percent_to_gain_mult(volume_percent)
            af_chain = self.build_extreme_loudness_chain(mult)
            
            # Enhanced FFmpeg command with optimal settings
            cmd = [
                FFMPEG_PATH, "-y",
                "-i", str(input_path),
                
                # Input format optimization
                "-async", "1",
                "-vsync", "0",
                
                # Audio filtering
                "-af", af_chain,
                
                # Output format optimization for maximum quality
                "-ar", "48000",
                "-ac", "2",
                "-acodec", "libmp3lame",
                "-b:a", "320k",  # Maximum MP3 bitrate
                "-q:a", "0",     # Best quality
                
                # Additional encoding parameters for loudness preservation
                "-write_xing", "0",  # Disable Xing header for better compatibility
                "-id3v2_version", "3",
                
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully processed audio with {volume_percent}% loudness boost")
                return True
            else:
                logger.error(f"FFmpeg processing failed: {result.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"Error in maximum loudness processing: {e}")
            return False

    async def analyze_audio_levels(self, file_path: str) -> dict:
        """
        Analyze the processed audio to verify loudness levels
        """
        try:
            cmd = [
                FFMPEG_PATH, "-i", str(file_path),
                "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:key=lavfi.astats.Overall.Peak_level",
                "-f", "null", "-"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Parse RMS and Peak levels from output
            rms_match = re.search(r'RMS_level=(-?\d+\.?\d*)', result.stderr)
            peak_match = re.search(r'Peak_level=(-?\d+\.?\d*)', result.stderr)
            
            levels = {}
            if rms_match:
                levels['rms_dbfs'] = float(rms_match.group(1))
            if peak_match:
                levels['peak_dbfs'] = float(peak_match.group(1))
                
            logger.info(f"Audio analysis: RMS={levels.get('rms_dbfs', 'N/A')}dBFS, Peak={levels.get('peak_dbfs', 'N/A')}dBFS")
            return levels
            
        except Exception as e:
            logger.error(f"Error analyzing audio levels: {e}")
            return {}

    async def play_media_with_maximum_loudness(self, chat_id: Union[int, str], file_path: str,
                    settings: VoiceSettings, is_video: bool = False) -> bool:
        """
        Enhanced play_media with maximum loudness processing
        """
        try:
            async with self._lock:
                chat_id_str = str(chat_id)
                if not Path(file_path).exists():
                    logger.error(f"Media file not found: {file_path}")
                    return False
                
                if chat_id_str not in self.active_calls:
                    logger.warning(f"Not in voice chat {chat_id}")
                    return False
                    
                call_info = self.active_calls[chat_id_str]
                pytgcalls = call_info.get("pytgcalls")
                
                if not pytgcalls:
                    logger.error(f"PyTgCalls instance not available for {chat_id}")
                    return False
                    
                try:
                    # Generate enhanced output path
                    input_file = Path(file_path)
                    enhanced_path = input_file.parent / f"max_loud_{input_file.name}"
                    
                    # Process audio for maximum loudness
                    volume = call_info.get("volume", MAX_VOLUME)
                    success = await self.process_audio_for_maximum_loudness(
                        str(input_file), str(enhanced_path), volume
                    )
                    
                    if not success:
                        logger.error("Failed to process audio for maximum loudness")
                        return False
                    
                    # Analyze the processed audio levels
                    levels = await self.analyze_audio_levels(str(enhanced_path))
                    
                    # Play the enhanced audio
                    from pytgcalls.types import MediaStream
                    await pytgcalls.play(chat_id, MediaStream(str(enhanced_path)))
                    
                    # Update call info
                    self.active_calls[chat_id_str].update({
                        "playing": True,
                        "file": str(enhanced_path),
                        "volume": volume,
                        "is_video": is_video,
                        "started_at": time.time(),
                        "current_stream": str(enhanced_path),
                        "stream_type": "audio",
                        "src_file": file_path,
                        "audio_levels": levels
                    })
                    
                    self.performance_stats['total_media_played'] += 1
                    
                    rms_level = levels.get('rms_dbfs', 'Unknown')
                    peak_level = levels.get('peak_dbfs', 'Unknown')
                    logger.info(f"Playing maximum loudness audio: RMS={rms_level}dBFS, Peak={peak_level}dBFS")
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"Failed to play media with maximum loudness: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error in maximum loudness playback: {e}")
            return False

    async def play_media_with_offset(self, chat_id: Union[int, str], file_path: str, is_video: bool = False):
        """Play media from start or resume from paused position using ffmpeg -ss (PyTgCalls v2.2.6)"""
        chat_id_str = str(chat_id)
        state = self.playback_state.setdefault(chat_id_str, {"is_playing": False, "paused_at": 0, "start_time": 0, "file": file_path, "is_video": is_video})
        state["is_playing"] = True
        state["start_time"] = time.time() - state["paused_at"]
        mult = self._ui_to_multiplier(self.active_calls.get(chat_id_str, {}).get("volume", 100))
        af_chain = self.build_filter_chain(mult)
        ffmpeg_cmd = [
            FFMPEG_PATH,
            "-y",
            "-ss", str(state["paused_at"]),
            "-i", str(file_path),
            "-vn" if not is_video else "",
            "-af", af_chain,
            "-ar", "48000",
            "-ac", "2",
            "-acodec", "libmp3lame",
            "-q:a", "0",
            "-f", "mp3",
            str(file_path) + ".seek.mp3"
        ]
        ffmpeg_cmd = [x for x in ffmpeg_cmd if x]
        import subprocess
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ ffmpeg error: {result.stderr}")
            return
        from pytgcalls.types import MediaStream
        pytgcalls = self.active_calls[chat_id_str]["pytgcalls"]
        stream = MediaStream(str(file_path) + ".seek.mp3")
        await pytgcalls.play(int(chat_id), stream)
        self.active_calls[chat_id_str]["playing"] = True
        self.active_calls[chat_id_str]["current_stream"] = str(file_path) + ".seek.mp3"
        self.active_calls[chat_id_str]["stream_type"] = "video" if is_video else "audio"
        print(f"▶️ Playing from {state['paused_at']}s ({'Video' if is_video else 'Audio'})")

    async def pause_media(self, chat_id: Union[int, str]) -> bool:
        """Pause and remember position, always save file and playback info"""
        chat_id_str = str(chat_id)
        call_info = self.active_calls.get(chat_id_str, {})
        current_stream = call_info.get("current_stream")
        is_video = call_info.get("stream_type") == "video"
        state = self.playback_state.setdefault(chat_id_str, {"is_playing": False, "paused_at": 0, "start_time": 0, "file": None, "is_video": is_video})
        if state["is_playing"]:
            elapsed = time.time() - state.get("start_time", 0)
            state["paused_at"] += int(elapsed)
            pytgcalls = call_info.get("pytgcalls")
            # Try pause, fallback to stop_playout
            if pytgcalls:
                if hasattr(pytgcalls, "pause"):
                    await pytgcalls.pause(int(chat_id))
                elif hasattr(pytgcalls, "stop_playout"):
                    await pytgcalls.stop_playout(int(chat_id))
                else:
                    logger.error("❌ PyTgCalls has no pause or stop_playout method!")
            state["is_playing"] = False
            self.active_calls[chat_id_str]["playing"] = False
            # Always save the current file and video state for resume
            if current_stream:
                state["file"] = current_stream
            state["is_video"] = is_video
            print(f"⏸️ Paused at {state['paused_at']}s, file: {state['file']}")
            return True
        return False

    async def resume_media(self, chat_id: Union[int, str]) -> bool:
        """Resume playback from last paused position, updating state correctly"""
        chat_id_str = str(chat_id)
        state = self.playback_state.setdefault(chat_id_str, {"is_playing": False, "paused_at": 0, "file": None, "is_video": False, "start_time": 0})
        # Only resume if paused and file is available
        if not state["is_playing"] and state["file"] is not None:
            try:
                await self.play_media_with_offset(chat_id, state["file"], state.get("is_video", False))
                state["is_playing"] = True
                state["start_time"] = time.time() - state["paused_at"]
                # Reset paused_at after resuming
                state["paused_at"] = 0
                return True
            except Exception as e:
                logger.error(f"❌ Failed to resume media in {chat_id}: {e}")
                return False
        return False
    """Enhanced Voice Chat Manager with modern PyTgCalls 2.2.5 support"""
    
    def __init__(self):
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        self.performance_stats = {
            "total_joins": 0,
            "successful_joins": 0,
            "failed_joins": 0,
            "total_media_played": 0,
            "connection_errors": 0
        }
        self.playlist_queues: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()
        self.reconnection_attempts: Dict[str, int] = {}
        self.max_reconnection_attempts = 3
        
    # Removed initialize_pytgcalls: not needed with GroupCallFactory API
    # ...existing code...

    async def join_voice_chat(self, client, chat_id: int | str, placeholder="silence.mp3"):
        """Join voice chat using PyTgCalls and AudioPiped (official pytgcalls API)"""
        try:
            async with self._lock:
                chat_id_str = str(chat_id)
                self.performance_stats['total_joins'] += 1
                if chat_id_str in self.active_calls:
                    logger.warning(f"⚠️ Already in voice chat in {chat_id}")
                    return self.active_calls[chat_id_str].get("pytgcalls")
                await self._ensure_silence_file()
                pytgcalls = PyTgCalls(client)
                await pytgcalls.start()
                stream = MediaStream("D:/vc bot/silence.mp3")
                await pytgcalls.play(chat_id, stream)
                me = await client.get_me()
                self.active_calls[chat_id_str] = {
                    "phone": getattr(me, "phone", "unknown"),
                    "joined_at": time.time(),
                    "playing": False,
                    "client": client,
                    "pytgcalls": pytgcalls,
                    "entity_id": int(chat_id),
                    "user_id": me.id,
                    "user_name": f"{me.first_name} {me.last_name or ''}".strip(),
                    "current_stream": stream,
                    "stream_type": "audio",
                    "chat_title": "Unknown Chat"
                }
                self.playlist_queues[chat_id_str] = []
                self.performance_stats['successful_joins'] += 1
                logger.info(f"✅ Successfully joined voice chat {chat_id} with PyTgCalls")
                return pytgcalls
        except Exception as e:
            logger.error(f"❌ Error joining voice chat: {e}")
            logger.error(traceback.format_exc())
            self.performance_stats['failed_joins'] += 1
            return None

    async def leave_voice_chat(self, chat_id: Union[int, str]) -> bool:
        """Leave voice chat using PyTgCalls.leave_call (official method)"""
        try:
            async with self._lock:
                chat_id_str = str(chat_id)
                if chat_id_str not in self.active_calls:
                    logger.warning(f"⚠️ Not in voice chat {chat_id}")
                    return False
                call_info = self.active_calls[chat_id_str]
                pytgcalls = call_info.get("pytgcalls")
                if pytgcalls:
                    try:
                        # Official recommended method per docs
                        await pytgcalls.leave_call(int(chat_id))
                        logger.info(f"✅ Left voice chat {chat_id} using PyTgCalls.leave_call")
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"❌ Error leaving voice chat: {e}")
                await self._cleanup_call(chat_id_str)
                return True
        except Exception as e:
            logger.error(f"❌ Error leaving voice chat {chat_id}: {e}")
            return False

    async def play_media(self, chat_id: Union[int, str], file_path: str,
                        settings: VoiceSettings, is_video: bool = False) -> bool:
        """Play media (audio only) using official pytgcalls API"""
        try:
            async with self._lock:
                chat_id_str = str(chat_id)
                if not Path(file_path).exists():
                    logger.error(f"❌ Media file not found: {file_path}")
                    return False
                if chat_id_str not in self.active_calls:
                    logger.warning(f"⚠️ Not in voice chat {chat_id}")
                    return False
                call_info = self.active_calls[chat_id_str]
                pytgcalls = call_info.get("pytgcalls")
                if not pytgcalls:
                    logger.error(f"❌ PyTgCalls instance not available for {chat_id}")
                    return False
                try:
                    if is_video:
                        logger.error("❌ Video playback is not supported by pytgcalls.")
                        return False
                    mult = self._ui_to_multiplier(call_info.get("volume", 100))
                    af_chain = self.build_filter_chain(mult)
                    adjusted_path = str(file_path) + ".adjusted.mp3"
                    ffmpeg_cmd = [
                        FFMPEG_PATH,
                        "-y",
                        "-i", str(file_path),
                        "-af", af_chain,
                        "-ar", "48000",
                        "-ac", "2",
                        "-acodec", "libmp3lame",
                        "-q:a", "0",
                        "-f", "mp3",
                        adjusted_path
                    ]
                    import subprocess
                    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        logger.error(f"❌ ffmpeg error: {result.stderr}")
                        return False
                    await pytgcalls.play(chat_id, MediaStream(adjusted_path))
                    self.active_calls[chat_id_str].update({
                        "playing": True,
                        "file": adjusted_path,
                        "volume": MAX_VOLUME,
                        "is_video": is_video,
                        "started_at": time.time(),
                        "current_stream": adjusted_path,
                        "stream_type": "audio",
                        "src_file": file_path  # Store original file path
                    })
                    self.performance_stats['total_media_played'] += 1
                    logger.info(f"✅ Playing enhanced audio in {chat_id} with PyTgCalls")
                    return True
                except Exception as e:
                    logger.error(f"❌ Failed to play media: {e}")
                    return False
        except Exception as e:
            logger.error(f"❌ Error playing media in {chat_id}: {e}")
            return False

    async def set_volume(self, chat_id: Union[int, str], volume: int) -> bool:
        """Set volume for voice chat using original source file to avoid re-compression"""
        try:
            chat_id_str = str(chat_id)
            if chat_id_str not in self.active_calls:
                return False

            volume = max(10, min(MAX_VOLUME, volume))
            call_info = self.active_calls[chat_id_str]

            current_stream = call_info.get("current_stream")
            if not current_stream or not call_info.get("playing", False):
                logger.warning(f"⚠️ No active stream to adjust volume in {chat_id}")
                return False

            self.active_calls[chat_id_str]["volume"] = volume
            
            # Use original source file if available to avoid re-compressing already compressed audio
            src_file = call_info.get("src_file")
            if src_file and Path(src_file).exists():
                file_path = src_file
                logger.info(f"🎵 Using original source file for volume adjustment: {file_path}")
            else:
                # Fallback to current stream if source file is not available
                file_path = current_stream
                logger.warning(f"⚠️ Source file not available, using current stream: {file_path}")
            
            is_video = call_info.get("stream_type") == "video"

            pytgcalls = call_info.get("pytgcalls")
            if pytgcalls:
                try:
                    import tempfile
                    import subprocess

                    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                    temp_path = temp_file.name
                    temp_file.close()

                    mult = self._ui_to_multiplier(volume)
                    af_chain = self.build_filter_chain(mult)
                    cmd = [
                        FFMPEG_PATH, "-y",
                        "-i", str(file_path),
                        "-af", af_chain,
                        "-ar", "48000",
                        "-ac", "2",
                        "-acodec", "libmp3lame",
                        "-q:a", "0",
                        "-f", "mp3", temp_path
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True)

                    if result.returncode == 0:
                        from pytgcalls.types import MediaStream
                        await pytgcalls.play(int(chat_id), MediaStream(temp_path))
                        self.active_calls[chat_id_str]["current_stream"] = temp_path
                        self.active_calls[chat_id_str]["temp_file"] = temp_path
                        logger.info(f"🔊 Set volume to {volume}% in {chat_id} using original source (quality preserved)")
                        return True
                    else:
                        logger.error(f"❌ Failed to adjust volume with ffmpeg: {result.stderr}")
                        return False

                except Exception as e:
                    logger.error(f"❌ Failed to adjust volume: {e}")
                    return False

            return False
        except Exception as e:
            logger.error(f"❌ Error setting volume: {e}")
            return False

    async def _ensure_silence_file(self):
        """Ensure silence.mp3 file exists for voice chat operations"""
        silence_path = Path("silence.mp3")
        if silence_path.exists():
            return
            
        try:
            logger.info("🔧 Creating silence.mp3 file...")
            
            # Try to create using ffmpeg first
            try:
                result = subprocess.run([
                    FFMPEG_PATH, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-t", "1", "-c:a", "libmp3lame", "-q:a", "0", "-y", str(silence_path)
                ], check=True, capture_output=True, text=True)
                
                if silence_path.exists() and silence_path.stat().st_size > 0:
                    logger.info("✅ Created silence.mp3 using ffmpeg")
                    return
                    
            except (subprocess.CalledProcessError, FileNotFoundError) as ffmpeg_error:
                logger.warning(f"⚠️ FFmpeg method failed: {ffmpeg_error}")
                
                # Fallback: Create a minimal MP3 file manually
                logger.info("🔄 Creating basic silence file as fallback...")
                mp3_data = bytearray([
                    0xFF, 0xFB, 0x90, 0x00,  # MP3 Header
                    0x00, 0x00, 0x00, 0x00,  # CRC + padding
                ])
                
                # Add silent frames
                silent_frame = bytes([0x00] * 417)
                for _ in range(38):
                    mp3_data.extend(silent_frame)
                
                with open(silence_path, 'wb') as f:
                    f.write(mp3_data)
                
                logger.info("✅ Created basic silence.mp3 file")
                
        except Exception as e:
            logger.error(f"❌ Failed to create silence.mp3: {e}")
            raise

    def _ui_to_multiplier(self, volume_percent: int) -> float:
        """
        100% -> 1.0x, 600% -> ~28.0x (OVERKILL entry).
        """
        volume_percent = max(1, min(MAX_VOLUME, int(volume_percent)))
        return 1.0 + (volume_percent - 100) * (27.0 / 500.0)

    def build_filter_chain(self, mult: float) -> str:
        """
        Build audio filter chain for volume processing
        This is a legacy method for backward compatibility
        """
        return self.build_extreme_loudness_chain(mult)

    async def _cleanup_call(self, chat_id_str: str):
        """Enhanced cleanup for voice calls"""
        try:
            # Clean up temporary files if any
            if chat_id_str in self.active_calls:
                call_info = self.active_calls[chat_id_str]
                temp_file = call_info.get("temp_file")
                if temp_file and Path(temp_file).exists():
                    try:
                        Path(temp_file).unlink()
                        logger.info(f"🧹 Cleaned up temporary file: {temp_file}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to clean up temp file: {e}")
                
                del self.active_calls[chat_id_str]
            
            if chat_id_str in self.playlist_queues:
                del self.playlist_queues[chat_id_str]
            if chat_id_str in self.reconnection_attempts:
                del self.reconnection_attempts[chat_id_str]
        except Exception as e:
            logger.error(f"❌ Error cleaning up call: {e}")

    async def _handle_stream_end(self, chat_id: int, phone: str):
        """Enhanced stream end handler with auto-queue management"""
        try:
            chat_id_str = str(chat_id)
            
            if chat_id_str in self.playlist_queues and self.playlist_queues[chat_id_str]:
                next_item = self.playlist_queues[chat_id_str].pop(0)
                settings = VoiceSettings(**next_item.get('settings', {}))
                
                logger.info(f"🎵 Auto-playing next queued item: {next_item['file']}")
                
                await asyncio.sleep(1) # Small delay
                
                success = await self.play_media(
                    chat_id,
                    next_item['file'],
                    settings,
                    next_item.get('is_video', False)
                )
                
                if not success and self.playlist_queues[chat_id_str]:
                    await self._handle_stream_end(chat_id, phone)
            else:
                if chat_id_str in self.active_calls:
                    self.active_calls[chat_id_str]["playing"] = False
                    logger.info(f"📻 Playlist finished for {chat_id}")
                    
        except Exception as e:
            logger.error(f"❌ Error handling stream end: {e}")

    async def _handle_kick_with_reconnection(self, chat_id: int, phone: str):
        """Handle being kicked with reconnection logic"""
        try:
            chat_id_str = str(chat_id)
            await self._cleanup_call(chat_id_str)
            
            if chat_id_str not in self.reconnection_attempts:
                self.reconnection_attempts[chat_id_str] = 0
            
            if self.reconnection_attempts[chat_id_str] < self.max_reconnection_attempts:
                self.reconnection_attempts[chat_id_str] += 1
                reconnect_delay = 10 * self.reconnection_attempts[chat_id_str]
                
                logger.info(f"🔄 Attempting reconnection to {chat_id} in {reconnect_delay} seconds")
                await asyncio.sleep(reconnect_delay)
                
                if phone in user_clients:
                    client, _ = user_clients[phone]
                    success = await self.join_voice_chat(client, chat_id, phone)
                    
                    if success:
                        self.reconnection_attempts[chat_id_str] = 0
                        logger.info(f"✅ Successfully reconnected to {chat_id}")
                        
        except Exception as e:
            logger.error(f"❌ Error in reconnection handler: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive voice chat status"""
        return {
            "active_calls": len(self.active_calls),
            "calls": dict(self.active_calls),
            "total_queued": sum(len(queue) for queue in self.playlist_queues.values()),
            "queue_info": {chat_id: len(queue) for chat_id, queue in self.playlist_queues.items()},
            "performance_stats": self.performance_stats.copy()
        }

# Initialize the enhanced voice chat manager
voice_manager = EnhancedVoiceChatManager()

# FSM States for modern Aiogram 3.15.0
class AccountStates(StatesGroup):
    phone = State()
    otp = State()
    password = State()

class VoiceChatStates(StatesGroup):
    target_chat = State()
    account_selection = State()
    media_file = State()

# Utility functions with enhanced error handling
def is_owner(user_id: int) -> bool:
    """Check if user is owner"""
    return user_id in OWNER_IDS

async def safe_json_operation(file_path: str, operation: str, data: Any = None) -> Any:
    """Safely perform JSON operations with orjson optimization"""
    try:
        if operation == "write":
            if JSON_PERFORMANCE:
                try:
                    import orjson
                    json_data = orjson.dumps(data, option=orjson.OPT_INDENT_2)
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(json_data)
                except ImportError:
                    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(data, indent=2, ensure_ascii=False))
            return True
        elif operation == "read":
            if not Path(file_path).exists():
                return {}
            if JSON_PERFORMANCE:
                try:
                    import orjson
                    async with aiofiles.open(file_path, 'rb') as f:
                        content = await f.read()
                        return orjson.loads(content) if content else {}
                except ImportError:
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        return json.loads(content) if content.strip() else {}
            else:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content) if content.strip() else {}
    except Exception as e:
        logger.error(f"❌ JSON operation error ({operation}) in {file_path}: {e}")
        return {} if operation == "read" else False

async def save_users():
    """Save user sessions with enhanced security"""
    try:
        data = {}
        for phone, (client, session_string) in user_clients.items():
            data[phone] = session_string
        
        success = await safe_json_operation('users.json', 'write', data)
        if success:
            logger.info(f"✅ Saved {len(data)} user sessions")
        else:
            logger.error("❌ Failed to save user sessions")
    except Exception as e:
        logger.error(f"❌ Error saving users: {e}")

async def load_users():
    """Load user sessions with enhanced validation"""
    try:
        data = await safe_json_operation('users.json', 'read')
        if not data:
            logger.info("📂 No existing user data found")
            return
        
        loaded_count = 0
        for phone, session_string in data.items():
            try:
                if not session_string or not isinstance(session_string, str):
                    continue
                
                client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
                await client.connect()
                
                if await client.is_user_authorized():
                    user_clients[phone] = (client, session_string)
                    loaded_count += 1
                    logger.info(f"✅ Loaded account: +{phone[-4:]}")
                else:
                    await client.disconnect()
                    
            except Exception as e:
                logger.error(f"❌ Failed to load account {phone}: {e}")
                
        logger.info(f"📊 Loaded {loaded_count} accounts successfully")
        
    except Exception as e:
        logger.error(f"❌ Error loading users: {e}")

async def get_account_selection_keyboard() -> InlineKeyboardMarkup:
    """Generate account selection keyboard"""
    buttons = []
    
    if not user_clients:
        buttons.append([InlineKeyboardButton(text="❌ No accounts available", callback_data="no_accounts")])
    else:
        for i, phone in enumerate(list(user_clients.keys())[:10]):
            buttons.append([InlineKeyboardButton(
                text=f"📱 {phone}",  # Show full phone number
                callback_data=f"select_account:{phone}"
            )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_chat_list_keyboard(client: TelegramClient) -> InlineKeyboardMarkup:
    """Generate chat list keyboard"""
    buttons = []
    
    try:
        # Get dialogs (recent chats)
        dialogs = await client.get_dialogs(limit=20)
        
        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:
                # Truncate long chat names
                name = dialog.name[:30] + "..." if len(dialog.name) > 30 else dialog.name
                buttons.append([InlineKeyboardButton(
                    text=f"💬 {name}",
                    callback_data=f"target_chat:{dialog.id}"
                )])
        
    except Exception as e:
        logger.error(f"❌ Error getting chat list: {e}")
        buttons.append([InlineKeyboardButton(text="❌ Error loading chats", callback_data="error")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Modern Aiogram 3.15.0 handlers
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Enhanced start command with feature detection"""
    try:
        if not is_owner(message.from_user.id):
            logger.warning(f"Access denied for user ID: {message.from_user.id}")
            await message.reply("❌ Access denied. This bot is private.")
            return
        logger.info(f"User ID: {message.from_user.id}, OWNER_IDS: {OWNER_IDS}")
        logger.info("✅ Access granted. Displaying main menu.")
        
        status = voice_manager.get_status()
        
        features = ["✅ py-tgcalls 2.2.5 GroupCallFactory (Auto-installed)"]
        if QUALITY_CLASSES_AVAILABLE:
            features.append("✅ Enhanced Quality Control")
    # INPUT_STREAM not available in v2.2.6
        if STREAM_EVENTS_AVAILABLE:
            features.append("✅ Auto-Queue Management")
        if JSON_PERFORMANCE:
            features.append("⚡ JSON Performance (orjson)")
        if AIOHTTP_AVAILABLE:
            features.append("⚡ HTTP Speedups")
        if PSUTIL_AVAILABLE:
            features.append("📊 Performance Monitoring")
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎤 Voice Chat", callback_data="voice_chat")],
            [InlineKeyboardButton(text="👥 Accounts", callback_data="accounts")],
            [InlineKeyboardButton(text="📊 Status", callback_data="status")]
        ])
        
        await message.reply(
            f"🎵 **Modern Voice Chat Bot**\n\n"
            f"📱 **Accounts:** {len(user_clients)}\n"
            f"🎤 **Active Calls:** {status['active_calls']}\n"
            f"📋 **Queued Items:** {status['total_queued']}\n\n"
            f"Select an option:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Error in start command: {e}")
        await message.reply("❌ An error occurred. Please try again.")

@dp.callback_query(F.data == "voice_chat")
async def callback_voice_chat(callback: CallbackQuery):
    """Voice chat menu with py-tgcalls 2.5 GroupCallFactory features"""
    try:
        status = voice_manager.get_status()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎤 Join Voice Chat", callback_data="join_voice")],
            [InlineKeyboardButton(text="🔇 Leave Voice Chat", callback_data="leave_voice")],
            [InlineKeyboardButton(text="🎵 Play Audio", callback_data="play_audio")],
            [InlineKeyboardButton(text="🎬 Play Video", callback_data="play_video")],
            [
                InlineKeyboardButton(text="⏸️ Pause", callback_data="pause"),
                InlineKeyboardButton(text="▶️ Resume", callback_data="resume"),
                InlineKeyboardButton(text="⏹️ Stop", callback_data="stop")
            ],
            [InlineKeyboardButton(text="🔊 Volume Control", callback_data="volume_control")],
            [InlineKeyboardButton(text="📊 Voice Status", callback_data="voice_status")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="main")]
        ])
        
        await callback.message.edit_text(
            f"🎤 **Voice Chat Control**\n\n"
            f"🎵 **Active Calls:** {status['active_calls']}\n"
            f"📋 **Total Queued:** {status['total_queued']}\n"
            f"🔧 **py-tgcalls:** ✅ Ready (v2.2.5 GroupCallFactory)\n\n"
            f"🆕 **Modern Features:**\n"
            f"• Enhanced quality control with InputStreams\n"
            f"• Auto-reconnection on disconnect\n"
            f"• Playlist queue management\n"
            f"• Performance monitoring\n"
            f"• Video+Audio streaming support\n\n"
            f"Select an option:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Error in voice chat menu: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "join_voice")
async def callback_join_voice(callback: CallbackQuery):
    """Join voice chat handler"""
    try:
        if not user_clients:
            await callback.answer("❌ No accounts available. Add an account first.", show_alert=True)
            return
            
        keyboard = await get_account_selection_keyboard()
        await callback.message.edit_text(
            "📱 **Select Account to Join Voice Chat**\n\n"
            "Choose an account to join voice chat:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Error in join voice handler: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data.startswith("select_account:"))
async def callback_select_account(callback: CallbackQuery):
    """Account selection handler"""
    try:
        phone = callback.data.split(":", 1)[1]
        
        if phone not in user_clients:
            await callback.answer("❌ Account not found", show_alert=True)
            return
            
        client, _ = user_clients[phone]
        keyboard = await get_chat_list_keyboard(client)
        
        await callback.message.edit_text(
            f"💬 **Select Chat for {phone}**\n\n"  # Show full phone number
            "Choose a group or channel to join:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        # Store selected account in callback data for next step
        active_operations[str(callback.from_user.id)] = {"selected_phone": phone}
        
    except Exception as e:
        logger.error(f"❌ Error in account selection: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data.startswith("target_chat:"))
async def callback_target_chat(callback: CallbackQuery):
    """Target chat selection handler"""
    try:
        chat_id = callback.data.split(":", 1)[1]
        user_op = active_operations.get(str(callback.from_user.id))
        
        if not user_op or "selected_phone" not in user_op:
            await callback.answer("❌ Please select an account first", show_alert=True)
            return
            
        phone = user_op["selected_phone"]
        
        if phone not in user_clients:
            await callback.answer("❌ Account not available", show_alert=True)
            return
            
        client, _ = user_clients[phone]
        
        # Join voice chat
        await callback.message.edit_text(
            f"🔄 **Joining Voice Chat**\n\n"
            f"📱 Account: {phone}\n"  # Show full phone number
            f"💬 Chat ID: {chat_id}\n\n"
            f"Please wait...",
            parse_mode="Markdown"
        )
        
        success = await voice_manager.join_voice_chat(client, int(chat_id), phone)
        
        if success:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎵 Play Audio", callback_data="play_audio")],
                [InlineKeyboardButton(text="🎬 Play Video", callback_data="play_video")],
                [InlineKeyboardButton(text="🔇 Leave", callback_data=f"leave_specific:{chat_id}")],
                [InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")]
            ])
            
            await callback.message.edit_text(
                f"✅ **Successfully Joined Voice Chat**\n\n"
                f"📱 Account: {phone}\n"  # Show full phone number
                f"💬 Chat ID: {chat_id}\n"
                f"🎤 Status: Connected\n\n"
                f"What would you like to do?",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Try Again", callback_data=f"target_chat:{chat_id}")],
                [InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")]
            ])
            
            await callback.message.edit_text(
                f"❌ **Failed to Join Voice Chat**\n\n"
                f"📱 Account: {phone}\n"  # Show full phone number
                f"💬 Chat ID: {chat_id}\n\n"
                f"Possible reasons:\n"
                f"• No active voice chat in this group\n"
                f"• Account doesn't have permission\n"
                f"• Connection issues\n\n"
                f"Try again or check the logs for details.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        # Clean up operation data
        if str(callback.from_user.id) in active_operations:
            del active_operations[str(callback.from_user.id)]
            
    except Exception as e:
        logger.error(f"❌ Error in target chat selection: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "leave_voice")
async def callback_leave_voice(callback: CallbackQuery):
    """Leave voice chat handler"""
    try:
        status = voice_manager.get_status()
        
        if not status['calls']:
            await callback.answer("❌ No active voice chats", show_alert=True)
            return
            
        buttons = []
        for chat_id, call_info in status['calls'].items():
            phone = call_info.get('phone', 'Unknown')
            chat_title = call_info.get('chat_title', f'Chat {chat_id}')
            buttons.append([InlineKeyboardButton(
                text=f"🔇 Leave {chat_title} ({phone})",  # Show full phone number
                callback_data=f"leave_specific:{chat_id}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔇 Leave All", callback_data="leave_all")])
        buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"🔇 **Leave Voice Chat**\n\n"
            f"🎤 **Active Calls:** {len(status['calls'])}\n\n"
            f"Select which voice chat to leave:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Error in leave voice handler: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data.startswith("leave_specific:"))
async def callback_leave_specific(callback: CallbackQuery):
    """Leave specific voice chat"""
    try:
        chat_id = callback.data.split(":", 1)[1]
        
        await callback.message.edit_text(
            f"🔄 **Leaving Voice Chat**\n\n"
            f"💬 Chat ID: {chat_id}\n\n"
            f"Please wait...",
            parse_mode="Markdown"
        )
        
        success = await voice_manager.leave_voice_chat(chat_id)
        
        if success:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Voice Chat", callback_data="voice_chat")]
            ])
            
            await callback.message.edit_text(
                f"✅ **Successfully Left Voice Chat**\n\n"
                f"💬 Chat ID: {chat_id}\n"
                f"🔇 Status: Disconnected",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Try Again", callback_data=f"leave_specific:{chat_id}")],
                [InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")]
            ])
            
            await callback.message.edit_text(
                f"❌ **Failed to Leave Voice Chat**\n\n"
                f"💬 Chat ID: {chat_id}\n\n"
                f"The voice chat may have already ended.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"❌ Error leaving specific voice chat: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "resume_all")
async def callback_resume_all(callback: CallbackQuery):
    """Resume playback in all active voice chats (optimized)"""
    try:
        status = voice_manager.get_status()
        if not status['calls']:
            await callback.answer("❌ No active voice chats", show_alert=True)
            return
        # Resume all in parallel for faster response
        await asyncio.gather(*(voice_manager.resume_media(chat_id) for chat_id in status['calls'].keys()))
        await callback.answer("▶️ Playback resumed in all chats.", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in resume_all handler: {e}")
        await callback.answer("❌ Error resuming playback.", show_alert=True)
        failed_count = 0
        
        for chat_id in list(status['calls'].keys()):
            try:
                success = await voice_manager.leave_voice_chat(chat_id)
                if success:
                    left_count += 1
                else:
                    failed_count += 1
                await asyncio.sleep(1)  # Small delay between leaves
            except Exception as e:
                logger.error(f"❌ Failed to leave {chat_id}: {e}")
                failed_count += 1
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Voice Chat", callback_data="voice_chat")]
        ])
        
        await callback.message.edit_text(
            f"📊 **Leave Operation Complete**\n\n"
            f"✅ **Successfully left:** {left_count}\n"
            f"❌ **Failed to leave:** {failed_count}\n"
            f"🎤 **Remaining calls:** {len(voice_manager.get_status()['calls'])}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"❌ Error leaving all voice chats: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "play_audio")
async def callback_play_audio(callback: CallbackQuery, state: FSMContext):
    """Play audio handler"""
    try:
        status = voice_manager.get_status()
        
        if not status['calls']:
            await callback.answer("❌ No active voice chats. Join a voice chat first.", show_alert=True)
            return
            
        await callback.message.edit_text(
            f"🎵 **Play Audio File**\n\n"
            f"📁 Send an audio file (MP3, WAV, OGG, M4A, etc.)\n"
            f"📊 Active calls: {len(status['calls'])}\n\n"
            f"🎤 The audio will be played in all active voice chats.\n\n"
            f"📎 **Please send your audio file now:**\n\n"
            f"Pause/Resume is not supported.",
            parse_mode="Markdown"
        )
        
        await state.set_state(VoiceChatStates.media_file)
        await state.update_data(media_type="audio")
        
    except Exception as e:
        logger.error(f"❌ Error in play audio handler: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "play_video")
async def callback_play_video(callback: CallbackQuery, state: FSMContext):
    """Play video handler"""
    try:
        status = voice_manager.get_status()
        
        if not status['calls']:
            await callback.answer("❌ No active voice chats. Join a voice chat first.", show_alert=True)
            return
            
        await callback.message.edit_text(
            f"🎬 **Play Video File**\n\n"
            f"📁 Send a video file (MP4, AVI, MKV, etc.)\n"
            f"📊 Active calls: {len(status['calls'])}\n\n"
            f"❌ Video playback is not supported by PyTgCalls.\n\n"
            f"📎 **Please send your video file now (audio only will play):**",
            parse_mode="Markdown"
        )
        
        await state.set_state(VoiceChatStates.media_file)
        await state.update_data(media_type="video")
        
    except Exception as e:
        logger.error(f"❌ Error in play video handler: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.message(VoiceChatStates.media_file)
async def handle_media_file(message: Message, state: FSMContext):
    """Handle uploaded media file"""
    try:
        data = await state.get_data()
        media_type = data.get("media_type", "audio")
        
        # Check if message has media
        if not (message.audio or message.video or message.voice or message.video_note or message.document):
            await message.reply("❌ Please send a valid audio or video file.")
            return
        
        # Get file info
        file_info = None
        file_name = None
        
        if message.audio:
            file_info = message.audio
            file_name = file_info.file_name or f"audio_{int(time.time())}.mp3"
        elif message.video:
            file_info = message.video
            file_name = file_info.file_name or f"video_{int(time.time())}.mp4"
        elif message.voice:
            file_info = message.voice
            file_name = f"voice_{int(time.time())}.ogg"
        elif message.video_note:
            file_info = message.video_note
            file_name = f"video_note_{int(time.time())}.mp4"
        elif message.document:
            file_info = message.document
            file_name = file_info.file_name or f"document_{int(time.time())}"
        
        if not file_info:
            await message.reply("❌ Invalid file type.")
            return
        
        # Check file size (limit to 50MB for stability)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_info.file_size > max_size:
            await message.reply(f"❌ File too large. Maximum size: {max_size // 1024 // 1024}MB")
            return
        
        # Download file
        status_msg = await message.reply(
            f"📥 **Downloading {media_type.title()} File**\n\n"
            f"📁 **File:** `{file_name}`\n"
            f"📊 **Size:** {file_info.file_size / 1024 / 1024:.1f}MB\n\n"
            f"⏳ Please wait...",
            parse_mode="Markdown"
        )

        try:
            # Create media directory
            media_dir = Path("media")
            media_dir.mkdir(exist_ok=True)
            
            # Download file
            file_path = media_dir / file_name
            file = await bot.get_file(file_info.file_id)
            await bot.download_file(file.file_path, file_path)
            file_path = file_path.resolve()
            data = await state.get_data()
            volume_db = data.get("volume_db", 0)
            # Refined ffmpeg filter chain for crystal-clear, natural, and powerful audio
            if volume_db != 0:
                try:
                    adjusted_path = (media_dir / f"adjusted_{file_name}").resolve()
                    ext = file_path.suffix.lower()
                    # Use the new helpers for volume mapping and filter chain
                    mult = voice_manager._ui_to_multiplier(volume_db)
                    af_chain = voice_manager.build_filter_chain(mult)
                    cmd = [
                        FFMPEG_PATH,
                        "-y",
                        "-i", str(file_path),
                        "-af", af_chain,
                        "-ar", "48000",
                        "-ac", "2",
                        "-acodec", "libmp3lame",
                        "-q:a", "0",
                        str(adjusted_path)
                    ]
                    if ext in [".mp4", ".mkv", ".avi", ".mov"]:
                        cmd.insert(4, "-vcodec")
                        cmd.insert(5, "copy")
                    import subprocess
                    if not file_path.exists():
                        logger.error(f"❌ Input file does not exist: {file_path}")
                        await status_msg.edit_text(f"❌ Input file does not exist: `{file_path}`")
                        await state.clear()
                        return
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        logger.error(f"❌ ffmpeg error: {result.stderr}")
                        await status_msg.edit_text(f"❌ ffmpeg error: ```\n{result.stderr}\n```")
                        await state.clear()
                        return
                    file_path = adjusted_path
                except Exception as e:
                    logger.error(f"❌ Error adjusting volume: {e}")
                    await status_msg.edit_text(f"❌ Error adjusting volume: `{str(e)}`")
                    await state.clear()
                    return
            
            # Update status
            await status_msg.edit_text(
                f"🎵 **Playing {media_type.title()}**\n\n"
                f"📁 **File:** `{file_name}`\n"
                f"📊 **Size:** {file_info.file_size / 1024 / 1024:.1f}MB\n\n"
                f"🔄 Starting playback in all active voice chats...",
                parse_mode="Markdown"
            )
            
            # Get voice settings for user
            user_settings = voice_settings.get(message.from_user.id, VoiceSettings())
            is_video = media_type == "video" or message.video or message.video_note
            
            # Play in all active voice chats with offset tracking
            play_results = []
            status = voice_manager.get_status()
            for chat_id in status['calls'].keys():
                try:
                    await voice_manager.play_media_with_offset(chat_id, str(file_path), is_video)
                    play_results.append((chat_id, True))
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"❌ Failed to play in {chat_id}: {e}")
                    play_results.append((chat_id, False))
            
            # Report results
            successful_plays = sum(1 for _, success in play_results if success)
            total_chats = len(play_results)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="⏸️ Pause", callback_data="pause_all"),
                    InlineKeyboardButton(text="▶️ Resume", callback_data="resume_all"),
                    InlineKeyboardButton(text="⏹️ Stop", callback_data="stop_all")
                ],
                [InlineKeyboardButton(text="🔊 Volume", callback_data="volume_control")],
                [InlineKeyboardButton(text="🔙 Back", callback_data="voice_chat")]
            ])
            
            await status_msg.edit_text(
                f"{'✅' if successful_plays > 0 else '❌'} **Playback Started**\n\n"
                f"📁 **File:** `{file_name}`\n"
                f"🎵 **Type:** {media_type.title()}\n"
                f"📊 **Success:** {successful_plays}/{total_chats} chats\n\n"
                f"🎤 **Now playing in active voice chats**",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing media file: {e}")
            await status_msg.edit_text(
                f"❌ **Error Processing File**\n\n"
                f"📁 **File:** `{file_name}`\n"
                f"❌ **Error:** ```\n{str(e)[:100]}...\n```\n\n"
                f"Please try with a different file.",
                parse_mode="Markdown"
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Error handling media file: {e}")
        await message.reply("❌ An error occurred while processing your file.")
        await state.clear()

@dp.callback_query(F.data == "pause")
async def _shim_pause(callback: CallbackQuery):
    """Shim for pause button"""
    await callback_pause_all(callback)

@dp.callback_query(F.data == "resume")
async def _shim_resume(callback: CallbackQuery):
    """Shim for resume button"""
    await callback_resume_all(callback)

@dp.callback_query(F.data.in_({"stop", "stop_all"}))
async def callback_stop_all(callback: CallbackQuery):
    """
    Stop playback in all active voice chats (stay connected).
    """
    try:
        status = voice_manager.get_status()
        if not status['calls']:
            await callback.answer("❌ No active voice chats", show_alert=True)
            return

        stopped = 0
        for chat_id, call in status['calls'].items():
            try:
                ptg = call.get("pytgcalls")
                if ptg and hasattr(ptg, "stop_playout"):
                    await ptg.stop_playout(int(chat_id))
                elif ptg and hasattr(ptg, "pause"):
                    await ptg.pause(int(chat_id))
                state = voice_manager.playback_state.setdefault(str(chat_id), {})
                state.update({"is_playing": False, "start_time": 0})
                call["playing"] = False
                stopped += 1
            except Exception as e:
                logger.error(f"❌ Failed to stop in {chat_id}: {e}")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="▶️ Resume All", callback_data="resume_all"),
                InlineKeyboardButton(text="⏸️ Pause All", callback_data="pause_all")
            ],
            [InlineKeyboardButton(text="🔙 Back to Voice Chat", callback_data="voice_chat")]
        ])
        await callback.message.edit_text(
            f"⏹️ **Stopped playback** in {stopped} chat(s).",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Error in stop_all: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data.startswith("pause_chat:"))
async def callback_pause_chat(callback: CallbackQuery):
    """Pause specific chat"""
    try:
        chat_id = callback.data.split(":", 1)[1]
        success = await voice_manager.pause_media(chat_id)
        
        if success:
            await callback.answer("⏸️ Paused successfully", show_alert=False)
        else:
            await callback.answer("❌ Failed to pause", show_alert=True)
            
        # Refresh the pause/resume menu
        await callback_pause_resume(callback)
        
    except Exception as e:
        logger.error(f"❌ Error pausing chat: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data.startswith("resume_chat:"))
async def callback_resume_chat(callback: CallbackQuery):
    """Resume specific chat"""
    try:
        chat_id = callback.data.split(":", 1)[1]
        success = await voice_manager.resume_media(chat_id)
        if success:
            await callback.answer("▶️ Resumed successfully", show_alert=False)
            # Optionally, update the message to show resumed status
            await callback.message.edit_text(
                f"▶️ Playback resumed in chat {chat_id}.",
                parse_mode="Markdown"
            )
        else:
            await callback.answer("❌ Failed to resume", show_alert=True)
            await callback.message.edit_text(
                f"❌ Failed to resume playback in chat {chat_id}.",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"❌ Error resuming chat: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "pause_all")
async def callback_pause_all(callback: CallbackQuery):
    """Pause all voice chats"""
    try:
        status = voice_manager.get_status()
        paused_count = 0
        for chat_id in status['calls'].keys():
            try:
                success = await voice_manager.pause_media(chat_id)
                if success:
                    paused_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to pause {chat_id}: {e}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="▶️ Resume All", callback_data="resume_all"),
                InlineKeyboardButton(text="⏹️ Stop All", callback_data="stop_all")
            ],
            [InlineKeyboardButton(text="🔙 Back to Voice Chat", callback_data="voice_chat")]
        ])
        
        await callback.message.edit_text(
            f"⏸️ **Pause Operation Complete**\n\n"
            f"✅ **Successfully paused:** {paused_count} voice chats\n"
            f"🎤 **Active calls:** {len(status['calls'])}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"❌ Error pausing all: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "resume_all")
async def callback_resume_all(callback: CallbackQuery):
    """Resume all voice chats"""
    try:
        status = voice_manager.get_status()
        resumed_count = 0
        for chat_id in status['calls'].keys():
            try:
                success = await voice_manager.resume_media(chat_id)
                if success:
                    resumed_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to resume {chat_id}: {e}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⏸️ Pause All", callback_data="pause_all"),
                InlineKeyboardButton(text="⏹️ Stop All", callback_data="stop_all")
            ],
            [InlineKeyboardButton(text="🔙 Back to Voice Chat", callback_data="voice_chat")]
        ])
        
        await callback.message.edit_text(
            f"▶️ **Resume Operation Complete**\n\n"
            f"✅ **Successfully resumed:** {resumed_count} voice chats\n"
            f"🎤 **Active calls:** {len(status['calls'])}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"❌ Error resuming all: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "volume_control")
async def callback_volume_control(callback: CallbackQuery):
    """Volume control handler"""
    try:
        status = voice_manager.get_status()
        
        if not status['calls']:
            await callback.answer("❌ No active voice chats", show_alert=True)
            return
        
        # Enhanced volume control with pydub processing (up to 300%)
        percent_steps = [25, 50, 75, 100, 125, 150, 175, 200, 250, 300, 400, 500, 600]
        volume_buttons = [InlineKeyboardButton(text=f"{v}%", callback_data=f"set_volume:{v}") for v in percent_steps]
        volume_rows = [volume_buttons[i:i+3] for i in range(0, len(volume_buttons), 3)]
        buttons = volume_rows + [
            [InlineKeyboardButton(text="🔙 Back to Voice Chat", callback_data="voice_chat")],
            [InlineKeyboardButton(text="📊 Voice Status", callback_data="voice_status")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(
            f"🔊 **Enhanced Volume Control**\n\n"
            f"🎤 **Active Calls:** {len(status['calls'])}\n\n"
            f"🚀 **NEW: Up to 600% volume with Pydub enhancement!**\n"
            f"🎵 **Crystal clear sound even at maximum volume**\n\n"
            f"Select a volume percentage (25% to 600%):\n\n"
            f"• 100% = Normal volume\n"
            f"• 150% = Loud boost\n"
            f"• 200% = Very loud\n"
            f"• 250-600% = Maximum power 🚀\n\n"
            f"✨ **Features:** Noise reduction, EQ enhancement, peak limiting",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Error in volume control: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)


@dp.callback_query(F.data == "status")
async def callback_status(callback: CallbackQuery):
    """Show overall bot status (accounts + calls + queues)"""
    try:
        status = voice_manager.get_status()
        accounts_count = len(user_clients)
        active_calls = status.get("active_calls", 0)
        total_queued = status.get("total_queued", 0)
        perf = status.get("performance_stats", {})

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Voice Status (per chat)", callback_data="voice_status")],
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="status")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="main")]
        ])

        await callback.message.edit_text(
            f"📊 **Bot Status**\n\n"
            f"📱 **Accounts:** {accounts_count}\n"
            f"🎤 **Active Calls:** {active_calls}\n"
            f"📋 **Queued Items:** {total_queued}\n\n"
            f"**Performance:**\n"
            f"📈 Total joins: {perf.get('total_joins', 0)}\n"
            f"✅ Successful joins: {perf.get('successful_joins', 0)}\n"
            f"🎵 Media played: {perf.get('total_media_played', 0)}\n"
            f"❌ Connection errors: {perf.get('connection_errors', 0)}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Error in status: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

# Account management handlers
@dp.callback_query(F.data == "accounts")
async def callback_accounts(callback: CallbackQuery):
    """Show accounts menu"""
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Add Account", callback_data="add_account")],
            [InlineKeyboardButton(text="📋 List Accounts", callback_data="list_accounts")],
            [InlineKeyboardButton(text="🗑️ Remove Account", callback_data="remove_account")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="main")]
        ])
        
        await callback.message.edit_text(
            f"👥 **Account Management**\n\n"
            f"📱 **Active Accounts:** {len(user_clients)}\n"
            f"🔐 **Max Accounts:** {MAX_ACCOUNTS}\n\n"
            f"Select an option:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Error in accounts menu: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "add_account")
async def callback_add_account(callback: CallbackQuery, state: FSMContext):
    """Add account handler"""
    try:
        if len(user_clients) >= MAX_ACCOUNTS:
            await callback.answer(f"❌ Maximum accounts ({MAX_ACCOUNTS}) reached", show_alert=True)
            return
            
        await callback.message.edit_text(
            f"➕ **Add New Account**\n\n"
            f"📱 **Step 1:** Enter phone number\n\n"
            f"📝 Format: +1234567890 (with country code)\n"
            f"⚠️ Make sure the number is correct!\n\n"
            f"📱 **Please send your phone number:**",
            parse_mode="Markdown"
        )
        
        await state.set_state(AccountStates.phone)
        
    except Exception as e:
        logger.error(f"❌ Error in add account: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.message(AccountStates.phone)
async def handle_account_phone(message: Message, state: FSMContext):
    """Handle phone number input for adding account, send OTP code request"""
    try:
        phone = message.text.strip()
        if not re.match(r'^\+\d{10,15}$', phone):
            await message.reply("❌ Invalid phone number format. Please use the format: +1234567890")
            return
        await state.update_data(phone=phone)
        try:
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            sent = await client.send_code_request(phone)
            # Save client for OTP step
            user_clients[phone] = (client, None)
            # Add back button to OTP prompt
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back", callback_data="accounts")]
            ])
            await message.reply(
                f"📱 **Phone number received:** {phone}\n\n"
                f"📩 OTP has been sent! Please check your Telegram app or SMS and enter it here.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await state.set_state(AccountStates.otp)
        except Exception as e:
            await message.reply(f"❌ Failed to send OTP: {e}")
            await state.clear()
    except Exception as e:
        logger.error(f"❌ Error handling phone input: {e}")
        await message.reply("❌ An error occurred. Please try again.")

@dp.message(AccountStates.otp)
async def handle_account_otp(message: Message, state: FSMContext):
    """Handle OTP input for adding account"""
    try:
        data = await state.get_data()
        phone = data.get("phone")
        otp = message.text.strip()
        await message.reply("🔄 Logging in, please wait...")

        # Use client saved in previous step
        client, _ = user_clients.get(phone, (None, None))
        if not client:
            await message.reply("❌ No client session found. Please start again.")
            await state.clear()
            return
        try:
            await client.sign_in(phone, otp)
        except SessionPasswordNeededError:
            # Add back button to password prompt
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back", callback_data="accounts")]
            ])
            await message.reply("🔐 2FA enabled. Please send your password.", reply_markup=keyboard)
            await state.set_state(AccountStates.password)
            await state.update_data(client=client)
            return
        except (PhoneCodeInvalidError, PhoneNumberInvalidError) as e:
            await message.reply(f"❌ Invalid OTP or phone number: {e}")
            await state.set_state(AccountStates.phone)
            return
        except FloodWaitError as e:
            await message.reply(f"⏳ Too many attempts. Wait {e.seconds} seconds and try again.")
            await state.clear()
            return

        session_string = client.session.save()
        user_clients[phone] = (client, session_string)
        await save_users()
        await message.reply(f"✅ Account +{phone[-4:]} added successfully!")
        await state.clear()
    except Exception as e:
        logger.error(f"❌ Error handling OTP: {e}")
        await message.reply("❌ Error logging in. Try again.")
        await state.clear()

@dp.message(AccountStates.password)
async def handle_account_password(message: Message, state: FSMContext):
    """Handle password input for 2FA accounts"""
    try:
        data = await state.get_data()
        phone = data.get("phone")
        client = data.get("client")
        password = message.text.strip()
        try:
            await client.sign_in(password=password)
            session_string = client.session.save()
            user_clients[phone] = (client, session_string)
            await save_users()
            await message.reply(f"✅ Account +{phone[-4:]} added successfully!")
        except PasswordHashInvalidError:
            # Add back button to password retry
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back", callback_data="accounts")]
            ])
            await message.reply("❌ Invalid password. Try again.", reply_markup=keyboard)
            return
        await state.clear()
    except Exception as e:
        logger.error(f"❌ Error handling password: {e}")
        await message.reply("❌ Error logging in. Try again.")
        await state.clear()

@dp.callback_query(F.data == "list_accounts")
async def callback_list_accounts(callback: CallbackQuery):
    """List all accounts"""
    try:
        if not user_clients:
            await callback.message.edit_text("❌ No accounts available.", parse_mode="Markdown")
            return
        msg = "📱 **Accounts:**\n\n"
        for phone in user_clients:
            msg += f"• {phone}\n"  # Show full phone number
        await callback.message.edit_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Error listing accounts: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data == "remove_account")
async def callback_remove_account_menu(callback: CallbackQuery):
    """Show remove account menu"""
    try:
        buttons = []
        for phone in user_clients:
            buttons.append([InlineKeyboardButton(
                text=f"🗑️ Remove {phone}",  # Show full phone number
                callback_data=f"remove_account:{phone}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="accounts")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(
            "🗑️ **Remove Account**\n\nSelect an account to remove:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Error in remove account menu: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data.startswith("remove_account:"))
async def callback_remove_account_confirm(callback: CallbackQuery):
    """Remove selected account"""
    try:
        phone = callback.data.split(":", 1)[1]
        if phone in user_clients:
            client, _ = user_clients.pop(phone)
            await client.disconnect()
            await save_users()
            await callback.message.edit_text(f"✅ Removed account {phone}", parse_mode="Markdown")  # Show full phone number
        else:
            await callback.message.edit_text("❌ Account not found.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Error removing account: {e}")
        await callback.answer("❌ An error occurred", show_alert=True)

@dp.callback_query(F.data.startswith("set_volume:"))
async def callback_set_volume(callback: CallbackQuery, state: FSMContext):
    """Set volume using ffmpeg-based approach"""
    try:
        percent = int(callback.data.split(":", 1)[1])
        if percent < 25 or percent > 600:
            await callback.answer("❌ Volume must be between 25% and 600%.", show_alert=True)
            return

        status = voice_manager.get_status()
        if not status['calls']:
            await callback.answer("❌ No active voice chats.", show_alert=True)
            return

        changed = 0
        for chat_id, call_info in status['calls'].items():
            try:
                success = await voice_manager.set_volume(int(chat_id), percent)
                if success:
                    changed += 1
                    call_info["volume"] = percent
            except Exception as e:
                logger.error(f"❌ Failed to change volume in {chat_id}: {e}")

        if changed:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Volume Control", callback_data="volume_control")],
                [InlineKeyboardButton(text="🎤 Voice Chat Menu", callback_data="voice_chat")]
            ])
            await callback.message.edit_text(
                f"🔊 Volume set to {percent}% in {changed} active voice chat(s).",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Try Again", callback_data="volume_control")],
                [InlineKeyboardButton(text="🎤 Voice Chat Menu", callback_data="voice_chat")]
            ])
            await callback.message.edit_text(
                "❌ Failed to change volume. Make sure audio is playing.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"❌ Error in set_volume handler: {e}")
        await callback.message.edit_text("❌ Error changing volume.", parse_mode="Markdown")

@dp.callback_query(F.data == "main")
async def callback_main(callback: CallbackQuery):
    """Show the main menu when Back is pressed"""
    try:
        if not is_owner(callback.from_user.id):
            await callback.answer("❌ Access denied. This bot is private.", show_alert=True)
            return

        status = voice_manager.get_status()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎤 Voice Chat", callback_data="voice_chat")],
            [InlineKeyboardButton(text="👥 Accounts", callback_data="accounts")],
            [InlineKeyboardButton(text="📊 Status", callback_data="status")]
        ])

        await callback.message.edit_text(
            f"🎵 **Modern Voice Chat Bot**\n\n"
            f"📱 **Accounts:** {len(user_clients)}\n"
            f"🎤 **Active Calls:** {status['active_calls']}\n"
            f"📋 **Queued Items:** {status['total_queued']}\n\n"
            f"Select an option:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Error showing main menu: {e}")
        await callback.answer("❌ Error showing main menu", show_alert=True)

if __name__ == "__main__":
    import asyncio
    from aiohttp import web
    from aiohttp.web_runner import GracefulExit

    async def main():
        """Main function to start the bot"""
        await load_users()
        logger.info("🤖 Bot is starting...")
        
        # Check if running on Heroku (has PORT environment variable)
        port = os.getenv('PORT')
        
        if port:
            # Heroku deployment - use webhook mode
            logger.info("🌐 Starting in webhook mode for Heroku...")
            
            # Create aiohttp app for webhook
            app = web.Application()
            
            # Add a simple health check endpoint
            async def health_check(request):
                return web.Response(text="Bot is running!", status=200)
            
            app.router.add_get('/', health_check)
            app.router.add_get('/health', health_check)
            
            # Start the bot in polling mode alongside the web server
            async def start_bot():
                try:
                    await dp.start_polling(bot, skip_updates=True)
                except Exception as e:
                    logger.error(f"❌ Bot polling error: {e}")
            
            # Run both the web server and bot concurrently
            bot_task = asyncio.create_task(start_bot())
            
            # Start web server
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', int(port))
            await site.start()
            
            logger.info(f"🌐 Web server started on port {port}")
            logger.info("🤖 Bot started in polling mode")
            
            # Keep both running
            try:
                await bot_task
            except (KeyboardInterrupt, SystemExit, GracefulExit):
                logger.info("🛑 Bot stopping...")
                await runner.cleanup()
        else:
            # Local development - use polling only
            logger.info("🖥️ Starting in polling mode for local development...")
            await dp.start_polling(bot, skip_updates=True)

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot stopped.")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        logger.error(traceback.format_exc())
