import os
import sys
import uuid
import math
import time
import random
import asyncio
import subprocess
from pathlib import Path

import requests
from gtts import gTTS
from pydub import AudioSegment

# ---------------- FFMPEG (Windows path – adjust if needed) ----------------
FFMPEG_PATH = r"C:\Users\91830\Desktop\Narration Project\ffmpeg\bin\ffmpeg.exe"
if not os.path.isfile(FFMPEG_PATH):
    raise FileNotFoundError(f"ffmpeg not found at {FFMPEG_PATH}. Please update FFMPEG_PATH.")
AudioSegment.converter = FFMPEG_PATH
os.environ["PATH"] += os.pathsep + os.path.dirname(FFMPEG_PATH)
print(" ffmpeg configured for pydub:", AudioSegment.converter)


# ---------------- Mood detection (keyword-based) ----------------
def detect_mood(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ["love", "romance", "kiss", "beloved", "heart"]):
        return "romantic"
    if any(w in t for w in ["war", "fight", "battle", "storm", "thunder", "rage"]):
        return "intense"
    if any(w in t for w in ["happy", "joy", "smile", "sun", "bright", "celebration"]):
        return "happy"
    if any(w in t for w in ["sad", "tears", "cry", "lonely", "sorrow", "melancholy"]):
        return "sad"
    if any(w in t for w in ["rain", "drizzle", "monsoon", "cloud"]):
        return "rainy"
    if any(w in t for w in ["peace", "calm", "serene", "quiet", "meditation", "zen"]):
        return "calm"
    return "calm"


# ---------------- Image prompt creation (no text in output) ----------------
def _build_image_prompt(text: str, mood: str) -> str:
    t = (text or "").lower()
    visual = []

    def add_if(words, phrase):
        if any(w in t for w in words):
            visual.append(phrase)

    add_if(["shadow", "silhouette"], "dramatic shadows and silhouettes")
    add_if(["candle", "dim"], "soft warm candlelight")
    add_if(["rose", "flower", "petal"], "rose garden with petals")
    add_if(["rain", "storm", "lightning"], "rainstorm and dramatic clouds")
    add_if(["ocean", "sea", "wave"], "ocean waves on rocky shore")
    add_if(["forest", "trees", "woods"], "enchanted forest")
    add_if(["sunset", "sunrise", "golden"], "golden sunset sky")
    add_if(["moon", "night", "stars"], "moonlit starry night")

    mood_scenes = {
        "romantic": [
            "candlelit scene with warm tones",
            "couple silhouettes at sunset",
            "rose garden at dusk",
        ],
        "intense": [
            "stormy sky over mountains",
            "crashing waves and cliffs",
            "volcanic glow and dramatic clouds",
        ],
        "happy": [
            "bright meadow with flowers",
            "balloons in a blue sky",
            "rainbow after a light rain",
        ],
        "sad": [
            "misty empty street with rain",
            "solitary figure near window",
            "faded flowers on a table",
        ],
        "rainy": [
            "umbrella on a wet city street at night",
            "raindrops on lake ripples",
            "heavy rainfall on green landscape",
        ],
        "calm": [
            "still lake with mountains",
            "zen garden with stones",
            "gentle stream in a quiet forest",
        ],
    }

    main = ", ".join(visual[:3]) if visual else random.choice(mood_scenes.get(mood, mood_scenes["calm"]))
    style = "cinematic, photorealistic, professional lighting, high detail, artistic"
    no_text = "no text, no captions, no letters"
    prompt = f"{main}, {style}, {no_text}"
    return prompt[:500]


# ---------------- Free poster generation (Pollinations) ----------------
def generate_poster(text: str, save_path: Path) -> None:
    """
    Tries Pollinations (free, no key). If it fails, create a local abstract fallback (no text).
    """
    prompt = _build_image_prompt(text, detect_mood(text))
    try:
        url = "https://image.pollinations.ai/prompt/" + requests.utils.quote(prompt)
        r = requests.get(url, timeout=60)
        if r.status_code == 200 and r.content:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(r.content)
            return
        print("⚠️ Pollinations returned non-200, using fallback.")
    except Exception as e:
        print("⚠️ Pollinations error:", e)

    # Fallback: abstract mood image (no text)
    try:
        from PIL import Image, ImageDraw
        w, h = 1000, 600
        mood = detect_mood(text)
        palettes = {
            "romantic": [(255, 182, 193), (219, 112, 147)],
            "intense": [(255, 69, 0), (139, 0, 0)],
            "happy": [(255, 215, 0), (255, 165, 0)],
            "sad": [(70, 130, 180), (72, 61, 139)],
            "rainy": [(100, 149, 237), (176, 196, 222)],
            "calm": [(144, 238, 144), (34, 139, 34)],
        }
        c1, c2 = palettes.get(mood, palettes["calm"])
        img = Image.new("RGB", (w, h), c1)
        draw = ImageDraw.Draw(img)
        for y in range(h):
            ratio = y / h
            r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        save_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(save_path, quality=90)
    except Exception as e:
        print("⚠️ Fallback poster failed:", e)


