# Copyright (C) 2013-2014  Stefano Zacchiroli <zack@upsilon.cc>
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

import ConfigParser as configparser
import importlib
import logging
import os
import string

from debian import deb822

import updater

# TODO split configuration entry to a separate file: it's too complex
# TODO more uniform handling of config typing/defaults: it's too brittle

DEFAULT_CONFIG = {
    'dry_run':     'false',
    'backends':    'db fs hooks hooks.db hooks.fs',
    'stages':      'extract suites gc stats cache charts',
    'log_level':   'info',
    'expire_days': '0',
    'force_triggers': [],
    'single_transaction': 'true',
}

LOG_FMT_FILE = '%(asctime)s %(module)s:%(levelname)s %(message)s'
LOG_FMT_STDERR = '%(module)s:%(levelname)s %(message)s'
LOG_DATE_FMT = '%Y-%m-%d %H:%M:%S'

LOG_LEVELS = {  # XXX module logging has no built-in way to do this conversion
                # unless one uses the logging.config cannon. Really?!?
    'debug':    logging.DEBUG,    # verbosity >= 3
    'info':     logging.INFO,     # verbosity >= 2
    'warning':  logging.WARNING,  # verbosity >= 1
    'error':    logging.ERROR,    # verbosity >= 0
    'critical': logging.CRITICAL,
}


def parse_exclude(fname):
    """parse file exclusion specifications from file `fname`

    """
    exclude_specs = []
    with open(fname) as f:
        exclude_specs = list(deb822.Deb822.iter_paragraphs(f))
    return exclude_specs


def load_conf(conffile):
    """load configuration from `conffile` and return it as a (typed) dictionary

    """
    conf = configparser.SafeConfigParser(DEFAULT_CONFIG)
    conf.read(conffile)

    typed_conf = {'conffile': conffile}
    for (key, value) in conf.items('infra'):
        if key == 'expire_days':
            value = int(value)
        elif key == 'dry_run':
            assert value in ['true', 'false']
            value = (value == 'true')
        elif key == 'hooks':
            value = value.split()
        elif key == 'log_level':
            value = LOG_LEVELS[value]
        elif key == 'backends':
            value = set(value.split())
        elif key == 'stages':
            value = updater.parse_stages(value)
        elif key == 'single_transaction':
            assert value in ['true', 'false']
            value = (value == 'true')
        typed_conf[key] = value

    exclude_file = os.path.join(typed_conf['local_dir'], 'exclude.conf')
    typed_conf['exclude'] = []
    if os.path.exists(exclude_file):
        typed_conf['exclude'] = parse_exclude(exclude_file)

    return typed_conf


def add_arguments(cmdline):
    """populate `cmdline` --- an `argpase.ArgumentParser` --- with cmdline
    options shared across several Debsources tools

    """
    cmdline.add_argument('--backend', '-b',
                         metavar='BACKEND',
                         action='append',
                         help='only affect a specific backend (one of: db, fs, hooks, hooks.db, hooks.fs). By default all backends are enabled; the special value "none" disables all backends. Can be specified multiple times. Warning: using this you can mess up the update logic, use at your own risk.',
                         dest='backends')
    cmdline.add_argument('--config', '-c', dest='conffile',
                         help='alternate configuration file')
    cmdline.add_argument('--dburi', '-u', dest='dburi',
                         help='database URI, e.g. postgresql:///mydbname. Override configuration file setting "db_uri"')
    cmdline.add_argument('--dry-run', '-d', dest='dry',
                         action='store_true',
                         help='enable dry run mode')
    cmdline.add_argument('--single-transaction', dest='single_transaction',
                         choices=['yes', 'no'],
                         help='use a single big DB transaction, instead of smaller per-package transactions (default: yes)')
    cmdline.add_argument('--stage', '-s',
                         metavar='STAGE',
                         action='append',
                         help='only perform a specific update stage (one of: %s). By default all update stages are performed. Can be specified multiple times. Warning: using this you can mess up the update logic, use at your own risk.' % \
                           map(updater.pp_stage, updater.UPDATE_STAGES),
                         dest='stages')
    cmdline.add_argument('--trigger', '-t',
                         metavar='EVENT/HOOK',
                         action='append',
                         help='force trigger of (Python) HOOK for EVENT. By default all registered hooks are triggered for all changed packages. Event is one of: %s. Hook is one of the available hooks. Can be specified multiple times. Warning: if not used with "--backend none" it might lead to multiple execution of the same hook. E.g.: -t add-package/checksums' % \
                           string.join(updater.KNOWN_EVENTS, ', '),
                         dest='force_triggers')
    cmdline.add_argument('--verbose', '-v',
                         action='count',
                         help='increase console verbosity')


