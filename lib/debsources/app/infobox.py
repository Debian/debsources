# Copyright (C) 2014-2015  The Debsources developers
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


from flask import current_app, url_for

from debsources.excepts import Http404Error, Http500Error
from debsources.models import Ctag, Metric, Package, PackageName, SlocCount, Suite

PTS_PREFIX = "https://tracker.debian.org/pkg/"
# XXX move this to configuration file?
# it would add a dependence layer with app.config

# to generate PTS link safely (for internal links we use url_for)
try:
    from werkzeug.urls import url_quote
except ImportError:  # pragma: no cover
    from urlparse import quote as url_quote


class Infobox(object):
    def __init__(self, session, package, version):
        """SQLAlchemy session, package name and version number"""
        self.session = session
        self.package = package
        self.version = version

    def _get_direct_infos(self):
        """information available directly in Package table"""
        try:
            infos = (
                self.session.query(Package)
                .filter(
                    Package.version == self.version,
                    Package.name_id == PackageName.id,
                    PackageName.name == self.package,
                )
                .first()
            )

        except Exception as e:  # pragma: no cover
            raise Http500Error(e)

        return infos

    def _get_associated_suites(self):
        """associated suites, which come from Suite"""
        try:
            suites = (
                self.session.query(Suite.suite)
                .filter(
                    Suite.package_id == Package.id,
                    Package.version == self.version,
                    Package.name_id == PackageName.id,
                    PackageName.name == self.package,
                )
                .all()
            )
        except Exception as e:  # pragma: no cover
            raise Http500Error(e)

        return [x[0] for x in suites]

    def _get_sloc(self):
        """sloccount"""
        try:
            sloc = (
                self.session.query(SlocCount)
                .filter(
                    SlocCount.package_id == Package.id,
                    Package.version == self.version,
                    Package.name_id == PackageName.id,
                    PackageName.name == self.package,
                )
                .order_by(SlocCount.count.desc())
                .all()
            )
        except Exception as e:  # pragma: no cover
            raise Http500Error(e)

        return [(x.language, x.count) for x in sloc]

    def _get_metrics(self):
        """metrics"""
        try:
            metric = (
                self.session.query(Metric)
                .filter(
                    Metric.package_id == Package.id,
                    Package.version == self.version,
                    Package.name_id == PackageName.id,
                    PackageName.name == self.package,
                )
                .all()
            )
        except Exception as e:  # pragma: no cover
            raise Http500Error(e)

        return dict([(x.metric, x.value) for x in metric])

    def _get_pts_link(self):
        """
        returns an URL for the package in the Debian Package Tracking System
        """
        pts_link = PTS_PREFIX + self.package
        pts_link = url_quote(pts_link)  # for '+' symbol in package names
        return pts_link

    def _get_ctags_count(self):
        """ctags counts"""
        try:
            ctags_count = (
                self.session.query(Ctag)
                .filter(
                    Ctag.package_id == Package.id,
                    Package.version == self.version,
                    Package.name_id == PackageName.id,
                    PackageName.name == self.package,
                )
                .count()
            )
        except Exception as e:  # pragma: no cover
            raise Http500Error(e)

        return ctags_count

    def _get_license_link(self):
        """Returns the license link in the copyright BP"""
        return url_for(
            "copyright.license", packagename=self.package, version=self.version
        )

    def get_infos(self):
        """
        Retrieves information about the version of a package:
        - area
        - vcs
        - suites
        - size
        - sloc
        - pts link
        """
        pkg_infos = dict()

        infos = self._get_direct_infos()
        if infos is None:  # pragma: no cover
            raise Http404Error()

        pkg_infos["area"] = infos.area

        if infos.vcs_type and infos.vcs_browser:
            pkg_infos["vcs_type"] = infos.vcs_type
            pkg_infos["vcs_browser"] = infos.vcs_browser

        pkg_infos["suites"] = self._get_associated_suites()

        pkg_infos["sloc"] = self._get_sloc()

        pkg_infos["metric"] = self._get_metrics()

        pkg_infos["pts_link"] = self._get_pts_link()

        pkg_infos["ctags_count"] = self._get_ctags_count()

        if current_app.config.get("BLUEPRINT_COPYRIGHT"):
            pkg_infos["copyright"] = True
            pkg_infos["license"] = self._get_license_link()
        else:
            pkg_infos["copyright"] = False

        return pkg_infos
