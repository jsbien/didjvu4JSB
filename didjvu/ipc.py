# encoding=UTF-8

# Copyright © 2008-2021 Jakub Wilk <jwilk@jwilk.net>
#
# This file is part of didjvu.
#
# didjvu is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# didjvu is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.

"""
Interprocess communication
"""

import errno
import logging
import os
import pipes
import re
import signal
import subprocess


# CalledProcessError, CalledProcessInterrupted
# ============================================

# Protect from scanadf[0] and possibly other software that sets
# SIGCHLD to SIG_IGN.
# [0] https://bugs.debian.org/596232
if os.name == 'posix':
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)


def get_signal_names():
    signal_name_pattern = re.compile(r'^SIG[A-Z\d]*$')
    data = {
        name: getattr(signal, name)
        for name in dir(signal)
        if signal_name_pattern.match(name)
    }
    try:
        if data['SIGABRT'] == data['SIGIOT']:
            del data['SIGIOT']
    except KeyError:  # no coverage
        pass
    try:
        if data['SIGCHLD'] == data['SIGCLD']:
            del data['SIGCLD']
    except KeyError:  # no coverage
        pass
    return {number: name for name, number in data.items()}


CalledProcessError = subprocess.CalledProcessError


class CalledProcessInterrupted(CalledProcessError):
    _signal_names = get_signal_names()

    def __init__(self, signal_id, command):
        Exception.__init__(self, command, signal_id)

    def __str__(self):
        signal_name = self._signal_names.get(self.args[1], self.args[1])
        return f'Command {self.args[0]!r} was interrupted by signal {signal_name}'


del get_signal_names


# Subprocess
# ==========

def shell_escape(commandline):
    return ' '.join(map(pipes.quote, commandline))


class Subprocess(subprocess.Popen):
    @classmethod
    def override_env(cls, override):
        env = os.environ
        # We'd like to:
        # - preserve LC_CTYPE (which is required by some DjVuLibre tools),
        # - but reset all other locale settings (which tend to break things).
        lc_ctype = env.get('LC_ALL') or env.get('LC_CTYPE') or env.get('LANG')
        env = {
            key: value
            for key, value in env.items()
            if not (key.startswith('LC_') or key in {'LANG', 'LANGUAGE'})
        }
        if lc_ctype:
            env['LC_CTYPE'] = lc_ctype
        if override:
            env.update(override)
        return env

    def __init__(self, *args, **kwargs):
        kwargs['env'] = self.override_env(kwargs.get('env'))
        if os.name == 'posix':
            kwargs.update(close_fds=True)
        try:
            commandline = kwargs['args']
        except KeyError:
            commandline = args[0]
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(shell_escape(commandline))
        self.__command = commandline[0]
        try:
            # noinspection PyArgumentList
            subprocess.Popen.__init__(self, *args, **kwargs)
        except EnvironmentError as exception:
            exception.filename = self.__command
            raise

    def wait(self, timeout=None):
        return_code = subprocess.Popen.wait(self, timeout=timeout)
        if return_code > 0:
            raise CalledProcessError(return_code, self.__command)
        if return_code < 0:
            raise CalledProcessInterrupted(-return_code, self.__command)
        return return_code


# PIPE
# ====

PIPE = subprocess.PIPE


# require()
# =========

def _require(command):
    directories = os.environ['PATH'].split(os.pathsep)
    for directory in directories:
        path = os.path.join(directory, command)
        if os.access(path, os.X_OK):
            return
    raise OSError(errno.ENOENT, 'command not found', command)


def require(*commands):
    for command in commands:
        _require(command)


# logging support
# ===============

LOGGER = logging.getLogger('didjvu.ipc')


# __all__
# =======

__all__ = [
    'CalledProcessError', 'CalledProcessInterrupted',
    'Subprocess', 'PIPE',
]

# vim:ts=4 sts=4 sw=4 et
