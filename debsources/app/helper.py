from functools import partial

from flask import render_template, redirect


def bind_render(template, **kwargs):
    return partial(render_template, template, **kwargs)


def bind_redirect(*args, **kwargs):
    def redirect_(**kwargs_):
        # we ignore the kwargs_, we don't need them
        return redirect(*args, **kwargs)
    return redirect_
