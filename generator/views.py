
import os
import uuid
import io
import asyncio
from django.shortcuts import render
from django.conf import settings
from pydub import AudioSegment
import edge_tts
from dotenv import load_dotenv
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from PIL import Image

# Load environment variables
load_dotenv()
STABILITY_KEY = os.getenv("STABILITY_KEY")


os.environ["PATH"] += os.pathsep + r"C:\Users\91830\Desktop\Narration Project\ffmpeg\bin"
os.environ["FFMPEG_BINARY"] = r"C:\Users\91830\Desktop\Narration Project\ffmpeg\bin\ffmpeg.exe"
os.environ["FFPROBE_BINARY"] = r"C:\Users\91830\Desktop\Narration Project\ffmpeg\bin\ffprobe.exe"

AudioSegment.converter = r"C:\Users\91830\Desktop\Narration Project\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffmpeg = r"C:\Users\91830\Desktop\Narration Project\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\Users\91830\Desktop\Narration Project\ffmpeg\bin\ffprobe.exe"


MOOD_MUSIC = {
    "happy": ["static/music/happy1.mp3", "static/music/happy2.mp3"],
    "sad": ["static/music/sad1.mp3", "static/music/sad2.mp3"],
    "excited": ["static/music/excited1.mp3"],
    "sombre": ["static/music/sombre1.mp3"]
}

VOICES = [
    {"name": "en-GB-SoniaNeural", "label": "British Female"},
    {"name": "en-GB-RyanNeural", "label": "British Male"},
    {"name": "en-US-JennyNeural", "label": "US Female"},
    {"name": "en-US-GuyNeural", "label": "US Male"},
    {"name": "en-AU-NatashaNeural", "label": "Australian Female"},
    {"name": "en-AU-WilliamNeural", "label": "Australian Male"},
]


async def generate_tts(text, voice, filename):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)


def index(request):
    audio_url = None
    image_url = None
    music_options = []
    poster_text = ""

    if request.method == "POST":
        text = request.POST.get("text")
        voice = request.POST.get("voice")
        mood = request.POST.get("mood")
        bg_music = request.POST.get("bg_music")

        poster_text = text

      
        filename = f"static/audio_{uuid.uuid4().hex}.mp3"
        asyncio.run(generate_tts(text, voice, filename))
        narration = AudioSegment.from_file(filename, format="mp3")

       
        if bg_music:
            bg = AudioSegment.from_file(bg_music, format="mp3")
            bg = bg - 20  # reduce volume (-20dB ~ 40%)
            final_audio = narration.overlay(bg)
            final_name = f"static/final_{uuid.uuid4().hex}.mp3"
            final_audio.export(final_name, format="mp3")
            audio_url = "/" + final_name
        else:
            audio_url = "/" + filename

        
        if mood in MOOD_MUSIC:
            music_options = MOOD_MUSIC[mood]

        # --- Generate Image from Stability AI ---
        image_name = None
        try:
            stability_api = client.StabilityInference(
                key=STABILITY_KEY,
                verbose=True,
            )

            answers = stability_api.generate(
                prompt=text,
                seed=123,
                steps=30,
                width=512,
                height=512,
                cfg_scale=8.0,
                samples=1,
                sampler=generation.SAMPLER_K_DPMPP_2M
            )

            for resp in answers:
                for artifact in resp.artifacts:
                    if artifact.type == generation.ARTIFACT_IMAGE:
                        img = Image.open(io.BytesIO(artifact.binary))
                        image_name = f"static/img_{uuid.uuid4().hex}.png"
                        img.save(image_name)

            if image_name:
                image_url = "/" + image_name
        except Exception as e:
            print("Image generation failed:", e)
            image_url = None

    return render(request, "generator/index.html", {
        "voices": VOICES,
        "moods": list(MOOD_MUSIC.keys()),
        "music_options": music_options,
        "audio_url": audio_url,
        "poster_text": poster_text,
        "image_url": image_url,
    })


