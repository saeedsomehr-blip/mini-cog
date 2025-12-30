from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import struct


@dataclass(frozen=True)
class WavData:
    channels: int
    sampwidth: int
    framerate: int
    frames: bytes


def _read_wav(path: Path) -> WavData | None:
    if path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            return WavData(
                channels=wf.getnchannels(),
                sampwidth=wf.getsampwidth(),
                framerate=wf.getframerate(),
                frames=frames,
            )
    except Exception:
        return None


def _write_wav(path: Path, data: WavData, start_frame: int, end_frame: int) -> None:
    frame_size = data.channels * data.sampwidth
    start = start_frame * frame_size
    end = end_frame * frame_size
    chunk = data.frames[start:end]
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(data.channels)
        wf.setsampwidth(data.sampwidth)
        wf.setframerate(data.framerate)
        wf.writeframes(chunk)


def _percentile(values: List[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = int(len(ordered) * pct)
    idx = min(max(idx, 0), len(ordered) - 1)
    return ordered[idx]


def _find_speech_regions(
    data: WavData,
    *,
    chunk_ms: int = 30,
    min_speech_ms: int = 200,
    min_silence_ms: int = 300,
    padding_ms: int = 150,
    max_chunk_s: float = 15.0,
) -> List[Tuple[int, int]]:
    frame_size = data.channels * data.sampwidth
    total_frames = len(data.frames) // frame_size
    chunk_frames = max(1, int(data.framerate * chunk_ms / 1000))
    rms_values: List[int] = []
    for start in range(0, total_frames, chunk_frames):
        end = min(total_frames, start + chunk_frames)
        chunk = data.frames[start * frame_size : end * frame_size]
        rms_values.append(_rms(chunk, data.sampwidth))

    if not rms_values:
        return []

    max_rms = max(rms_values)
    noise = _percentile(rms_values, 0.2)
    min_thresh = 100 if data.sampwidth >= 2 else 10
    threshold = max(noise * 3, int(max_rms * 0.02), min_thresh)

    speech_flags = [rms >= threshold for rms in rms_values]
    if not any(speech_flags):
        return []

    min_speech_chunks = max(1, int(min_speech_ms / chunk_ms))
    min_silence_chunks = max(1, int(min_silence_ms / chunk_ms))
    pad_frames = int(data.framerate * padding_ms / 1000)

    segments: List[Tuple[int, int]] = []
    start_idx = None
    for idx, is_speech in enumerate(speech_flags):
        if is_speech and start_idx is None:
            start_idx = idx
        elif not is_speech and start_idx is not None:
            segments.append((start_idx, idx - 1))
            start_idx = None
    if start_idx is not None:
        segments.append((start_idx, len(speech_flags) - 1))

    merged: List[Tuple[int, int]] = []
    for seg_start, seg_end in segments:
        if not merged:
            merged.append((seg_start, seg_end))
            continue
        last_start, last_end = merged[-1]
        if seg_start - last_end - 1 <= min_silence_chunks:
            merged[-1] = (last_start, seg_end)
        else:
            merged.append((seg_start, seg_end))

    frame_segments: List[Tuple[int, int]] = []
    max_frames = int(data.framerate * max_chunk_s)
    for seg_start, seg_end in merged:
        if seg_end - seg_start + 1 < min_speech_chunks:
            continue
        start_frame = max(0, seg_start * chunk_frames - pad_frames)
        end_frame = min(total_frames, (seg_end + 1) * chunk_frames + pad_frames)
        length = end_frame - start_frame
        if length <= 0:
            continue
        if length <= max_frames:
            frame_segments.append((start_frame, end_frame))
            continue
        cur = start_frame
        while cur < end_frame:
            split_end = min(end_frame, cur + max_frames)
            frame_segments.append((cur, split_end))
            cur = split_end

    return frame_segments


def prepare_speech_chunks(audio_path: Path) -> List[Path]:
    data = _read_wav(audio_path)
    if data is None:
        return [audio_path]

    segments = _find_speech_regions(data)
    if not segments:
        return [audio_path]

    out_dir = audio_path.parent / "chunks" / audio_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for idx, (start_frame, end_frame) in enumerate(segments, start=1):
        out_path = out_dir / f"{audio_path.stem}_chunk_{idx:02d}.wav"
        _write_wav(out_path, data, start_frame, end_frame)
        paths.append(out_path)
    return paths


def _rms(data: bytes, sampwidth: int) -> int:
    if not data:
        return 0
    if sampwidth == 1:
        # 8-bit PCM is unsigned.
        fmt = f"{len(data)}B"
        samples = struct.unpack(fmt, data)
        total = 0
        for s in samples:
            v = s - 128
            total += v * v
        return int((total / len(samples)) ** 0.5)
    if sampwidth == 2:
        count = len(data) // 2
        fmt = f"<{count}h"
        samples = struct.unpack(fmt, data[: count * 2])
        total = 0
        for s in samples:
            total += s * s
        return int((total / count) ** 0.5)
    if sampwidth == 4:
        count = len(data) // 4
        fmt = f"<{count}i"
        samples = struct.unpack(fmt, data[: count * 4])
        total = 0
        for s in samples:
            total += s * s
        return int((total / count) ** 0.5)
    # Fallback: treat as 8-bit unsigned.
    total = 0
    for b in data:
        v = b - 128
        total += v * v
    return int((total / len(data)) ** 0.5)
