# Copyright (C) 2013-2021  The Debsources developers
# <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING


from functools import cmp_to_key, partial
from debian.debian_support import version_compare

from flask import request, url_for, render_template, redirect

import debsources.query as qry
from debsources import consts
from debsources.models import SuiteAlias
from debsources.excepts import InvalidPackageOrVersionError, Http404Error
from . import app_wrapper

session = app_wrapper.session


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


def url_for_other_page(page, page_path_params=None):
    """
    wrapper function of url_for, used for pagination.
    """
    args = dict(request.args.copy())
    args["page"] = page
    if page_path_params:
        args.update(page_path_params)
    return url_for(request.endpoint, **args)


def redirect_to_url(endpoint, redirect_url, redirect_code=301):
    """This is a nasty little hack. The problem is that from the
    different endpoints we can have as url parameters just the
    package, or the package and a version or a path.

    If we are in .versions we only need to supply a packagename.

    If we are in patches.summary or copyright.license then we need
    to give packagename and version.

    Navigating through patches, sources or files for license always
    requires a path hence the last case.

    """
    if request.blueprint == "sources" and request.endpoint != ".versions":
        return redirect(url_for(endpoint, path_to=redirect_url), code=redirect_code)

    parts = redirect_url.split("/")
    if len(parts) == 1:  # endpoint is versions
        return redirect(url_for(endpoint, packagename=redirect_url), code=redirect_code)
    elif len(parts) == 2:  # endpoint is summary or license view
        return redirect(
            url_for(endpoint, packagename=parts[0], version=parts[1]),
            code=redirect_code,
        )
    else:  # package/version/path
        return redirect(
            url_for(
                endpoint,
                packagename=parts[0],
                version=parts[1],
                path_to="/".join(parts[2:]),
            ),
            code=redirect_code,
        )


def handle_latest_version(endpoint, package, path):
    """
    redirects to the latest version for the requested page,
    when 'latest' is provided instead of a version number
    """

    try:
        versions = qry.pkg_names_list_versions(session, package)

    except InvalidPackageOrVersionError:
        raise Http404Error("%s not found" % package)
    # This is already sorted in the pkg_names_list_versions function.
    # So, we just extract the required value.
    version = [v.version for v in versions][-1]

    # avoids extra '/' at the end
    if path == "":
        redirect_url = "/".join([package, version])
    else:
        redirect_url = "/".join([package, version, path])
    return redirect_to_url(endpoint, redirect_url)


def handle_versions(version, package, path):
    check_for_alias = (
        session.query(SuiteAlias).filter(SuiteAlias.alias == version).first()
    )
    if check_for_alias:
        version = check_for_alias.suite
    try:
        versions_w_suites = qry.pkg_names_list_versions_w_suites(session, package)
    except InvalidPackageOrVersionError:
        raise Http404Error("%s not found" % package)

    versions = sorted(
        [v["version"] for v in versions_w_suites if version in v["suites"]],
        key=cmp_to_key(version_compare),
    )
    return versions


def parse_version(endpoint, package, version, path):
    if version == "latest":  # we search the latest available version
        return handle_latest_version(request.endpoint, package, path)

    versions = handle_versions(version, package, path)
    if versions:
        redirect_url_parts = [package, versions[-1]]
        if path:
            redirect_url_parts.append(path)
        redirect_url = "/".join(redirect_url_parts)
        return redirect_to_url(request.endpoint, redirect_url, redirect_code=302)


def generic_before_request(request, offset):
    if "api" in request.endpoint:
        offset += 1
    path_dict = request.path.split("/")
    package = path_dict[offset]
    version = path_dict[offset + 1]
    # -1 is to delete ending slash
    path = "/".join(path_dict[offset + 2 : -1])
    return parse_version(request.endpoint, package, version, path)
