# encoding=UTF-8

# Copyright © 2009, 2010, 2011, 2012 Jakub Wilk <jwilk@jwilk.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 dated June, 1991.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

'''command line interface for *didjvu*'''

from . import utils

try:
    import argparse
except ImportError, ex:
    utils.enhance_import_error(ex, 'argparse', 'python-argparse', 'http://code.google.com/p/argparse/')
    raise

from . import djvu_extra as djvu
from . import version as version_module
try:
    from . import xmp
except ImportError, xmp_import_error:
    xmp = None

def range_int(x, y, typename):
    class rint(int):
        def __new__(cls, n):
            n = int(n)
            if not (x <= n <= y):
                raise ValueError
            return n
    return type(typename, (rint,), {})

dpi_type = range_int(djvu.DPI_MIN, djvu.DPI_MAX, 'dpi')
losslevel_type = range_int(djvu.LOSS_LEVEL_MIN, djvu.LOSS_LEVEL_MAX, 'loss level')
subsample_type = range_int(djvu.SUBSAMPLE_MIN, djvu.SUBSAMPLE_MAX, 'subsample')

def slice_type(max_slices=99):

    def slices(value):
        if ',' in value:
            result = map(int, value.split(','))
        elif '+' in value:
            result = []
            accum = 0
            for slice in value.split('+'):
                accum += int(slice)
                result += accum,
        else:
            result = [int(value)]
        if not result:
            raise ValueError('invalid slice specification')
        if len(result) > max_slices:
            raise ValueError('too many slices')
        return result
    return slices

def get_slice_repr(lst):
    def fold(lst, obj):
        return lst + [obj - sum(lst)]
    plus_lst = reduce(fold, lst[1:], lst[:1])
    return '+'.join(map(str, plus_lst))

class intact(object):

    def __init__(self, x):
        self.x = x

    def __call__(self):
        return self.x

def replace_underscores(s):
    return s.replace('_', '-')

