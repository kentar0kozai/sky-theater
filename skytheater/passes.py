"""ISS visible-pass calculation.

Computes, for a configured observer, the ISS passes that are actually
visible: the ISS is sunlit, at least `min_visible_el` degrees above the
horizon, and the observer's sun is at or below `sun_el_max` degrees.
The reported peak is the peak inside the visible segment only, because
a pass often enters Earth's shadow before its geometric peak.
"""
import math
from datetime import datetime, timedelta, timezone

from sgp4.api import Satrec

RE_KM = 6371.0
DIRS = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東",
        "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]


def dir_name(az_deg):
    return DIRS[int((az_deg + 11.25) // 22.5) % 16]


def _gmst(jd):
    t = (jd - 2451545.0) / 36525.0
    g = 280.46061837 + 360.98564736629 * (jd - 2451545.0) \
        + 0.000387933 * t * t - t * t * t / 38710000.0
    return math.radians(g % 360.0)


def _sun_dir_eci(jd):
    n = jd - 2451545.0
    L = math.radians((280.460 + 0.9856474 * n) % 360.0)
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)
    lam = L + math.radians(1.915) * math.sin(g) + math.radians(0.020) * math.sin(2 * g)
    eps = math.radians(23.439 - 0.0000004 * n)
    return (math.cos(lam), math.cos(eps) * math.sin(lam), math.sin(eps) * math.sin(lam))


def _jd_of(dt):
    return dt.timestamp() / 86400.0 + 2440587.5


class Observer:
    def __init__(self, lat, lon, alt_m=0.0, tz=timezone.utc):
        self.lat = lat
        self.lon = lon
        self.alt_m = alt_m
        self.tz = tz

    def topo(self, sat, dt):
        """(elevation_deg, azimuth_deg, sun_elevation_deg, sunlit) or None."""
        jd = _jd_of(dt)
        err, r, _v = sat.sgp4(jd, 0.0)
        if err != 0:
            return None
        sun = _sun_dir_eci(jd)
        th = _gmst(jd) + math.radians(self.lon)
        lat = math.radians(self.lat)
        sl, cl = math.sin(lat), math.cos(lat)
        st, ct = math.sin(th), math.cos(th)
        obs = (RE_KM * cl * ct, RE_KM * cl * st, RE_KM * sl)
        rho = (r[0] - obs[0], r[1] - obs[1], r[2] - obs[2])
        e = -st * rho[0] + ct * rho[1]
        n_ = -sl * ct * rho[0] - sl * st * rho[1] + cl * rho[2]
        u = cl * ct * rho[0] + cl * st * rho[1] + sl * rho[2]
        rng = math.sqrt(e * e + n_ * n_ + u * u)
        el = math.degrees(math.asin(u / rng))
        az = math.degrees(math.atan2(e, n_)) % 360.0
        up = (cl * ct, cl * st, sl)
        sun_el = math.degrees(math.asin(up[0] * sun[0] + up[1] * sun[1] + up[2] * sun[2]))
        d = r[0] * sun[0] + r[1] * sun[1] + r[2] * sun[2]
        if d < 0:
            perp = math.sqrt(max(0.0, r[0] ** 2 + r[1] ** 2 + r[2] ** 2 - d * d))
            sunlit = perp > RE_KM
        else:
            sunlit = True
        return el, az, sun_el, sunlit


def visible_passes(tle_text, observer, days=7, step_s=20,
                   min_visible_el=10.0, min_peak_el=15.0, sun_el_max=-6.0,
                   start=None):
    lines = [ln for ln in tle_text.splitlines() if ln.strip()]
    sat = Satrec.twoline2rv(lines[1], lines[2])
    start = start or datetime.now(timezone.utc)
    end = start + timedelta(days=days)
    step = timedelta(seconds=step_s)

    raw = []
    cur = None
    t = start
    while t <= end:
        res = observer.topo(sat, t)
        if res is not None:
            el, az, sun_el, sunlit = res
            if el > 0:
                if cur is None:
                    cur = []
                cur.append((t, el, az, sun_el, sunlit))
            elif cur is not None:
                raw.append(cur)
                cur = None
        t += step
    if cur is not None:
        raw.append(cur)

    out = []
    tz = observer.tz
    for pts in raw:
        seg = [p for p in pts if p[4] and p[1] >= min_visible_el and p[3] <= sun_el_max]
        if not seg:
            continue
        peak = max(seg, key=lambda p: p[1])
        if peak[1] < min_peak_el:
            continue
        first, last = seg[0], seg[-1]
        out.append({
            "date_local": first[0].astimezone(tz).strftime("%Y-%m-%d"),
            "start_local": first[0].astimezone(tz).strftime("%H:%M:%S"),
            "peak_local": peak[0].astimezone(tz).strftime("%H:%M:%S"),
            "end_local": last[0].astimezone(tz).strftime("%H:%M:%S"),
            "peak_el": round(peak[1], 1),
            "az_start": dir_name(first[2]),
            "az_peak": dir_name(peak[2]),
            "az_end": dir_name(last[2]),
            "ends_in_shadow": bool(last[1] > 12 and pts[-1][0] > last[0]),
        })
    return out
