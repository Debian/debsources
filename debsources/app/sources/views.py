import os

from flask import current_app

from debsources.excepts import Http404Error
from debsources.consts import SLOCCOUNT_LANGUAGES, SUITES
from debsources.app.extract_stats import extract_stats
from debsources import statistics

from ..app.views import GeneralView

from ..app.views import app, session


class StatsView(GeneralView):

    def get_stats_suite(self, suite, **kwargs):
        if suite not in statistics.suites(session, 'all'):
            raise Http404Error()  # security, to avoid suite='../../foo',
            # to include <img>s, etc.
        stats_file = os.path.join(current_app.config["CACHE_DIR"], "stats.data")
        res = extract_stats(filename=stats_file,
                            filter_suites=["debian_" + suite])

        return dict(results=res,
                    languages=SLOCCOUNT_LANGUAGES,
                    suite=suite)


    def get_stats(self):
        stats_file = os.path.join(app.config["CACHE_DIR"], "stats.data")
        res = extract_stats(filename=stats_file)

        all_suites = ["debian_" + x for x in
                      statistics.suites(session, suites='all')]
        release_suites = ["debian_" + x for x in
                          statistics.suites(session, suites='release')]
        devel_suites = ["debian_" + x for x in
                        statistics.suites(session, suites='devel')]

        return dict(results=res,
                    languages=SLOCCOUNT_LANGUAGES,
                    all_suites=all_suites,
                    release_suites=release_suites,
                    devel_suites=devel_suites)
