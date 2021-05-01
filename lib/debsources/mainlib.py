# Copyright (C) 2013-2014  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING

from __future__ import absolute_import

import configparser
import importlib
import logging
from collections import defaultdict
from pathlib import Path

from debian import deb822

from debsources import updater

# TODO split configuration entry to a separate file: it's too complex
# TODO more uniform handling of config typing/defaults: it's too brittle

DEFAULT_CONFIG = defaultdict(dict)  # a non-existing key will return {}
DEFAULT_CONFIG.update(
    {
        "infra": {
            "dry_run": "false",
            "backends": "db fs hooks hooks.db hooks.fs",
            "stages": "extract suites gc stats cache charts",
            "log_level": "info",
            "expire_days": "0",
            "force_triggers": "",  # space-separated list
            "single_transaction": "true",
        },
        "webapp": {"hidden_files": "*/*.pc/"},
    }
)

LOG_FMT_FILE = "%(asctime)s %(module)s:%(levelname)s %(message)s"
LOG_FMT_STDERR = "%(module)s:%(levelname)s %(message)s"
LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"

LOG_LEVELS = {  # XXX module logging has no built-in way to do this conversion
    # unless one uses the logging.config cannon. Really?!?
    "debug": logging.DEBUG,  # verbosity >= 3
    "info": logging.INFO,  # verbosity >= 2
    "warning": logging.WARNING,  # verbosity >= 1
    "error": logging.ERROR,  # verbosity >= 0
    "critical": logging.CRITICAL,
}

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

PROBABLE_CONF_FILES = [
    ROOT_DIR / "etc" / "config.local.ini",
    Path("/etc") / "debsources" / "config.ini",
    Path("/srv") / "debsources" / "etc" / "config.local.ini",
    Path("/srv") / "debsources" / "etc" / "config.ini",
    ROOT_DIR / "etc" / "config.ini",
]


def parse_exclude(fname):
    """parse file exclusion specifications from file `fname`

    """
    exclude_specs = []
    with open(fname) as f:
        exclude_specs = list(deb822.Deb822.iter_paragraphs(f))
    return exclude_specs


def guess_conffile():
    """ returns the first probable configuration file, that exists and is not
    empty, and raises Exception if nothing is found """
    for conffile in PROBABLE_CONF_FILES:
        if conffile.exists():
            if conffile.stat().st_size > 0:  # file is not empty
                # TODO: debug
                # Doing logging here prevents Flask's development server
                # to output its usual logs in the terminal.
                # logging.info('Configuration file found: %s' % conffile)
                return conffile

    raise Exception("No configuration file found in %s" % str(PROBABLE_CONF_FILES))


def _to_path(key, value):
    """Convert paths in config to pathlib.Path."""
    if key.endswith("_dir") or key.endswith("_file"):
        value = Path(value)
    return value


def parse_conf_infra(items):
    """ returns correct typing for the [infra] section """
    typed = {}
    for (key, value) in items:
        if key == "expire_days":
            value = int(value)
        elif key == "dry_run":
            assert value in ["true", "false"]
            value = value == "true"
        elif key == "force_triggers":
            value = value.split()
        elif key == "hooks":
            value = value.split()
        elif key == "log_level":
            value = LOG_LEVELS[value]
        elif key == "backends":
            value = set(value.split())
        elif key == "stages":
            value = updater.parse_stages(value)
        elif key == "single_transaction":
            assert value in ["true", "false"]
            value = value == "true"
        typed[key] = _to_path(key, value)
    return typed


def parse_conf_webapp(items):
    """ returns correct typing for the [webapp] section """
    typed = {}
    for (key, value) in items:
        if value.lower() == "false":
            value = False
        elif value.lower() == "true":
            value = True
        # Flask only understands CAPSLOCKED keys
        typed[key.upper()] = _to_path(key, value)
    return typed


def load_conf(conffile, section="infra"):
    """
    load configuration from `conffile` and return it as a (typed) dictionary,
    containing the desired section
    """
    conf = configparser.ConfigParser(DEFAULT_CONFIG[section])

    if not conffile.exists():
        raise Exception("Configuration file %s does not exist" % conffile)
    conf.read(conffile)

    typed_conf = {"conffile": conffile}

    # Checks that we have section in the loaded conf, and throws a more
    # precise error if not (easier to debug when we know where the files are)
    if section not in conf.sections():
        raise Exception("No section [%s] found in %s" % (section, conffile))

    if section == "infra":
        typed_conf.update(parse_conf_infra(conf.items("infra")))

        exclude_file = typed_conf["local_dir"] / "exclude.conf"
        typed_conf["exclude"] = []
        if exclude_file.exists():
            typed_conf["exclude"] = parse_exclude(exclude_file)

    elif section == "webapp":
        typed_conf.update(parse_conf_webapp(conf.items("webapp")))

    else:
        typed_conf.update(conf.items(section))

    return typed_conf


