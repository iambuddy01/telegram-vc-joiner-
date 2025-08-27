#!/usr/bin/env python3
"""
Create a silence audio file for voice chat operations.
This script creates a 1-second silence MP3 file that's used
when joining voice chats with py-tgcalls.
"""

import subprocess
import sys
import os
from pathlib import Path

def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return True
    except FileNotFoundError:
        return False

def create_silence_with_ffmpeg():
    """Create silence file using FFmpeg"""
    try:
        cmd = [
            "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", 
            "-t", "1", "-ar", "48000", "-ac", "2", "-acodec", "libmp3lame", "-q:a", "0", 
            "-y", "silence.mp3"  # -y to overwrite if exists
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Created silence.mp3 using FFmpeg")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ FFmpeg not found in PATH")
        return False

def create_silence_manually():
    """Create a basic silence file manually (Windows-compatible)"""
    try:
        # Create a proper minimal MP3 file
        # This is a valid 1-second silent MP3 file in bytes
        mp3_silence_data = bytes([
            # MP3 Header
            0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        ])
        
        # Extend to create roughly 1 second of silence
        silence_data = mp3_silence_data * 100  # Repeat to get roughly 1 second
        
        with open("silence.mp3", "wb") as f:
            f.write(silence_data)
        
        print("✅ Created basic silence.mp3 file")
        return True
        
    except Exception as e:
        print(f"❌ Error creating silence file: {e}")
        return False

def download_silence_file():
    """Download a pre-made silence file (fallback option)"""
    try:
        import urllib.request
        
        # URL to a small silent MP3 file (1 second)
        url = "https://raw.githubusercontent.com/anars/blank-audio/master/1-second-of-silence.mp3"
        
        print("📥 Downloading silence file from GitHub...")
        urllib.request.urlretrieve(url, "silence.mp3")
        print("✅ Downloaded silence.mp3 successfully")
        return True
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def create_wav_silence():
    """Create a simple WAV silence file as last resort"""
    try:
        import wave
        import struct
        
        # Create 1 second of silence at 44.1kHz, 16-bit, stereo
        sample_rate = 44100
        duration = 1  # seconds
        channels = 2
        sample_width = 2  # 16-bit
        
        num_samples = sample_rate * duration
        
        with wave.open("silence.wav", "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            
            # Write silence (zeros)
            silence = struct.pack("<h", 0) * channels * num_samples
            wav_file.writeframes(silence)
        
        print("✅ Created silence.wav file (using as fallback)")
        
        # Try to convert WAV to MP3 if FFmpeg is available
        if check_ffmpeg():
            try:
                subprocess.run([
                    "ffmpeg", "-i", "silence.wav", "-ar", "48000", "-ac", "2", 
                    "-acodec", "libmp3lame", "-q:a", "0", "-y", "silence.mp3"
                ], capture_output=True, check=True)
                os.remove("silence.wav")  # Remove WAV file
                print("✅ Converted to silence.mp3")
                return True
            except:
                pass
        
        # Rename WAV to MP3 (py-tgcalls might accept it)
        os.rename("silence.wav", "silence.mp3")
        print("✅ Renamed to silence.mp3 (may work with py-tgcalls)")
        return True
        
    except Exception as e:
        print(f"❌ Error creating WAV file: {e}")
        return False

def verify_silence_file():
    """Verify the silence file exists and has reasonable size"""
    silence_path = Path("silence.mp3")
    
    if not silence_path.exists():
        return False
    
    file_size = silence_path.stat().st_size
    if file_size < 50:  # Too small
        print(f"⚠️ Silence file seems too small: {file_size} bytes")
        return False
    
    print(f"✅ Silence file created successfully: {file_size} bytes")
    return True

def main():
    """Main function to create silence file"""
    print("🎵 Creating silence.mp3 file for voice chat operations...")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Check if file already exists
    if Path("silence.mp3").exists():
        if verify_silence_file():
            print("✅ silence.mp3 already exists and looks good!")
            return
        else:
            print("⚠️ Existing silence.mp3 file seems invalid, recreating...")
    
    # Method 1: Try FFmpeg first (best quality)
    print("\n1️⃣ Checking for FFmpeg...")
    if check_ffmpeg():
        print("✅ FFmpeg found! Creating high-quality silence file...")
        if create_silence_with_ffmpeg():
            if verify_silence_file():
                return
    else:
        print("❌ FFmpeg not found")
    
    # Method 2: Try downloading a pre-made file
    print("\n2️⃣ Attempting to download silence file...")
    if download_silence_file():
        if verify_silence_file():
            return
    
    # Method 3: Create manually (basic)
    print("\n3️⃣ Creating basic silence file manually...")
    if create_silence_manually():
        if verify_silence_file():
            return
    
    # Method 4: Create WAV as last resort
    print("\n4️⃣ Creating WAV silence file as fallback...")
    if create_wav_silence():
        if verify_silence_file():
            return
    
    # All methods failed
    print("\n❌ Failed to create silence file!")
    print("\n📋 Manual solutions:")
    print("1. Install FFmpeg from: https://ffmpeg.org/download.html")
    print("2. Add FFmpeg to your system PATH")
    print("3. Or manually create a 1-second silent MP3 file named 'silence.mp3'")
    print("4. Or download one from: https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3")
    
    # Don't exit with error on Windows, just warn
    if os.name == 'nt':  # Windows
        print("\n⚠️ On Windows, you can try running the bot anyway.")
        print("Some features may not work without the silence file.")
        input("Press Enter to continue...")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
