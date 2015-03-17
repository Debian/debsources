from __future__ import absolute_import

from functools import partial

from flask import request, url_for, render_template, redirect


def bind_render(template, **kwargs):
    """
    Returns a bound function of render_template.
    The template argument is passed as the first argument to
    render_template function.
    """
    return partial(render_template, template, **kwargs)


def bind_redirect(*args, **kwargs):
    """
    Returns a bound function of redirect.
    The *args argument is passed to the redirect function.
    """
    def redirect_(**kwargs_):
        # we ignore the kwargs_, we don't need them
        return redirect(*args, **kwargs)
    return redirect_


# jinja settings
def format_big_num(num):
    """
    Format the number in comma-separated form.
    """
    try:
        res = "{:,}".format(num)
    except:
        res = num
    return res


def url_for_other_page(page):
    """
    wrapper function of url_for, used for pagination.
    """
    args = dict(request.args.copy())
    args['page'] = page
    return url_for(request.endpoint, **args)
