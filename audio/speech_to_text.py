"""Local, streaming, offline speech recognition and wake-word detection using sherpa-onnx."""
from functools import lru_cache
import os
from pathlib import Path
import re
import time
from typing import Callable

MODEL_NAME = "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17"
MODEL_DIR = Path(os.getenv("APOORVA_STT_MODEL_DIR", f"models/audio/{MODEL_NAME}"))


def _model_paths() -> tuple[Path, Path, Path, Path]:
    return (
        MODEL_DIR / "tokens.txt",
        MODEL_DIR / "encoder-epoch-99-avg-1.int8.onnx",
        MODEL_DIR / "decoder-epoch-99-avg-1.onnx",
        MODEL_DIR / "joiner-epoch-99-avg-1.int8.onnx",
    )


def available() -> bool:
    return all(path.is_file() for path in _model_paths())


@lru_cache(maxsize=1)
def _recognizer():
    if not available():
        raise RuntimeError("Speech model files are missing. Run: python -m audio.download_models")
    try:
        import sherpa_onnx
    except ImportError as exc:
        raise RuntimeError("Install local speech packages with: pip install -r requirements.txt") from exc
    tokens, encoder, decoder, joiner = _model_paths()
    return sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=str(tokens),
        encoder=str(encoder),
        decoder=str(decoder),
        joiner=str(joiner),
        num_threads=max(1, min(4, int(os.getenv("APOORVA_AUDIO_THREADS", "2")))),
        sample_rate=16000,
        feature_dim=80,
        decoding_method="greedy_search",
        provider="cpu",
        enable_endpoint_detection=True,
        rule1_min_trailing_silence=0.8,
        rule2_min_trailing_silence=0.35,
        rule3_min_utterance_length=20.0,
    )



def listen_once(timeout_seconds: int = 45, on_partial: Callable[[str], None] | None = None) -> str:
    """Listen locally until an utterance ends, then return its transcription."""
    if not 3 <= timeout_seconds <= 180:
        raise ValueError("timeout_seconds must be between 3 and 180")
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError("Install local audio packages with: pip install -r requirements.txt") from exc

    recognizer = _recognizer()
    stream = recognizer.create_stream()
    sample_rate = 16000
    block_size = 1600  # 100 ms
    deadline = time.monotonic() + timeout_seconds
    last_partial = ""

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", blocksize=block_size) as mic:
        while time.monotonic() < deadline:
            samples, _ = mic.read(block_size)
            stream.accept_waveform(sample_rate, samples.reshape(-1))
            while recognizer.is_ready(stream):
                recognizer.decode_stream(stream)
            partial = recognizer.get_result(stream).strip()
            if partial and partial != last_partial:
                if on_partial:
                    on_partial(partial)
                else:
                    print(f"\r[Listening] You: {partial}", end="", flush=True)
                last_partial = partial
            if recognizer.is_endpoint(stream):
                final = partial
                if on_partial is None:
                    print()
                if final:
                    return final
                stream = recognizer.create_stream()
                last_partial = ""

    if on_partial is None:
        print()
    if last_partial:
        return last_partial
    raise TimeoutError("No speech was recognized before the listening timeout")


def detect_wake_word_and_command(wake_patterns: list[str] | None = None) -> tuple[bool, str]:
    """
    Continuous wake-word listening loop.
    Returns (True, command_text) when 'Jarvis' is detected.
    If only 'Jarvis' was spoken, command_text is empty string.
    """
    try:
        import sounddevice as sd
    except ImportError:
        return False, ""

    if wake_patterns is None:
        wake_patterns = ["jarvis", "jarvis.", "hey jarvis", "hi jarvis", "ok jarvis"]

    recognizer = _recognizer()
    stream = recognizer.create_stream()
    sample_rate = 16000
    block_size = 1600

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", blocksize=block_size) as mic:
        while True:
            samples, _ = mic.read(block_size)
            stream.accept_waveform(sample_rate, samples.reshape(-1))
            while recognizer.is_ready(stream):
                recognizer.decode_stream(stream)

            text = recognizer.get_result(stream).strip().lower()
            if text:
                # Check for wake word in text
                for wake in wake_patterns:
                    if wake in text:
                        # Extract the command after wake word
                        idx = text.find(wake) + len(wake)
                        command = text[idx:].strip(" .,!?:;-")
                        # If command has started, give another 1.5s to capture the rest of the sentence
                        if command:
                            extra_deadline = time.monotonic() + 1.2
                            silence_deadline = time.monotonic() + 0.6
                            while time.monotonic() < extra_deadline and time.monotonic() < silence_deadline:
                                samples, _ = mic.read(block_size)
                                stream.accept_waveform(sample_rate, samples.reshape(-1))
                                while recognizer.is_ready(stream):
                                    recognizer.decode_stream(stream)
                                updated = recognizer.get_result(stream).strip().lower()
                                if updated != text:
                                    text = updated
                                    command = text[idx:].strip(" .,!?:;-")
                                    silence_deadline = time.monotonic() + 0.6
                                if recognizer.is_endpoint(stream):
                                    break
                        return True, command


            if recognizer.is_endpoint(stream):
                stream = recognizer.create_stream()
