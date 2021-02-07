from youtube_dl import utils, YoutubeDL
from youtube_dl.compat import compat_str
import sys


class FixedYoutubeDL(YoutubeDL):
    def _write_string(self, s, out=None):
        fixed_write_string(s, out, self.params.get('encoding'))


def fixed_write_string(s, out=None, encoding=None):
    if out is None:
        out = sys.stderr
    assert type(s) == compat_str

    if sys.platform == 'win32' and encoding is None and hasattr(out, 'fileno'):
        if utils._windows_write_string(s, out):
            return

    if ('b' in getattr(out, 'mode', '')
            or sys.version_info[0] < 3):  # Python 2 lies about mode of sys.stderr
        byt = s.encode(encoding or utils.preferredencoding(), 'ignore')
        out.write(byt)
    elif hasattr(out, 'buffer') and hasattr(out.buffer, "write"):  # kivy replaces sys.stderr with a logfile objects with str buffer
        enc = encoding or getattr(out, 'encoding', None) or utils.preferredencoding()
        byt = s.encode(enc, 'ignore')
        out.buffer.write(byt)
    else:
        out.write(s)
    out.flush()
