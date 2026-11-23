"""空の劇場 pipeline: TLE -> visible passes -> program.json (+ optional audio).

Usage:
    python -m skytheater.run [--config config.json] [--out docs] [--audio]

Writes <out>/program.json. With --audio, also writes narration WAV files
under <out>/audio/<date>/ using a local VOICEVOX engine.
"""
import argparse
import json
import os
from zoneinfo import ZoneInfo

from .passes import Observer
from .program import build_program


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out", default="docs")
    ap.add_argument("--audio", action="store_true")
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    ob = cfg["observer"]
    tz = ZoneInfo(ob["tz_name"])
    observer = Observer(ob["lat"], ob["lon"], ob.get("alt_m", 0), tz=tz)

    program = build_program(cfg, observer)
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "program.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(program, f, ensure_ascii=False, indent=1)
    print(f"wrote {out_path}: {len(program['shows'])} show(s)")
    for s in program["shows"]:
        print(" ", s["date"], s["pass"]["start_local"], "peak", s["pass"]["peak_el"],
              "held" if s["held"] else "cancelled(cloud)")

    if args.audio:
        from .audio import generate_audio
        made = generate_audio(program, args.out,
                              cfg.get("voicevox_url", "http://127.0.0.1:50021"),
                              cfg.get("voicevox_speaker", 3))
        print(f"audio: {len(made)} new file(s)")


if __name__ == "__main__":
    main()
