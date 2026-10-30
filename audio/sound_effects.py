"""Stark Industries audio cue generator using synthesized waveforms."""
import threading
import numpy as np


def _play_tone_thread(samples: np.ndarray, sample_rate: int = 24000):
    try:
        import sounddevice as sd
        sd.play(samples, sample_rate, blocking=False)
    except Exception:
        pass


def play_wake_chime():
    """Crisp two-tone rising chime when J.A.R.V.I.S. activates/starts listening."""
    sample_rate = 24000
    duration1 = 0.08
    duration2 = 0.12
    t1 = np.linspace(0, duration1, int(sample_rate * duration1), endpoint=False)
    t2 = np.linspace(0, duration2, int(sample_rate * duration2), endpoint=False)

    # Tone 1: 587.33 Hz (D5) with exponential decay
    tone1 = 0.22 * np.sin(2 * np.pi * 587.33 * t1) * np.exp(-t1 * 18)
    # Tone 2: 880.00 Hz (A5) with smooth decay
    tone2 = 0.28 * np.sin(2 * np.pi * 880.00 * t2) * np.exp(-t2 * 12)

    combined = np.concatenate([tone1, tone2])
    threading.Thread(target=_play_tone_thread, args=(combined, sample_rate), daemon=True).start()


def play_confirm_chime():
    """Soft confirmation ping when a command is acknowledged or completed."""
    sample_rate = 24000
    duration = 0.14
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Harmonic ping at 659.25 Hz (E5) + overtone 1318.5 Hz
    tone = (0.2 * np.sin(2 * np.pi * 659.25 * t) + 0.1 * np.sin(2 * np.pi * 1318.5 * t)) * np.exp(-t * 16)
    threading.Thread(target=_play_tone_thread, args=(tone, sample_rate), daemon=True).start()


def play_standby_chime():
    """Gentle descending chime when J.A.R.V.I.S. returns to standby."""
    sample_rate = 24000
    duration = 0.15
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Pitch slides downwards
    freqs = np.linspace(700, 440, len(t))
    phase = 2 * np.pi * np.cumsum(freqs) / sample_rate
    tone = 0.18 * np.sin(phase) * np.exp(-t * 10)
    threading.Thread(target=_play_tone_thread, args=(tone, sample_rate), daemon=True).start()