def override_conf(conf, cmdline):
    """override configuration `conf` based on `cmdline` flags

    `cmdline` must be a `argpase.ArgumentParser`, on which `parse_args()` has
    been called

    """
    if cmdline.backends:
        if 'none' in cmdline.backends:
            conf['backends'] = set()
        else:
            conf['backends'] = set(cmdline.backends)
    if cmdline.stages:
        conf['stages'] = set(map(updater.parse_stage, cmdline.stages))
    if cmdline.dburi:
        conf['db_uri'] = cmdline.dburi
    if cmdline.dry:
        conf['dry_run'] = True
    if cmdline.force_triggers:
        conf['force_triggers'] = []
        for trigger in cmdline.force_triggers:
            (event, hook) = trigger.split('/')
            conf['force_triggers'].append((event, hook))
    if cmdline.single_transaction:
        conf['single_transaction'] = (cmdline.single_transaction == 'yes')


def conf_warnings(conf):
    """check configuration `conf` and log warnings about non standard settings
    if needed

    """
    if conf['dry_run']:
        logging.warn('note: DRY RUN mode is enabled')
    if conf['backends'] != set(DEFAULT_CONFIG['backends'].split()):
        logging.warn('only using backends: %s' % list(conf['backends']))
    if conf['stages'] != updater.UPDATE_STAGES:
        logging.warn('only doing stages: %s' %
                     map(updater.pp_stage, conf['stages']))
    if conf['force_triggers']:
        logging.warn('forcing triggers: %s' % conf['force_triggers'])


def load_hooks(conf):
    """load and initialize hooks from the corresponding Python modules

    return a pair (observers, extensions), where observers is a dictionary
    mapping events to list of subscribed callable, and extensions is a
    dictionary mapping per-package file extensions (to be found in the
    filesystem storage) to the owner plugin
    """
    observers = updater.NO_OBSERVERS
    file_exts = {}

    def subscribe_callback(event, action, title=""):
        if not event in updater.KNOWN_EVENTS:
            raise ValueError('unknown event type "%s"' % event)
        observers[event].append((title, action))

    def declare_ext_callback(ext, title=""):
        assert ext.startswith('.')
        assert ext not in file_exts
        file_exts[ext] = title

    debsources = {'subscribe': subscribe_callback,
                  'declare_ext': declare_ext_callback,
                  'config': conf}
    for hook in conf['hooks']:
        plugin = importlib.import_module('plugins.hook_' + hook)
        plugin.init_plugin(debsources)

    return (observers, file_exts)


def log_level_of_verbosity(n):
    if n >= 3:
        return logging.DEBUG
    elif n >= 2:
        return logging.INFO
    elif n >= 1:
        return logging.WARNING
    else:
        return logging.ERROR


def init_logging(conf, console_verbosity=logging.ERROR):
    """initialize logging

    log everythong to logfile, log errors to stderr. stderr will be shown on
    console for interactive use, or mailed by cron.

    to completely disable logging to file ensure that the 'log_file' key is not
    defined in conf
    """
    logger = logging.getLogger()

    if 'log_file' in conf:  # log to file and stderr, w/ different settings
        logging.basicConfig(level=logging.DEBUG,  # log everything by default
                            format=LOG_FMT_FILE,
                            datefmt=LOG_DATE_FMT,
                            filename=conf['log_file'])
        logger.handlers[0].setLevel(conf['log_level'])  # logfile verbosity

        stderr_log = logging.StreamHandler()
        stderr_log.setLevel(console_verbosity)  # console verbosity
        stderr_log.setFormatter(logging.Formatter(LOG_FMT_STDERR))
        logger.addHandler(stderr_log)
    else:  # only log to stderr
        logging.basicConfig(level=console_verbosity,
                            format=LOG_FMT_STDERR,
                            datefmt=LOG_DATE_FMT)
