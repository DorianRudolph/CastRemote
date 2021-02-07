import requests
import enzyme
from ebmlite import loadSchema


def test_options():
    U = "https://r2---sn-5hnekn7z.googlevideo.com/videoplayback?expire=1612721048&ei=ONcfYOS4HcmtgAfVnrSYCQ&ip=94.31.82.90&id=o-APCV24yGlBlnwmh8pvwADCbsGNWUjIwmqYAofOLJGwO_&itag=137&aitags=133%2C134%2C135%2C136%2C137%2C160%2C242%2C243%2C244%2C247%2C248%2C271%2C278%2C313&source=youtube&requiressl=yes&mh=U8&mm=31%2C29&mn=sn-5hnekn7z%2Csn-5hne6nsy&ms=au%2Crdu&mv=m&mvi=2&pl=18&initcwndbps=2006250&vprv=1&mime=video%2Fmp4&ns=qe0l6aHxq4AENl4HNgIZp1AF&gir=yes&clen=120224987&dur=505.404&lmt=1612458168114400&mt=1612699034&fvip=2&keepalive=yes&c=WEB&txp=5516222&n=cLrLASSDzoJI5Vz&sparams=expire%2Cei%2Cip%2Cid%2Caitags%2Csource%2Crequiressl%2Cvprv%2Cmime%2Cns%2Cgir%2Cclen%2Cdur%2Clmt&sig=AOq0QJ8wRQIgVhKMvTxF159PuX1l6ZjMr8Go7WSTMfxi00xY4kM7gAgCIQD9kgSAjB4U-og-H8N9nvyUtJO1DuCjKhQTjp8LQeEniQ%3D%3D&lsparams=mh%2Cmm%2Cmn%2Cms%2Cmv%2Cmvi%2Cpl%2Cinitcwndbps&lsig=AG3C_xAwRQIhALPAzEoj7vOITutPn9IiliABFjeTOGnaR1uksSZBlxt-AiAb1_IPHksVffn12amV5JoqBl7sngMNppvoZ84UinWUsA%3D%3D&ratebypass=yes"

    r = requests.options(U)
    print(r.headers)
    

def test_enzyme():
    with open('yy.webm', 'rb') as f:
        webm = enzyme.MKV(f)
        print(webm)


def test_ebmlite():
    schema = loadSchema('matroska.xml')
    with open('yy.webm', 'rb') as f:
        dat = f.read(10000)
    doc = schema.loads(dat)
    print(doc[0][3])


test_ebmlite()
