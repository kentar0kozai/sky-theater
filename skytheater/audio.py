"""Optional: generate narration WAV files with a VOICEVOX engine.

Requires a running VOICEVOX engine (default http://127.0.0.1:50021).
Each user generates their own audio; no audio is distributed with this
project. When redistributing generated audio, follow the terms of
VOICEVOX and of the voice library you use (credit notation etc.).
"""
import json
import os
import urllib.parse
import urllib.request


def synth(engine_url, speaker, text):
    q = urllib.parse.urlencode({"text": text, "speaker": speaker})
    req = urllib.request.Request(f"{engine_url}/audio_query?{q}", method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        query = json.load(r)
    req = urllib.request.Request(
        f"{engine_url}/synthesis?speaker={speaker}",
        data=json.dumps(query).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def generate_audio(program, out_dir, engine_url="http://127.0.0.1:50021", speaker=3):
    made = []
    for show in program["shows"]:
        if not show["held"]:
            continue
        d = os.path.join(out_dir, "audio", show["date"])
        os.makedirs(d, exist_ok=True)
        for ev in show["events"]:
            path = os.path.join(d, ev["kind"] + ".wav")
            if os.path.exists(path):
                continue
            wav = synth(engine_url, speaker, ev["say"])
            with open(path, "wb") as f:
                f.write(wav)
            made.append(path)
    return made