class ArgumentParser(argparse.ArgumentParser):

    class defaults:
        pageid_template = '{base-ext}.djvu'
        pages_per_dict = 1
        dpi = djvu.DPI_DEFAULT
        fg_slices = [100]
        fg_crcb = djvu.CRCB.full
        fg_subsample = 6
        bg_slices = [74, 84, 90, 97]
        bg_crcb = djvu.CRCB.normal
        bg_subsample = 3

    def __init__(self, methods, default_method):
        argparse.ArgumentParser.__init__(self, formatter_class=argparse.RawDescriptionHelpFormatter)
        version = version_module.get_software_agent()
        self.add_argument('--version', action='version', version=version, help='show version information and exit')
        p_separate = self.add_subparser('separate', help='generate masks for images')
        p_encode = self.add_subparser('encode', help='convert images to single-page DjVu documents')
        p_bundle = self.add_subparser('bundle', help='convert images to bundled multi-page DjVu document')
        epilog = []
        default = self.defaults
        for p in p_separate, p_encode, p_bundle:
            epilog += ['%s --help' % p.prog]
            p.add_argument('-o', '--output', metavar='FILE', help='output filename')
            if p is p_bundle:
                p.add_argument(
                    '--pageid-template', metavar='TEMPLATE', default=default.pageid_template,
                    help='naming scheme for page identifiers (default: "%s")' % default.pageid_template
                )
            else:
                p.add_argument(
                    '--output-template', metavar='TEMPLATE',
                    help='naming scheme for output file (e.g. "%s")' % default.pageid_template
                )
            p.add_argument('--losslevel', dest='loss_level', type=losslevel_type, help=argparse.SUPPRESS)
            p.add_argument('--loss-level', dest='loss_level', type=losslevel_type, metavar='N', help='aggressiveness of lossy compression')
            p.add_argument('--lossless', dest='loss_level', action='store_const', const=djvu.LOSS_LEVEL_MIN, help='lossless compression (default)')
            p.add_argument('--clean', dest='loss_level', action='store_const', const=djvu.LOSS_LEVEL_CLEAN, help='lossy compression: remove flyspecks')
            p.add_argument('--lossy', dest='loss_level', action='store_const', const=djvu.LOSS_LEVEL_LOSSY, help='lossy compression: substitute patterns with small variations')
            if p is not p_separate:
                p.add_argument('--masks', nargs='+', metavar='MASK', help='use pre-generated masks')
                p.add_argument('--mask', action='append', dest='masks', metavar='MASK', help='use a pre-generated mask')
                for layer, layer_name in ('fg', 'foreground'), ('bg', 'background'):
                    if layer == 'fg':
                        p.add_argument(
                            '--fg-slices', type=slice_type(1), metavar='N',
                            help='number of slices for background (default: %s)' % get_slice_repr(default.fg_slices)
                        )
                    else:
                        p.add_argument(
                            '--bg-slices', type=slice_type(), metavar='N+...+N',
                            help='number of slices in each forgeground chunk (default: %s)' % get_slice_repr(default.bg_slices)
                        )
                    default_crcb = getattr(default, '%s_crcb' % layer)
                    p.add_argument(
                        '--%s-crcb' % layer, choices=map(str, djvu.CRCB.values),
                        help='chrominance encoding for %s (default: %s)' % (layer_name, default_crcb)
                    )
                    default_subsample = getattr(default, '%s_subsample' % layer)
                    p.add_argument(
                        '--%s-subsample' % layer, type=subsample_type, metavar='N',
                        help='subsample ratio for %s (default: %d)' % (layer_name, default_subsample)
                    )
                p.add_argument('--fg-bg-defaults', help=argparse.SUPPRESS, action='store_const', const=1)
            if p is not p_separate:
                p.add_argument(
                    '-d', '--dpi', type=dpi_type, metavar='N',
                    help='image resolution (default: %d)' % default.dpi
                )
            if p is p_bundle:
                p.add_argument(
                    '-p', '--pages-per-dict', type=int, metavar='N',
                    help='how many pages to compress in one pass (default: %d)' % default.pages_per_dict
                )
            p.add_argument(
                '-m', '--method', choices=methods, type=replace_underscores, default=default_method,
                help='binarization method (default: %s)' % default_method
            )
            if p is p_encode or p is p_bundle:
                p.add_argument('--xmp', action='store_true', help='create sidecar XMP metadata (experimental!)')
            p.add_argument('-v', '--verbose', dest='verbosity', action='append_const', const=None, help='more informational messages')
            p.add_argument('-q', '--quiet', dest='verbosity', action='store_const', const=[], help='no informational messages')
            p.add_argument('input', metavar='<input-image>', nargs='+')
            p.set_defaults(
                masks=[],
                fg_bg_defaults=None,
                loss_level=djvu.LOSS_LEVEL_MIN,
                pages_per_dict=default.pages_per_dict,
                dpi=default.dpi,
                fg_slices=intact(default.fg_slices), fg_crcb=intact(default.fg_crcb), fg_subsample=intact(default.fg_subsample),
                bg_slices=intact(default.bg_slices), bg_crcb=intact(default.bg_crcb), bg_subsample=intact(default.bg_subsample),
                verbosity=[None],
            )
        self.epilog = 'more help:\n  ' + '\n  '.join(epilog)
        self.__methods = methods

    def add_subparser(self, name, **kwargs):
        try:
            self.__subparsers
        except AttributeError:
            self.__subparsers = self.add_subparsers(parser_class=argparse.ArgumentParser)
        p = self.__subparsers.add_parser(name, **kwargs)
        p.set_defaults(_action_=name)
        return p

    def parse_args(self, actions):
        o = argparse.ArgumentParser.parse_args(self)
        if o.fg_bg_defaults is None:
            for layer in 'fg', 'bg':
                namespace = argparse.Namespace()
                setattr(o, '%s_options' % layer, namespace)
                for facet in 'slices', 'crcb', 'subsample':
                    attrname = '%s_%s' % (layer, facet)
                    value = getattr(o, attrname)
                    if isinstance(value, intact):
                        value = value()
                    else:
                        o.fg_bg_defaults = False
                    setattr(namespace, facet, value)
                    delattr(o, attrname)
                if isinstance(namespace.crcb, str):
                    namespace.crcb = getattr(djvu.CRCB, namespace.crcb)
        if o.fg_bg_defaults is not False:
            o.fg_bg_defaults = True
        o.verbosity = len(o.verbosity)
        if o.pages_per_dict <= 1:
            o.pages_per_dict = 1
        action = getattr(actions, vars(o).pop('_action_'))
        o.method = self.__methods[o.method]
        try:
            if not xmp and o.xmp:
                raise xmp_import_error
        except AttributeError:
            pass
        return action(o)

def dump_options(o, multipage=False):
    yield ('method', o.method.didjvu_name)
    if multipage:
        yield ('pages-per-dict', o.pages_per_dict)
    yield ('loss-level', o.loss_level)
    if o.fg_bg_defaults:
        yield ('fg-bg-defaults', True)
    else:
        for layer_name in 'fg', 'bg':
            layer = getattr(o, layer_name + '_options')
            yield (layer_name + '-crcb', str(layer.crcb))
            yield (layer_name + '-slices', get_slice_repr(layer.slices))
            yield (layer_name + '-subsample', layer.subsample)

__all__ = ['ArgumentParser', 'dump_options']

# vim:ts=4 sw=4 et
