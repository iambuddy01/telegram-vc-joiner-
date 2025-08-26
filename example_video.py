import os
import time

from ntgcalls import MediaSource
from pyrogram import Client

from pytgcalls import idle
from pytgcalls import PyTgCalls
from pytgcalls.types.raw import AudioParameters
from pytgcalls.types.raw import AudioStream
from pytgcalls.types.raw import Stream
from pytgcalls.types.raw import VideoParameters
from pytgcalls.types.raw import VideoStream

app = Client(
    'py-tgcalls',
    api_id=123456789,
    api_hash='abcdef12345',
)

call_py = PyTgCalls(app)
call_py.start()
audio_file = os.path.join(os.getcwd(), 'audio.raw')
video_file = os.path.join(os.getcwd(), 'video.raw')
while not os.path.exists(audio_file) or \
        not os.path.exists(video_file):
    time.sleep(0.125)
call_py.play(
    -1001234567890,
    Stream(
        AudioStream(
            MediaSource.FILE,
            audio_file,
            AudioParameters(
                bitrate=48000,
            ),
        ),
        camera=VideoStream(
            MediaSource.FILE,
            video_file,
            VideoParameters(
                width=1280,
                height=720,
                frame_rate=30,
            ),
        ),
    ),
)
idle()
