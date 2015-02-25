from functools import partial

from flask import render_template


def bind_render(template, **kwargs):
    return partial(render_template, template, **kwargs)
