#!/usr/bin/env python3
"""
FFmpeg availability checker for Heroku deployment
"""
import os
import subprocess
import sys

def check_command(cmd):
    """Check if a command is available"""
    try:
        result = subprocess.run([cmd, '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ {cmd}: {version_line}")
            return True
        else:
            print(f"❌ {cmd}: Command failed with return code {result.returncode}")
            return False
    except FileNotFoundError:
        print(f"❌ {cmd}: Command not found")
        return False
    except Exception as e:
        print(f"❌ {cmd}: Error - {e}")
        return False

def find_ffmpeg_tools():
    """Find FFmpeg tools in common locations"""
    common_paths = [
        '/usr/bin/',
        '/usr/local/bin/',
        '/app/.apt/usr/bin/',
        '/app/.heroku/',
    ]
    
    tools = ['ffmpeg', 'ffprobe']
    found_tools = {}
    
    for tool in tools:
        found = False
        # Check in PATH first
        if check_command(tool):
            found_tools[tool] = tool
            found = True
        else:
            # Check common paths
            for path in common_paths:
                full_path = os.path.join(path, tool)
                if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                    print(f"✅ Found {tool} at: {full_path}")
                    found_tools[tool] = full_path
                    found = True
                    break
            
            if not found:
                print(f"❌ {tool}: Not found in any common location")
    
    return found_tools

def main():
    print("🔍 Checking FFmpeg installation on Heroku...")
    print("=" * 50)
    
    # Check environment
    print(f"Platform: {sys.platform}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"PATH: {os.environ.get('PATH', 'Not set')}")
    print()
    
    # List /usr/bin/ contents
    if os.path.exists('/usr/bin/'):
        print("📂 Contents of /usr/bin/ (related to ffmpeg):")
        try:
            contents = os.listdir('/usr/bin/')
            ffmpeg_related = [f for f in contents if 'ffmpeg' in f.lower() or 'ffprobe' in f.lower()]
            if ffmpeg_related:
                for item in ffmpeg_related:
                    print(f"  - {item}")
            else:
                print("  No FFmpeg-related files found")
        except Exception as e:
            print(f"  Error reading directory: {e}")
        print()
    
    # Check apt directory
    apt_dir = '/app/.apt/usr/bin/'
    if os.path.exists(apt_dir):
        print(f"📂 Contents of {apt_dir} (related to ffmpeg):")
        try:
            contents = os.listdir(apt_dir)
            ffmpeg_related = [f for f in contents if 'ffmpeg' in f.lower() or 'ffprobe' in f.lower()]
            if ffmpeg_related:
                for item in ffmpeg_related:
                    print(f"  - {item}")
            else:
                print("  No FFmpeg-related files found")
        except Exception as e:
            print(f"  Error reading directory: {e}")
        print()
    
    # Find tools
    found_tools = find_ffmpeg_tools()
    
    print()
    print("📋 Summary:")
    print("=" * 30)
    if found_tools:
        for tool, path in found_tools.items():
            print(f"{tool}: {path}")
    else:
        print("❌ No FFmpeg tools found!")
    
    # Test PyTgCalls import
    print()
    print("🧪 Testing PyTgCalls import...")
    try:
        from pytgcalls import PyTgCalls
        print("✅ PyTgCalls imported successfully")
    except Exception as e:
        print(f"❌ PyTgCalls import failed: {e}")

if __name__ == "__main__":
    main()
