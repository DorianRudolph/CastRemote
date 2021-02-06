import youtube_dl
from pprint import pprint
from pymp4.parser import MP4


def test_ytdl():
    # url = "https://www.youtube.com/watch?v=hjKO0d_umLc"
    url = "https://www.youtube.com/watch?v=VC_zaUil5pQ"
    ydl_opts = {"format": "best"}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=False)
        pprint(result)
        print(result["url"])
        

def test_mp4():
    # f = "ElephantsDream_AAC48K_064.mp4.dash"
    f = "ElephantsDream_H264BPL30_0100.264.dash"
    # f = "video_8000k_init.mp4"
    b = open(f, "rb").read(10000)
    cs = MP4.parse(b)
    for c in cs:
        if c.type == b"sidx":
            print(f"""<SegmentBase indexRangeExact="true" indexRange="{c.offset}-{c.end-1}">
  <Initialization range="0-{c.offset-1}"/>
</SegmentBase>
            """)
            break
    else:
        raise Exception("No sidx found")


test_ytdl()