# ---------------- Background music suggestions / discovery ----------------
BG_ROOT = Path(__file__).resolve().parent.parent / "bg_music"

_MOOD_TO_FILES = {
    "happy": ["happy.mp3"],
    "sad": ["sad.mp3"],
    "romantic": ["romantic.mp3"],
    "intense": ["intense.mp3"],
    "calm": ["calm.mp3"],
    "rainy": ["rainy.mp3"],
}

def list_bg_tracks_for_mood(mood: str):
    """
    Returns list of (label, absolute_path) that actually exist.
    """
    mood = mood or "calm"
    files = _MOOD_TO_FILES.get(mood, _MOOD_TO_FILES["calm"])
    out = []
    for fname in files:
        p = BG_ROOT / fname
        if p.exists():
            out.append((fname.replace(".mp3", "").capitalize(), str(p)))
    # If none exist, return any mp3s in BG_ROOT
    if not out and BG_ROOT.exists():
        for p in BG_ROOT.glob("*.mp3"):
            out.append((p.stem.capitalize(), str(p)))
    return out


# ---------------- Edge-TTS (preferred) + gTTS fallback ----------------
EDGE_VOICES = {
    "en-US": {"Male": "en-US-GuyNeural", "Female": "en-US-JennyNeural"},
    "en-GB": {"Male": "en-GB-RyanNeural", "Female": "en-GB-SoniaNeural"},
    "en-IN": {"Male": "en-IN-PrabhatNeural", "Female": "en-IN-NeerjaNeural"},
    "en-AU": {"Male": "en-AU-WilliamNeural", "Female": "en-AU-NatashaNeural"},
}

# gTTS accents via tld
GTTS_TLD = {
    "en-US": "com",
    "en-GB": "co.uk",
    "en-IN": "co.in",
    "en-AU": "com.au",
}

def _edge_tts_available() -> bool:
    try:
        import edge_tts  # noqa
        return True
    except Exception:
        return False

async def _edge_tts_async(text: str, voice_name: str, out_file: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(out_file)

def generate_tts(text: str, engine: str, accent: str, gender: str, out_file: Path):
    """
    Generate narration mp3 at out_file.
    engine: "edge" or "gtts"
    accent: en-US/en-GB/en-IN/en-AU
    gender: Male/Female (Edge only meaningfully changes; gTTS stays same voice)
    """
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if engine == "edge" and _edge_tts_available():
        try:
            voice = EDGE_VOICES.get(accent, EDGE_VOICES["en-US"]).get(gender, "en-US-JennyNeural")
            asyncio.run(_edge_tts_async(text, voice, str(out_file)))
            return True
        except Exception as e:
            print(" Edge-TTS failed, falling back to gTTS:", e)

    # gTTS fallback
    try:
        tld = GTTS_TLD.get(accent, "com")
        slow = (gender == "Male")  # mild timbre difference
        tts = gTTS(text=text, lang="en", tld=tld, slow=slow)
        tts.save(str(out_file))
        # Optional small pitch tweak for "Male" using pydub:
        if gender == "Male":
            audio = AudioSegment.from_file(out_file)
            audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * 0.92)}).set_frame_rate(audio.frame_rate)
            audio.export(out_file, format="mp3", bitrate="192k")
        return True
    except Exception as e:
        print(" gTTS failed:", e)
        try:
            # last resort: short silence
            AudioSegment.silent(duration=max(1000, len(text) * 60)).export(out_file, format="mp3")
            return True
        except Exception as e2:
            print(" Creating silence failed:", e2)
            return False


# ---------------- Mixing (narration + background @ ~40%) ----------------
def mix_with_background(narration_path: Path, bg_path: str | None, out_path: Path):
    """
    Mix bg beneath narration. bg at about 40% of narration loudness.
    """
    narration = AudioSegment.from_file(narration_path).normalize()
    if bg_path and os.path.exists(bg_path):
        bg = AudioSegment.from_file(bg_path)
        # loop & trim to narration length
        if len(bg) < len(narration):
            loops = (len(narration) // len(bg)) + 1
            bg = bg * loops
        bg = bg[:len(narration)]

        # Set bg relative loudness (~40% amplitude ≈ -8 dB; adjust to narration dBFS)
        # Start from narration loudness then pull bg down.
        target_bg = narration.dBFS - 8.0
        bg = bg.normalize().apply_gain(target_bg - bg.dBFS)

        mixed = bg.overlay(narration)  # narration on top
        mixed = mixed.fade_in(600).fade_out(800)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        mixed.export(out_path, format="mp3", bitrate="192k")
    else:
        # No bg – just tidy narration
        out_path.parent.mkdir(parents=True, exist_ok=True)
        narration.fade_in(300).fade_out(300).export(out_path, format="mp3", bitrate="192k")


   
