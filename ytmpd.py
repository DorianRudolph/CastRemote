from pymp4.parser import MP4
from xml.sax.saxutils import escape
from urllib.parse import urlparse
import requests
from ebmlite import loadSchema

matroska = loadSchema('matroska.xml')
CODECS = ("hev", "vp9", "vp8", "avc")


def get_range(url, n=10000):
    return requests.get(url, headers={"Range": f"bytes=0-{n}"}).content


def compute_segment_base_mp4(data):
    cs = MP4.parse(data)
    for c in cs:
        if c.type == b"sidx":
            return c.offset, c.end - 1
    raise Exception("No sidx found")


def compute_segment_base_webm(data):
    doc = matroska.loads(data)
    for el in doc[0]:
        if el.name == "Cues":
            return el.offset, el.offset + el.size - 1
    raise Exception("No Cues element found")


def split_url(url):
    u = urlparse(url)
    assert u.params == ""
    assert u.fragment == ""
    return f"{u.scheme}://{u.netloc}/", f"{u.path[1:]}?{u.query}"


def format_mime(f):
    ext = f["ext"]
    return "video/" + ext if f["vcodec"] != "none" else ("audio/" + ext).replace("m4a", "mp4")                


def build_representation(f, id):
    url = f["url"]
    head = get_range(url)
    ext = f["ext"]
    if ext in ("m4a", "mp4"):
        segment = compute_segment_base_mp4(head)
    elif ext == "webm":
        segment = compute_segment_base_webm(head)
    else:
        raise NotImplementedError

    if f["acodec"] == "none":
        codec = f["vcodec"]
        extra = f'width="{f["width"]}" height="{f["height"]}"'
    else:
        codec = f["acodec"]
        extra = ""
    mime = format_mime(f)

    return f"""
      <Representation id="{id}" bandwidth="{int(f["tbr"] * 1000)}" mimeType="{mime}" codecs="{codec}" {extra}>
        <BaseURL>{escape(split_url(url)[1])}</BaseURL>
        <SegmentBase indexRange="{segment[0]}-{segment[1]}">
          <Initialization range="0-{segment[0] - 1}"/>
        </SegmentBase>
      </Representation>"""


def build_mpd(info, cors_proxy, supported_codecs=CODECS, max_height=100000):
    formats = info["formats"]
    audio_formats = [f for f in formats if
                     f["acodec"] != "none" and
                     f["vcodec"] == "none" and
                     f["ext"] in ("m4a", "webm")]
    audio_formats.sort(key=lambda f: f["abr"])
    audio_format = audio_formats[-1]

    video_formats = [f for f in formats if
                     f["acodec"] == "none" and
                     f["vcodec"] != "none" and
                     f["height"] <= max_height]
    video_formats.sort(key=lambda f: f["width"])
    video_formats_by_codec = [
        (codec, vf)
        for codec in supported_codecs
        if (vf := [f for f in video_formats if f["vcodec"].startswith(codec)])
    ]
    video_formats_by_codec.sort(key=lambda x: x[1][-1]["width"])
    video_formats = video_formats_by_codec[-1][1]
    
    if not video_formats:
        raise Exception("no supported video formats found")
    if not audio_format:
        raise Exception("no supported audio formats found")

    base_urls = [split_url(f["url"])[0] for f in video_formats + audio_formats]
    if len(set(base_urls)) != 1:
        raise Exception(f"Different base urls: {base_urls}")

    mpd = f"""<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns="urn:mpeg:dash:schema:mpd:2011"
  xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 DASH-MPD.xsd"
  type="static"
  mediaPresentationDuration="PT{info["duration"]}S"
  minBufferTime="PT2S"
  profiles="urn:mpeg:dash:profile:isoff-on-demand:2011">

  <ProgramInformation moreInformationURL="youtube.com">
    <Title>{escape(info["title"])}</Title>
  </ProgramInformation>

  <BaseURL>{escape(cors_proxy + base_urls[0])}</BaseURL>
  <Period>
    <AdaptationSet subsegmentAlignment="true" subsegmentStartsWithSAP="1">{
      build_representation(audio_format, 1)}
    </AdaptationSet>

    <AdaptationSet subsegmentAlignment="true" subsegmentStartsWithSAP="1">{
      "".join(build_representation(f, i + 2) for i, f in enumerate(video_formats))}
    </AdaptationSet>
  </Period>
</MPD>"""

    return mpd
