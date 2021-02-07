import youtube_dl
from pprint import pprint
from pymp4.parser import MP4
from mpegdash.mpd import MPD
from mpegdash.period import Period
from mpegdash.adaptation_set import AdaptationSet
from mpegdash.representation import Representation
from xml.sax.saxutils import escape
from urllib.parse import urlparse
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
    
    
def split_url(url):
    u = urlparse(url)
    assert u.params == ""
    assert u.fragment == ""
    return f"{u.scheme}://{u.netloc}/", f"{u.path[1:]}?{u.query}"


def build_representation(f, id):
    url = f["url"]
    head = get_range(url)
    ext = f["ext"]
    if ext in ("m4a", "mp4"):
        segment = compute_segment_base_mp4(head)
    else:
        raise NotImplementedError
    
    if f["acodec"] == "none":
        mime = "video/" + ext
        codec = f["vcodec"]
        extra = f'width="{f["width"]}" height="{f["height"]}"'
    else:
        mime = ("audio/" + ext).replace("m4a", "mp4")
        codec = f["acodec"]
        extra = ""

    return f"""
      <Representation id="{id}" bandwidth="{int(f["tbr"] * 1000)}" mimeType="{mime}" codecs="{codec}" {extra}>
        <BaseURL>{escape(split_url(url)[1])}</BaseURL>
        <SegmentBase indexRange="{segment[0]}-{segment[1]}">
          <Initialization range="0-{segment[0]-1}"/>
        </SegmentBase>
      </Representation>"""


def build_mpd(url, supported_codecs=("hev", "vp9", "vp8", "avc")):
    ydl_opts = {"format": "best"}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=False)
        
    # for f in result["formats"]:
    #     print(f["format"], f["ext"])
    #     print(f["url"])
    # return

    audio_formats = [f for f in result["formats"] if 
                     f["acodec"] != "none" and 
                     f["vcodec"] == "none" and
                     f["ext"] in ("m4a", "webmm")]
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
    video_formats = video_formats_by_codec[-1][1]
    
    base_urls = [split_url(f["url"])[0] for f in video_formats + audio_formats]
    if len(set(base_urls)) != 1:
        raise Exception(f"Different base urls: {base_urls}")

    mpd = f"""<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns="urn:mpeg:dash:schema:mpd:2011"
  xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 DASH-MPD.xsd"
  type="static"
  mediaPresentationDuration="PT{result["duration"]}S"
  minBufferTime="PT2S"
  profiles="urn:mpeg:dash:profile:isoff-on-demand:2011">

  <ProgramInformation moreInformationURL="youtube.com">
    <Title>{escape(result["title"])}</Title>
  </ProgramInformation>

  <BaseURL>http://192.168.178.20:8080/p/{escape(base_urls[0])}</BaseURL>
  <Period>
    <AdaptationSet subsegmentAlignment="true" subsegmentStartsWithSAP="1">
{build_representation(audio_format, 1)}
    </AdaptationSet>
    
    <AdaptationSet subsegmentAlignment="true" subsegmentStartsWithSAP="1">
{"".join(build_representation(f, i+2) for i, f in enumerate(video_formats))}
    </AdaptationSet>
  </Period>
</MPD>"""
    
    print(mpd)
    with open("test.mpd", "w") as f:
        f.write(mpd)

    for f in vf:
        print(f["width"], compute_segment_base_mp4(get_range(f["url"])))

    pprint(audio_format)
    pprint(vf)
    
    # pprint(result)
    print(result["url"])


print(build_mpd("https://www.youtube.com/watch?v=VC_zaUil5pQ", ["avc"]))
