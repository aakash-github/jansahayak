"""Turn narration.py into one WAV per clip (capstone/video/_audio/, git-ignored).

Which voice is used (settings come from the environment or backend/.env):
    VOICE_PROVIDER=elevenlabs   needs ELEVENLABS_API_KEY; ELEVENLABS_VOICE_ID picks the voice
    VOICE_PROVIDER=edge         free Microsoft neural voices (Indian English + native Hindi); EDGE_VOICE picks it
    VOICE_PROVIDER=windows      offline Windows voice, only good for checking timing
If VOICE_PROVIDER is not set: elevenlabs when a key is present, otherwise edge.

Clips are cached by provider + voice + text, so changing one line only re-voices that line.

    backend/.venv/Scripts/python capstone/video/voice.py            # make missing clips
    backend/.venv/Scripts/python capstone/video/voice.py --chars    # character count (ElevenLabs bills per character)
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from narration import CLIPS  # noqa: E402

AUDIO = HERE / "_audio"
ENV_FILE = HERE.parent.parent / "backend" / ".env"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
BREAK_RE = re.compile(r'<break time="([\d.]+)s"\s*/>')
DEVANAGARI_RE = re.compile(r"([ऀ-ॿ][ऀ-ॿ\s.,।]*)")
HINDI_PARTNER = {"en-IN-PrabhatNeural": "hi-IN-MadhurNeural", "en-IN-NeerjaNeural": "hi-IN-SwaraNeural",
                 "en-IN-NeerjaExpressiveNeural": "hi-IN-SwaraNeural"}


def env(name, default=""):
    if os.getenv(name):
        return os.environ[name]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return default


def plain(text):
    """Narration without pause tags (for subtitles and character counts)."""
    return re.sub(r"\s+", " ", BREAK_RE.sub(" ", text)).strip()


def engine():
    key = env("ELEVENLABS_API_KEY")
    name = env("VOICE_PROVIDER") or ("elevenlabs" if key else "edge")
    if name == "elevenlabs":
        if not key:
            raise SystemExit("VOICE_PROVIDER=elevenlabs needs ELEVENLABS_API_KEY in backend/.env")
        return {"name": name, "key": key, "voice": env("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"),
                "model": env("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
                "tag": f"el-{env('ELEVENLABS_VOICE_ID', 'JBFqnCBsd6RMkjVDRZzb')}-{env('ELEVENLABS_MODEL', 'eleven_multilingual_v2')}"}
    if name == "edge":
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            raise SystemExit("The free voice needs: backend/.venv/Scripts/pip install -r capstone/video/requirements.txt")
        v = env("EDGE_VOICE", "en-IN-PrabhatNeural")
        return {"name": name, "voice": v, "hindi": env("EDGE_HINDI_VOICE", HINDI_PARTNER.get(v, "hi-IN-MadhurNeural")),
                "rate": env("EDGE_RATE", "+8%"), "tag": f"edge2-{v}-{env('EDGE_RATE', '+8%')}"}
    return {"name": "windows", "tag": "windows"}


# ---------------------------------------------------------------- providers (each writes a WAV)
def eleven(text, prev_text, next_text, eng, out_wav):
    body = {"text": text, "model_id": eng["model"], "previous_text": plain(prev_text), "next_text": plain(next_text),
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.2, "use_speaker_boost": True,
                               "speed": 0.97}}
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{eng['voice']}?output_format=mp3_44100_128",
        data=json.dumps(body).encode(), method="POST",
        headers={"xi-api-key": eng["key"], "Content-Type": "application/json", "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            mp3 = out_wav.with_suffix(".mp3")
            mp3.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="ignore")
        if "library voices" in msg:
            raise SystemExit("ElevenLabs: free plans can only use the Default voices through the API. Pick one under "
                             "Voices > Default and put its ID in ELEVENLABS_VOICE_ID (or use a paid plan).")
        raise SystemExit(f"ElevenLabs error {e.code}: {msg[:300]}")
    to_wav(mp3, out_wav)
    mp3.unlink()


def edge(text, eng, out_wav):
    """Microsoft neural voice. Pauses become real silence; Devanagari runs go to the matching Hindi voice."""
    import edge_tts
    parts = []   # ("say", text, voice) | ("gap", seconds)
    for i, chunk in enumerate(BREAK_RE.split(text)):
        if i % 2:
            parts.append(("gap", float(chunk)))
            continue
        for j, run in enumerate(DEVANAGARI_RE.split(chunk)):
            if run.strip(" ,."):
                parts.append(("say", run.strip(), eng["hindi"] if j % 2 else eng["voice"]))
    pieces = []
    for n, part in enumerate(parts):
        if part[0] == "gap":
            pieces.append(("gap", part[1] * 0.8))
            continue
        mp3 = out_wav.with_name(f"{out_wav.stem}.p{n}.mp3")
        asyncio.run(edge_tts.Communicate(part[1], part[2], rate=eng["rate"]).save(str(mp3)))
        w = mp3.with_suffix(".wav")
        to_wav(mp3, w, trim=True)   # Edge pads every piece with silence; keep only the pauses we asked for
        mp3.unlink()
        pieces.append(("wav", w))
    join_wavs(pieces, out_wav)


def windows(text, out_wav):
    """Offline draft with System.Speech; Devanagari is skipped (no Hindi voice)."""
    t = DEVANAGARI_RE.sub(" ", text).replace("&", "and")
    ssml = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">{t}</speak>'
    ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          "$s.Rate = 0; $s.SetOutputToWaveFile($env:OUT_WAV); $s.SpeakSsml([Console]::In.ReadToEnd()); $s.Dispose()")
    raw = out_wav.with_suffix(".raw.wav")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], input=ssml.encode("utf-8"), check=True,
                   env={**os.environ, "OUT_WAV": str(raw)})
    to_wav(raw, out_wav)
    raw.unlink()


# ---------------------------------------------------------------- audio helpers
TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse")


def to_wav(src, dst, trim=False):
    af = ["-af", TRIM] if trim else []
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src), *af, "-ar", "44100", "-ac", "2", str(dst)],
                   check=True)


def join_wavs(pieces, out):
    """Concatenate 44.1 kHz stereo WAVs and silences into one file."""
    with wave.open(str(out), "wb") as o:
        o.setnchannels(2), o.setsampwidth(2), o.setframerate(44100)
        for kind, v in pieces:
            if kind == "gap":
                o.writeframes(b"\x00\x00\x00\x00" * int(44100 * v))
            else:
                with wave.open(str(v)) as w:
                    o.writeframes(w.readframes(w.getnframes()))
                v.unlink()


def duration(wav_path):
    with wave.open(str(wav_path)) as w:
        return w.getnframes() / w.getframerate()


def build(force=False):
    """Make sure every clip exists; return {clip_id: {"wav": path, "secs": float, "text": plain text}}."""
    AUDIO.mkdir(exist_ok=True)
    eng = engine()
    ids = list(CLIPS)
    out, made = {}, 0
    for n, cid in enumerate(ids):
        text = CLIPS[cid]
        h = hashlib.sha1(f"{eng['tag']}|{text}".encode()).hexdigest()[:10]
        wav = AUDIO / f"{cid}-{h}.wav"
        if force or not wav.exists():
            print(f"  voice [{eng['name']}] {cid}")
            tmp = AUDIO / f"_new-{cid}.wav"
            if eng["name"] == "elevenlabs":
                eleven(text, CLIPS[ids[n - 1]] if n else "", CLIPS[ids[n + 1]] if n + 1 < len(ids) else "", eng, tmp)
            elif eng["name"] == "edge":
                edge(text, eng, tmp)
            else:
                windows(text, tmp)
            for old in AUDIO.glob(f"{cid}-*.wav"):   # replace the old take only once the new one exists
                old.unlink()
            tmp.rename(wav)
            made += 1
        out[cid] = {"wav": str(wav), "secs": duration(wav), "text": plain(text)}
    total = sum(c["secs"] for c in out.values())
    print(f"voice: {eng['name']} ({eng.get('voice', '')}), {len(out)} clips ({made} new), {total / 60:.1f} min of narration")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--chars", action="store_true", help="only count characters (ElevenLabs bills per character)")
    ap.add_argument("--force", action="store_true", help="re-generate every clip")
    a = ap.parse_args()
    if a.chars:
        n = sum(len(plain(t)) for t in CLIPS.values())
        print(f"{len(CLIPS)} clips, {n} characters, about {sum(len(plain(t).split()) for t in CLIPS.values())} words")
    else:
        build(a.force)
