from functools import partial

from flask import request, url_for, render_template, redirect


def bind_render(template, **kwargs):
    return partial(render_template, template, **kwargs)


def bind_redirect(*args, **kwargs):
    def redirect_(**kwargs_):
        # we ignore the kwargs_, we don't need them
        return redirect(*args, **kwargs)
    return redirect_


# jinja settings
def format_big_num(num):
    try:
        res = "{:,}".format(num)
    except:
        res = num
    return res


def url_for_other_page(page):
    args = dict(request.args.copy())
    args['page'] = page
    return url_for(request.endpoint, **args)
