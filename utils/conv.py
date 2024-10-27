from datetime import timedelta, datetime
from typing import Union
from re import compile
from utils.language.preload import language as loc
YOUTUBE_VIDEO_REG = compile(r"(https?://)?(www\.)?youtube\.(com|nl)/watch\?v=([-\w]+)")
URLREGEX = compile(r'^https?://[^\s/$.?#].\S*$')

replaces = [
    ('&quot;', '"'),
    ('&amp;', '&'),
    ('(', '\u0028'),
    (')', '\u0029'),
    ('[', '【'),
    (']', '】'),
    ("  ", " "),
    ("*", '"'),
    ("_", ' '),
    ("{", "\u0028"),
    ("}", "\u0029"),
    ("`", "'")
]
def trim_text(text: str, limit: int = 0):
    for r in replaces:
        text = text.replace(r[0], r[1])

    if limit:
        text = f"{text[:limit]}..." if len(text) > limit else text

    return text

def time_format(milliseconds: Union[int, float], use_names: bool = False, language: str = "vi") -> str:
    minutes, seconds = divmod(int(milliseconds / 1000), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    if use_names:

        times = []

        for time_, name in (
                (days, loc.get(language, 'time',"days")),
                (hours, loc.get(language, 'time',"hours")),
                (minutes, loc.get(language, 'time',"min")),
                (seconds, loc.get(language, 'time',"sec"))
        ):
            if not time_:
                continue

            times.append(f"{time_} {name}")

        try:
            last_time = times.pop()
        except IndexError:
            last_time = None
            times = ["1s"]

        strings = ", ".join(t for t in times)

        if last_time:
            strings += f" {loc.get(language, 'time','and')} {last_time}" if strings else last_time

    else:

        strings = f"{minutes:02d}:{seconds:02d}"

        if hours:
            strings = f"{hours}:{strings}"

        if days:
            strings = (f"{days} d" if days > 1 else f"{days} d") + (f", {strings}" if strings != "00:00" else "")

    return strings

class LoopMODE(enumerate):
    OFF = 0
    SONG = 1
    PLAYLIST = 2


time_names = ["seconds", "minutes", "hours"]

def string_to_seconds(time):
    try:

        times = reversed([i for i in time.replace(" ", ":").split(':') if i.isdigit()])
        time_dict = {}

        for n, t in enumerate(times):
            time_dict[time_names[n]] = int(t)

        return timedelta(**time_dict).total_seconds()

    except:
        return

def percentage(part, whole):
    return int((part * whole) / 100.0)

sources = {
    "deezer": "https://i.ibb.co/Wz7kJYy/deezer.png",
    "soundcloud": "https://i.ibb.co/CV6NB6w/soundcloud.png",
    "spotify": "https://i.ibb.co/3SWMXj8/spotify.png",
    "youtube": "https://i.ibb.co/LCsCCWD/8198147-music-play-player-sound-stream-icon.png",
    "applemusic": "https://i.ibb.co/Dr4hbS5/applemusic.png",
    "twitch": "https://cdn3.iconfinder.com/data/icons/popular-services-brands-vol-2/512/twitch-512.png"
}

def music_source_image(sourcename):
    return sources.get(
        sourcename,
        "https://i.ibb.co/17CK6c1/764167636849917952.gif"
    )

