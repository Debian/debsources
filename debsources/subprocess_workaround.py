
from __future__ import absolute_import

import signal


def subprocess_setup():
    """SIGPIPE handling work-around. See https://bugs.python.org/issue1652

    """
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
