""" Usage: from packfind import find_package; find_package('LPT')
"""

import os, sys

if sys.version_info >= (3, 0):
    from importlib import find_loader
else:
    from pkgutil import find_loader

def find_package(package_name, search_levels=3):
    if find_loader(package_name) is not None:
        return
    path = os.getcwd(); pkg_init = os.path.join(package_name, '__init__.py')
    for i in xrange(search_levels):
        path = os.path.abspath(os.path.join(path, os.pardir))
        if os.path.isfile(os.path.join(path, pkg_init)):
            if not path in sys.path:
                sys.path.append(path)
            return
    print('Warning: failed to find package ' + package_name)