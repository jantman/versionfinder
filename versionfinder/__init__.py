"""
The latest version of this package is available at:
<http://github.com/jantman/versionfinder>

##################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of versionfinder.

    versionfinder is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    versionfinder is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with versionfinder.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
##################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/versionfinder> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
##################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
##################################################################################
"""

import inspect
from .versionfinder import VersionFinder


def find_version(*args, **kwargs):
    """
    Wrapper around :py:class:`~.VersionFinder` and its
    :py:meth:`~.VersionFinder.find_package_version` method. Pass arguments and
    kwargs to VersionFinder constructor, return the value of its
    ``find_package_version`` method.

    :param package_name: name of the package to find information about
    :type package_name: str
    :param package_file: absolute path to a Python source file in the
      package to find information about; if not specified, the file calling
      this class will be used
    :type package_file: str
    :param log: If not set to True, the "versionfinder" and "pip" loggers
      will be set to a level of ``logging.CRITICAL`` to suppress
      log output. If set to True, you will see a LOT of debug-level log
      output, for debugging the internals of versionfinder.
    :type log: bool
    :returns: information about the installed version of the package
    :rtype: :py:class:`~versionfinder.versioninfo.VersionInfo`
    """
    if 'caller_frame' not in kwargs:
        kwargs['caller_frame'] = inspect.stack()[1][0]
    return VersionFinder(*args, **kwargs).find_package_version()
