"""Build the watch-facing program (program.json) from visible passes.

Each show gets scheduled events (announce / warn5 / appear / shadow / end)
with narration text. Cloud cover comes from Open-Meteo (no API key).
A show is marked not held when cloud cover at show time exceeds the
configured threshold.
"""
import json
import urllib.request
from datetime import datetime, timedelta

from .passes import visible_passes


def fetch_tle(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def fetch_cloud(lat, lon, tz_name, dates):
    """Return {date: cloud_cover_pct_at_show_hours} from Open-Meteo."""
    if not dates:
        return {}
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}&hourly=cloud_cover"
           f"&timezone={urllib.parse.quote(tz_name)}"
           f"&start_date={min(dates)}&end_date={max(dates)}")
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    hourly = {}
    for t, c in zip(data["hourly"]["time"], data["hourly"]["cloud_cover"]):
        hourly[t] = c
    return hourly


import urllib.parse  # noqa: E402  (used by fetch_cloud)


def build_show(p, cloud_pct, cloud_cancel_pct, tz):
    d = p["date_local"]
    start = datetime.fromisoformat(f"{d}T{p['start_local']}").replace(tzinfo=tz)
    peak = datetime.fromisoformat(f"{d}T{p['peak_local']}").replace(tzinfo=tz)
    end = datetime.fromisoformat(f"{d}T{p['end_local']}").replace(tzinfo=tz)
    held = cloud_pct is None or cloud_pct <= cloud_cancel_pct
    el = p["peak_el"]
    audio_base = f"audio/{d}/{start:%H%M}"
    events = [
        {"time": (start - timedelta(minutes=30)).isoformat(), "kind": "announce",
         "vibrate": False,
         "say": (f"今夜の空の劇場のお知らせなのだ。今夜は{start:%H時%M分}から、"
                 f"国際宇宙ステーションが見えるのだ。高さは最大{el:.0f}度、{p['az_peak']}の空なのだ。"
                 + ("天気は晴れの見込みなのだ。" if held
                    else "ただし、雲が多いので中止の可能性が高いのだ。"))},
        {"time": (start - timedelta(minutes=5)).isoformat(), "kind": "warn5",
         "vibrate": True,
         "say": f"あと5分で開演なのだ。{p['az_start']}の空を見てほしいのだ。"},
        {"time": start.isoformat(), "kind": "appear", "vibrate": True,
         "say": f"開演なのだ。{p['az_start']}の空、低く光が動き始めたのだ。"},
    ]
    if p["ends_in_shadow"]:
        events.append({"time": peak.isoformat(), "kind": "shadow", "vibrate": False,
                       "say": "まもなく地球の影に入って、光が消えるのだ。これが今夜の見どころなのだ。"})
        events.append({"time": (end + timedelta(seconds=40)).isoformat(), "kind": "end",
                       "vibrate": False,
                       "say": "終演なのだ。観察スタンプを1つ押したのだ。おつかれさまなのだ。"})
    else:
        events.append({"time": end.isoformat(), "kind": "end", "vibrate": False,
                       "say": "終演なのだ。観察スタンプを1つ押したのだ。おつかれさまなのだ。"})
    for ev in events:
        ev["audio"] = f"{audio_base}/{ev['kind']}.wav"
    return {"date": d, "held": held, "cloud_pct": cloud_pct, "pass": p,
            "audio_base": audio_base, "events": events}


def build_program(cfg, observer):
    tle = fetch_tle(cfg["tle_url"])
    passes = visible_passes(
        tle, observer,
        days=cfg.get("days", 7),
        min_visible_el=cfg["thresholds"].get("min_visible_el", 10),
        min_peak_el=cfg["thresholds"].get("min_peak_el", 15),
        sun_el_max=cfg["thresholds"].get("sun_el_max", -6),
    )
    hourly = {}
    try:
        hourly = fetch_cloud(cfg["observer"]["lat"], cfg["observer"]["lon"],
                             cfg["observer"]["tz_name"],
                             sorted({p["date_local"] for p in passes}))
    except Exception:
        hourly = {}
    shows = []
    for p in passes:
        key = f"{p['date_local']}T{p['start_local'][:2]}:00"
        shows.append(build_show(p, hourly.get(key),
                                cfg["thresholds"].get("cloud_cancel_pct", 60),
                                observer.tz))
    return {
        "generated_at": datetime.now(observer.tz).isoformat(),
        "observer": cfg["observer"]["name"],
        "shows": shows,
    }
