import youtube_dl
from pprint import pprint
from pymp4.parser import MP4
from mpegdash.mpd import MPD
from mpegdash.period import Period
from mpegdash.adaptation_set import AdaptationSet
from mpegdash.representation import Representation
import requests


def get_range(url, n=10000):
    return requests.get(url, headers={"Range": f"bytes=0-{n}"}).content


def compute_segment_base_mp4(data):
    cs = MP4.parse(data)
    for c in cs:
        if c.type == b"sidx":
            return c.offset, c.end - 1
    else:
        raise Exception("No sidx found")


def build_mpd(url, supported_codecs=("hev", "vp9", "vp8", "avc")):
    ydl_opts = {"format": "best"}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=False)
    
    url_height = result["height"]

    audio_formats = [f for f in result["formats"] if 
                     f["acodec"] != "none" and 
                     f["vcodec"] == "none" and
                     f["ext"] in ("m4a", "webm")]
    audio_formats.sort(key=lambda f: f["abr"])
    audio_format = audio_formats[-1]  # select audio format with highest bitrate

    video_formats = [f for f in result["formats"] if f["acodec"] == "none" and f["vcodec"] != "none"]
    video_formats.sort(key=lambda f: f["width"])
    video_formats_by_codec = [
        (codec, vf)
        for codec in supported_codecs
        if (vf := [f for f in video_formats if f["vcodec"].startswith(codec)])
    ]
    video_formats_by_codec.sort(key=lambda x: x[1][-1]["width"])
    vf = video_formats_by_codec[-1][1]

    mpd = MPD(profiles='urn:mpeg:dash:profile:isoff-on-demand:2011', min_buffer_time=1)
    period = Period(start=0, duration=result["duration"])
    
    as_audio = AdaptationSet(subsegment_alignment=True, subsegment_starts_with_sap=1)
    period.append_adaptation_set(as_audio)
    
    rep_audio = Representation(id=1, bandwidth=int(audio_format["tbr"] * 1000))
    as_audio.append_representation(rep_audio)

    mpd.append_period(period)
    print(mpd.to_xml(pretty_print=True).decode())

    for f in vf:
        print(f["width"], compute_segment_base_mp4(get_range(f["url"])))

    pprint(audio_format)
    pprint(vf)
    
    #pprint(result)
    print(result["url"])


print(build_mpd("https://www.youtube.com/watch?v=VC_zaUil5pQ", ["avc"]))