def add_arguments(cmdline):
    """populate `cmdline` --- an `argpase.ArgumentParser` --- with cmdline
    options shared across several Debsources tools

    """
    cmdline.add_argument(
        "--backend",
        "-b",
        metavar="BACKEND",
        action="append",
        help="only affect a specific backend (one of: db, fs,"
        "hooks, hooks.db, hooks.fs). By default all backends"
        'are enabled; the special value "none" disables all'
        "backends. Can be specified multiple times. Warning:"
        "using this you can mess up the update logic, use at "
        "your own risk.",
        dest="backends",
    )
    cmdline.add_argument(
        "--config", "-c", dest="conffile", help="alternate configuration file"
    )
    cmdline.add_argument(
        "--dburi",
        "-u",
        dest="dburi",
        help="database URI, e.g. postgresql:///mydbname."
        'Override configuration file setting "db_uri"',
    )
    cmdline.add_argument(
        "--dry-run", "-d", dest="dry", action="store_true", help="enable dry run mode"
    )
    cmdline.add_argument(
        "--single-transaction",
        dest="single_transaction",
        choices=["yes", "no"],
        help="use a single big DB transaction, instead of "
        "smaller per-package transactions (default: yes)",
    )
    cmdline.add_argument(
        "--stage",
        "-s",
        metavar="STAGE",
        action="append",
        help="only perform a specific update stage "
        "(one of: %s). By default all update stages are "
        "performed. Can be specified multiple times. Warning:"
        "using this you can mess up the update logic, use at"
        "your own risk." % list(map(updater.pp_stage, updater.UPDATE_STAGES)),
        dest="stages",
    )
    cmdline.add_argument(
        "--trigger",
        "-t",
        metavar="EVENT/HOOK",
        action="append",
        help="force trigger of (Python) HOOK for EVENT. By "
        "default all registered hooks are triggered for all "
        "changed packages. Event is one of: %s. Hook is one "
        "of the available hooks. Can be specified multiple "
        'times. Warning: if not used with "--backend none" '
        "it might lead to multiple execution of the same "
        "hook. E.g.: -t add-package/checksums" % ", ".join(updater.KNOWN_EVENTS),
        dest="force_triggers",
    )
    cmdline.add_argument(
        "--verbose", "-v", action="count", default=0, help="increase console verbosity"
    )


def override_conf(conf, cmdline):
    """override configuration `conf` based on `cmdline` flags

    `cmdline` must be a `argpase.ArgumentParser`, on which `parse_args()` has
    been called

    """
    if cmdline.backends:
        if "none" in cmdline.backends:
            conf["backends"] = set()
        else:
            conf["backends"] = set(cmdline.backends)
    if cmdline.stages:
        conf["stages"] = set(map(updater.parse_stage, cmdline.stages))
    if cmdline.dburi:
        conf["db_uri"] = cmdline.dburi
    if cmdline.dry:
        conf["dry_run"] = True
    if cmdline.force_triggers:
        conf["force_triggers"] = []
        for trigger in cmdline.force_triggers:
            (event, hook) = trigger.split("/")
            conf["force_triggers"].append((event, hook))
    if cmdline.single_transaction:
        conf["single_transaction"] = cmdline.single_transaction == "yes"


def conf_warnings(conf):
    """check configuration `conf` and log warnings about non standard settings
    if needed

    """
    if conf["dry_run"]:
        logging.warn("note: DRY RUN mode is enabled")
    if conf["backends"] != set(DEFAULT_CONFIG["infra"]["backends"].split()):
        logging.warn("only using backends: %s" % list(conf["backends"]))
    if conf["stages"] != updater.UPDATE_STAGES:
        logging.warn(
            "only doing stages: %s" % list(map(updater.pp_stage, conf["stages"]))
        )
    if conf["force_triggers"]:
        logging.warn("forcing triggers: %s" % conf["force_triggers"])


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
        if event not in updater.KNOWN_EVENTS:
            raise ValueError('unknown event type "%s"' % event)
        observers[event].append((title, action))

    def declare_ext_callback(ext, title=""):
        assert ext.startswith(".")
        assert ext not in file_exts
        file_exts[ext] = title

    debsources = {
        "subscribe": subscribe_callback,
        "declare_ext": declare_ext_callback,
        "config": conf,
    }
    for hook in conf["hooks"]:
        plugin = importlib.import_module("debsources.plugins.hook_" + hook)
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

    if "log_file" in conf:  # log to file and stderr, w/ different settings
        logging.basicConfig(
            level=logging.DEBUG,  # log everything by default
            format=LOG_FMT_FILE,
            datefmt=LOG_DATE_FMT,
            filename=conf["log_file"],
        )
        logger.handlers[0].setLevel(conf["log_level"])  # logfile verbosity

        stderr_log = logging.StreamHandler()
        stderr_log.setLevel(console_verbosity)  # console verbosity
        stderr_log.setFormatter(logging.Formatter(LOG_FMT_STDERR))
        logger.addHandler(stderr_log)
    else:  # only log to stderr
        logging.basicConfig(
            level=console_verbosity, format=LOG_FMT_STDERR, datefmt=LOG_DATE_FMT
        )
