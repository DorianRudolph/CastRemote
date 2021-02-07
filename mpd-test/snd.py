import pychromecast
from pprint import pprint

chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=["Basement TV"])
cast = chromecasts[0]
print(cast)
cast.wait()
print(cast.status)

mc = cast.media_controller


def cast4():
    d = "http://192.168.178.20:8080/f/test.mpd"
    mc.play_media(d, "application/dash+xml")


cast4()
mc.block_until_active()
print(mc.update_status())
