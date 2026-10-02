"""Solar altitude (NOAA Global Monitoring Laboratory equations, design [R3]) and the dark share of a clock hour.

The equations are the NOAA spreadsheet's (Julian century, geometric mean longitude and anomaly, equation of centre,
apparent longitude, obliquity, declination, equation of time, true solar time, hour angle); refraction is ignored,
which moves civil dusk by well under a minute.
"""
import math
from datetime import datetime, timedelta, timezone

DARK = -6.0  # civil dusk / dawn


def altitude(when_utc: datetime, lat: float, lon: float) -> float:
    jd = when_utc.timestamp() / 86400 + 2440587.5
    jc = (jd - 2451545) / 36525
    l0 = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    m = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    e = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    mr = math.radians(m)
    c = (math.sin(mr) * (1.914602 - jc * (0.004817 + 0.000014 * jc)) + math.sin(2 * mr) * (0.019993 - 0.000101 * jc)
         + math.sin(3 * mr) * 0.000289)
    app = l0 + c - 0.00569 - 0.00478 * math.sin(math.radians(125.04 - 1934.136 * jc))
    eps0 = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    eps = eps0 + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * jc))
    decl = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(app))))
    y = math.tan(math.radians(eps / 2)) ** 2
    l0r = math.radians(l0)
    eot = 4 * math.degrees(y * math.sin(2 * l0r) - 2 * e * math.sin(mr) + 4 * e * y * math.sin(mr) * math.cos(2 * l0r)
                           - 0.5 * y * y * math.sin(4 * l0r) - 1.25 * e * e * math.sin(2 * mr))
    minutes = when_utc.hour * 60 + when_utc.minute + when_utc.second / 60
    tst = (minutes + eot + 4 * lon) % 1440
    ha = tst / 4 - 180 if tst / 4 >= 0 else tst / 4 + 180
    zen = math.degrees(math.acos(math.sin(math.radians(lat)) * math.sin(math.radians(decl))
                                 + math.cos(math.radians(lat)) * math.cos(math.radians(decl)) * math.cos(math.radians(ha))))
    return 90 - zen


def dark_share(day, hour: int, utc_offset_h: int, lat: float, lon: float, step_min: int = 5) -> float:
    """Share of the clock hour [hour:00, hour+1:00) local time with the sun below −6°."""
    start = datetime(day.year, day.month, day.day, hour, tzinfo=timezone(timedelta(hours=utc_offset_h)))
    n = 60 // step_min
    pts = [(start + timedelta(minutes=step_min * (k + 0.5))).astimezone(timezone.utc) for k in range(n)]
    return sum(altitude(p, lat, lon) < DARK for p in pts) / n
