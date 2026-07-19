#!/usr/bin/env python3
"""Assemble the ProofRank Build Week demo from local narration and captured assets."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import textwrap
from collections import OrderedDict
from pathlib import Path


FPS = 30
WIDTH = 1920
HEIGHT = 1080
INTRO_PAD = 0.55
GAP = 0.14
OUTRO_PAD = 0.8


def run(command: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def duration(ffprobe: Path, media: Path) -> float:
    result = subprocess.run(
        [
            str(ffprobe), "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(media),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def timestamp(value: float) -> str:
    total_ms = max(0, round(value * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def split_cues(text: str) -> list[str]:
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", text.strip()) if item.strip()]
    cues: list[str] = []
    for sentence in sentences:
        if len(sentence) <= 105:
            cues.append(sentence)
            continue
        parts = [item.strip() for item in re.split(r"(?<=[,:;—])\s+", sentence) if item.strip()]
        buffer = ""
        for part in parts:
            candidate = f"{buffer} {part}".strip()
            if buffer and len(candidate) > 105:
                cues.append(buffer)
                buffer = part
            else:
                buffer = candidate
        if buffer:
            cues.append(buffer)
    return cues or [text.strip()]


def write_concat(path: Path, media: list[Path]) -> None:
    lines = []
    for item in media:
        escaped = item.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def source_for_scene(assets: Path, scene: str) -> tuple[Path, bool]:
    clips = {
        "incomplete": assets / "clip-incomplete.webm",
        "complete": assets / "clip-complete.webm",
        "safety": assets / "clip-safety.webm",
    }
    if scene in clips:
        return clips[scene], True
    return assets / f"slide-{scene}.png", False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--audio-dir", required=True, type=Path)
    parser.add_argument("--assets-dir", required=True, type=Path)
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ffmpeg", required=True, type=Path)
    parser.add_argument("--ffprobe", required=True, type=Path)
    parser.add_argument(
        "--srt-output",
        type=Path,
        help="Optional sidecar subtitle path. Captions are always burned into the MP4.",
    )
    args = parser.parse_args()

    for field in ("manifest", "audio_dir", "assets_dir", "build_dir", "output", "ffmpeg", "ffprobe"):
        setattr(args, field, getattr(args, field).resolve())
    if args.srt_output is not None:
        args.srt_output = args.srt_output.resolve()

    segments = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.build_dir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    normalized_dir = args.build_dir / "audio-normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    normalized: list[Path] = []
    segment_durations: list[float] = []
    for segment in segments:
        source = args.audio_dir / f"{segment['id']}.wav"
        target = normalized_dir / f"{segment['id']}.wav"
        if not source.is_file():
            raise FileNotFoundError(source)
        run([
            str(args.ffmpeg), "-y", "-loglevel", "error", "-i", str(source),
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(target),
        ])
        normalized.append(target)
        segment_durations.append(duration(args.ffprobe, target))

    def make_silence(name: str, seconds: float) -> Path:
        target = normalized_dir / f"{name}.wav"
        run([
            str(args.ffmpeg), "-y", "-loglevel", "error", "-f", "lavfi",
            "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{seconds:.3f}",
            "-c:a", "pcm_s16le", str(target),
        ])
        return target

    intro = make_silence("silence-intro", INTRO_PAD)
    gap = make_silence("silence-gap", GAP)
    outro = make_silence("silence-outro", OUTRO_PAD)
    audio_parts = [intro]
    for index, item in enumerate(normalized):
        audio_parts.append(item)
        if index < len(normalized) - 1:
            audio_parts.append(gap)
    audio_parts.append(outro)
    audio_list = args.build_dir / "audio-concat.txt"
    write_concat(audio_list, audio_parts)
    narration = args.build_dir / "narration.wav"
    run([
        str(args.ffmpeg), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
        "-i", str(audio_list), "-c", "copy", str(narration),
    ])

    current = INTRO_PAD
    subtitle_rows: list[tuple[float, float, str]] = []
    scene_windows: OrderedDict[str, list[float]] = OrderedDict()
    for index, (segment, seconds) in enumerate(zip(segments, segment_durations)):
        scene = segment["scene"]
        if scene not in scene_windows:
            scene_windows[scene] = [0.0 if not scene_windows else current, current]
        cues = split_cues(segment["text"])
        weights = [max(1, len(re.findall(r"\w+", cue, re.UNICODE))) for cue in cues]
        allocated = 0.0
        for cue_index, (cue, weight) in enumerate(zip(cues, weights)):
            cue_start = current + allocated
            if cue_index == len(cues) - 1:
                cue_end = current + seconds
            else:
                allocated += seconds * weight / sum(weights)
                cue_end = current + allocated
            wrapped = "\n".join(textwrap.wrap(
                cue,
                width=54,
                break_long_words=False,
                break_on_hyphens=False,
            ))
            subtitle_rows.append((cue_start, cue_end, wrapped))
        current += seconds
        scene_windows[scene][1] = current
        if index < len(segments) - 1:
            current += GAP
            scene_windows[scene][1] = current
    total_duration = current + OUTRO_PAD
    scene_windows[next(reversed(scene_windows))][1] = total_duration

    srt = args.build_dir / "narration.srt"
    blocks = []
    for index, (start, end, cue) in enumerate(subtitle_rows, 1):
        blocks.append(f"{index}\n{timestamp(start)} --> {timestamp(end)}\n{cue}\n")
    srt.write_text("\n".join(blocks), encoding="utf-8")

    video_parts: list[Path] = []
    for part_index, (scene, (start, end)) in enumerate(scene_windows.items(), 1):
        seconds = max(0.2, end - start)
        source, moving = source_for_scene(args.assets_dir, scene)
        if not source.is_file():
            raise FileNotFoundError(source)
        target = args.build_dir / f"video-{part_index:02d}-{scene}.mp4"
        command = [str(args.ffmpeg), "-y", "-loglevel", "error"]
        if moving:
            command += ["-stream_loop", "-1", "-i", str(source)]
        else:
            command += ["-loop", "1", "-framerate", str(FPS), "-i", str(source)]
        command += [
            "-t", f"{seconds:.3f}",
            "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=0x07111f,fps={FPS},format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-r", str(FPS), "-pix_fmt", "yuv420p", str(target),
        ]
        run(command)
        video_parts.append(target)

    video_list = args.build_dir / "video-concat.txt"
    write_concat(video_list, video_parts)
    visuals = args.build_dir / "visuals.mp4"
    run([
        str(args.ffmpeg), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
        "-i", str(video_list), "-c", "copy", str(visuals),
    ])

    subtitle_filter = (
        "subtitles=narration.srt:force_style='FontName=Segoe UI,FontSize=13,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,"
        "Outline=1,Shadow=0,Alignment=2,MarginV=22'"
    )
    run([
        str(args.ffmpeg), "-y", "-loglevel", "error", "-i", str(visuals), "-i", str(narration),
        "-vf", subtitle_filter, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        "-t", f"{total_duration:.3f}", str(args.output.resolve()),
    ], cwd=args.build_dir)

    sidecar = None
    if args.srt_output is not None:
        args.srt_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(srt, args.srt_output)
        sidecar = str(args.srt_output)
    result = {
        "status": "ok",
        "output": str(args.output.resolve()),
        "burned_subtitles": True,
        "sidecar_subtitles": sidecar,
        "duration_seconds": round(duration(args.ffprobe, args.output), 3),
        "narration_segments": len(segments),
        "scenes": list(scene_windows),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
