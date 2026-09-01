"""Generate tiny, dependency-free WAV cues for Water Buddy interactions."""

from __future__ import annotations

import io
import math
import struct
import wave
from functools import lru_cache

SAMPLE_RATE = 16_000


@lru_cache(maxsize=4)
def sound_bytes(event: str) -> bytes:
    """Return a short WAV cue for ``water``, ``goal``, or ``reset`` events."""

    patterns = {
        "water": ((520.0, 0.10), (680.0, 0.13)),
        "goal": ((523.25, 0.12), (659.25, 0.12), (783.99, 0.22)),
        "reset": ((440.0, 0.10), (330.0, 0.16)),
        "reminder": ((587.33, 0.12), (783.99, 0.15)),
    }
    notes = patterns.get(event, patterns["water"])
    frames: list[bytes] = []

    for frequency, duration in notes:
        sample_count = max(1, int(SAMPLE_RATE * duration))
        fade_samples = max(1, int(SAMPLE_RATE * min(0.025, duration / 3)))
        for index in range(sample_count):
            attack = min(1.0, index / fade_samples)
            release = min(1.0, (sample_count - index - 1) / fade_samples)
            envelope = max(0.0, min(attack, release))
            fundamental = math.sin(2 * math.pi * frequency * index / SAMPLE_RATE)
            shimmer = 0.16 * math.sin(2 * math.pi * frequency * 2 * index / SAMPLE_RATE)
            sample = int(9_000 * envelope * (fundamental + shimmer))
            frames.append(struct.pack("<h", max(-32_768, min(32_767, sample))))

        silence_count = int(SAMPLE_RATE * 0.025)
        frames.extend(struct.pack("<h", 0) for _ in range(silence_count))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(b"".join(frames))
    return buffer.getvalue()
