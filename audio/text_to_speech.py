"""High-speed pipelined J.A.R.V.I.S. speech synthesis using Edge-TTS with sentence prefetching,
instant audio caching, and offline fallbacks."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import os
from pathlib import Path
from queue import Empty, Queue
import re
import threading
from threading import Event, Lock
import time

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    import sounddevice as sd
    import soundfile as sf
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

_PLAYBACK_LOCK = Lock()
_PLAYBACK_STATE_LOCK = Lock()
_PLAYBACK_GENERATION = 0

DEFAULT_VOICE = os.getenv("JARVIS_VOICE", "en-GB-RyanNeural")
VOICE_RATE = os.getenv("JARVIS_VOICE_RATE", "+3%")
VOICE_PITCH = os.getenv("JARVIS_VOICE_PITCH", "+0Hz")

LOCAL_MODEL_NAME = "vits-piper-en_US-lessac-medium"
LOCAL_MODEL_DIR = Path(os.getenv("APOORVA_TTS_MODEL_DIR", f"models/audio/{LOCAL_MODEL_NAME}"))
LOCAL_MODEL = LOCAL_MODEL_DIR / "en_US-lessac-medium.onnx"
LOCAL_TOKENS = LOCAL_MODEL_DIR / "tokens.txt"
LOCAL_ESPEAK_DATA = LOCAL_MODEL_DIR / "espeak-ng-data"

# In-memory LRU cache for instant 0ms playback of common phrases
_AUDIO_CACHE: dict[str, bytes] = {}
_CACHE_LOCK = Lock()

# Pre-fetch executor for sentence pipelining
_SYNTHESIS_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="jarvis-tts-synth")


def local_piper_available() -> bool:
    return LOCAL_MODEL.is_file() and LOCAL_TOKENS.is_file() and LOCAL_ESPEAK_DATA.is_dir()


def available() -> bool:
    return HAS_EDGE_TTS or local_piper_available()


def _get_local_piper():
    import sherpa_onnx
    config = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=str(LOCAL_MODEL), tokens=str(LOCAL_TOKENS), data_dir=str(LOCAL_ESPEAK_DATA),
            ),
            provider="cpu",
            num_threads=max(1, min(4, int(os.getenv("APOORVA_AUDIO_THREADS", "2")))),
        ),
        max_num_sentences=1,
    )
    return sherpa_onnx.OfflineTts(config)


def speech_friendly(text: str) -> str:
    """Convert Markdown into clean spoken text."""
    text = re.sub(r"```.*?```", " [code displayed on terminal] ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\((?:[^()]|\([^()]*\))*\)", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = re.sub(r"(?m)^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", text)
    text = re.sub(r"[*_~]{1,3}", "", text)
    text = re.sub(r"\(\s*\)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stop() -> None:
    """Stop current speech playback immediately and increment generation to discard pending audio."""
    global _PLAYBACK_GENERATION
    with _PLAYBACK_STATE_LOCK:
        _PLAYBACK_GENERATION += 1
    if HAS_SOUNDDEVICE:
        try:
            sd.stop()
        except Exception:
            pass


async def _synthesize_edge_async(text: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice=DEFAULT_VOICE, rate=VOICE_RATE, pitch=VOICE_PITCH)
    mp3_buffer = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_buffer.extend(chunk["data"])
    return bytes(mp3_buffer)


def _synthesize_sentence(sentence: str) -> bytes | None:
    """Synthesize a single sentence into audio bytes with memory cache."""
    clean = sentence.strip()
    if not clean:
        return None

    with _CACHE_LOCK:
        if clean in _AUDIO_CACHE:
            return _AUDIO_CACHE[clean]

    if HAS_EDGE_TTS:
        try:
            loop = asyncio.new_event_loop()
            data = loop.run_until_complete(_synthesize_edge_async(clean))
            loop.close()
            if data:
                with _CACHE_LOCK:
                    if len(_AUDIO_CACHE) < 100:
                        _AUDIO_CACHE[clean] = data
                return data
        except Exception:
            pass

    if local_piper_available():
        try:
            import sherpa_onnx
            tts = _get_local_piper()
            gen_cfg = sherpa_onnx.GenerationConfig()
            gen_cfg.sid = 0
            gen_cfg.speed = 1.05
            audio = tts.generate(clean, gen_cfg)
            if len(audio.samples) > 0:
                buf = io.BytesIO()
                sf.write(buf, audio.samples, audio.sample_rate, format="WAV")
                return buf.getvalue()
        except Exception:
            pass

    return None


def _play_single_audio_bytes(audio_bytes: bytes, generation: int, enabled: Event | None = None) -> bool:
    """Play raw audio bytes if generation matches current."""
    if not audio_bytes or not HAS_SOUNDDEVICE:
        return False
    with _PLAYBACK_STATE_LOCK:
        if generation != _PLAYBACK_GENERATION or (enabled is not None and not enabled.is_set()):
            return False

    try:
        data, sample_rate = sf.read(io.BytesIO(audio_bytes))
        with _PLAYBACK_STATE_LOCK:
            if generation != _PLAYBACK_GENERATION or (enabled is not None and not enabled.is_set()):
                return False
        sd.play(data, sample_rate, blocking=True)
        return True
    except Exception:
        return False


def speak(text: str, enabled: Event | None = None) -> None:
    """
    Pipelined speech synthesis:
    Breaks response into sentences.
    Starts playing Sentence 1 as soon as it is synthesized,
    while pre-synthesizing Sentence 2 concurrently in the background.
    """
    with _PLAYBACK_STATE_LOCK:
        current_gen = _PLAYBACK_GENERATION

    text = speech_friendly(text)[:4000]
    if not text:
        return

    # Split into sentences for pipelining
    raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not raw_sentences:
        return

    # If answer is very long, cap verbal output to first 2-3 sentences
    if len(raw_sentences) > 3 and len(text) > 300:
        sentences = raw_sentences[:2] + ["I have displayed the detailed telemetry on your terminal, sir."]
    else:
        sentences = raw_sentences

    with _PLAYBACK_LOCK:
        with _PLAYBACK_STATE_LOCK:
            if current_gen != _PLAYBACK_GENERATION or (enabled is not None and not enabled.is_set()):
                return

        # Single sentence optimization
        if len(sentences) == 1:
            data = _synthesize_sentence(sentences[0])
            if data:
                _play_single_audio_bytes(data, current_gen, enabled)
            return

        # Pipelined multi-sentence execution
        # Submit first sentence immediately
        first_future = _SYNTHESIS_EXECUTOR.submit(_synthesize_sentence, sentences[0])

        for i, sentence in enumerate(sentences):
            with _PLAYBACK_STATE_LOCK:
                if current_gen != _PLAYBACK_GENERATION or (enabled is not None and not enabled.is_set()):
                    return

            # Submit next sentence in background while waiting for current
            if i + 1 < len(sentences):
                next_future = _SYNTHESIS_EXECUTOR.submit(_synthesize_sentence, sentences[i + 1])
            else:
                next_future = None

            # Await current sentence audio
            current_future = first_future if i == 0 else active_future
            try:
                audio_data = current_future.result(timeout=10.0)
            except Exception:
                audio_data = None

            if audio_data:
                _play_single_audio_bytes(audio_data, current_gen, enabled)

            first_future = None
            active_future = next_future


# Warm up cache in background for standard J.A.R.V.I.S. phrases
def warm_cache():
    def _warm():
        common_phrases = [
            "At your service, sir.",
            "Right away, sir.",
            "All systems online, sir. At your service.",
            "Working on it, sir…",
            "Vocalization muted, sir.",
            "Voice output enabled, sir.",
        ]
        for p in common_phrases:
            _synthesize_sentence(p)
    threading.Thread(target=_warm, daemon=True, name="jarvis-tts-warmup").start()


warm_cache()
