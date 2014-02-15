# Copyright (C) 2014  Matthieu Caneill <matthieu.caneill@gmail.com>
#
# This file is part of Debsources.
#
# Debsources is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


PTS_PREFIX = "http://packages.qa.debian.org/"
# move this to configuration file?
# it would add a dependence layer with app.config


from models import Package, Version, SuitesMapping, SlocCount, Metric
from excepts import Http500Error

# to generate PTS link safely (for internal links we use url_for)
try:
    from werkzeug.urls import url_quote
except ImportError:
    from urlparse import quote as url_quote


class Infobox(object):
    def __init__(self, session, package, version):
        """ SQLAlchemy session, package name and version number """
        self.session = session
        self.package = package
        self.version = version
    
    def _get_direct_infos(self):
        """ information available directly in Version table """
        try:
            infos = (self.session.query(Version)
                     .filter(Version.vnumber==self.version,
                             Version.package_id==Package.id,
                             Package.name==self.package)
                     .first())
            
        except Exception as e:
            raise Http500Error(e)
        
        return infos
    
    def _get_associated_suites(self):
        """ associated suites, which come from SuitesMapping """
        try:
            suites = (self.session.query(SuitesMapping.suite)
                      .filter(SuitesMapping.sourceversion_id==Version.id,
                              Version.vnumber==self.version,
                              Version.package_id==Package.id,
                              Package.name==self.package)
                      .all())
        except Exception as e:
            raise Http500Error(e)
        
        return [x[0] for x in suites]
    
    def _get_sloc(self):
        """ sloccount """
        try:
            sloc = (self.session.query(SlocCount)
                    .filter(SlocCount.sourceversion_id==Version.id,
                            Version.vnumber==self.version,
                            Version.package_id==Package.id,
                            Package.name==self.package)
                    .order_by(SlocCount.count.desc())
                    .all())
        except Exception as e:
            raise Http500Error(e)
        
        return [(x.language, x.count) for x in sloc]
    
    def _get_metrics(self):
        """ metrics"""
        try:
            metric = (self.session.query(Metric)
                      .filter(Metric.sourceversion_id==Version.id,
                              Version.vnumber==self.version,
                              Version.package_id==Package.id,
                              Package.name==self.package)
                      .all())
        except Exception as e:
            raise Http500Error(e)

        return dict([(x.metric, x.value) for x in metric])
    
    def _get_pts_link(self):
        """
        returns an URL for the package in the Debian Package Tracking System
        """
        pts_link = PTS_PREFIX + self.package
        pts_link = url_quote(pts_link) # for '+' symbol in Debian package names
        return pts_link

    
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
        pkg_infos["area"] = infos.area
        
        if infos.vcs_type and infos.vcs_browser:
                pkg_infos['vcs_type'] = infos.vcs_type
                pkg_infos['vcs_browser'] = infos.vcs_browser
        
        pkg_infos["suites"] = self._get_associated_suites()
        
        pkg_infos["sloc"] = self._get_sloc()
        
        pkg_infos["metric"] = self._get_metrics()
        
        pkg_infos["pts_link"] = self._get_pts_link()
        
        return pkg_infos
