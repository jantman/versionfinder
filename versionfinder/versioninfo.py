"""
versionfinder/versioninfo.py

The latest version of this package is available at:
<https://github.com/jantman/versionfinder>

################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of versionfinder.

    versionfinder is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    versionfinder is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with versionfinder.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the GPL v3)
################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/versionfinder> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
################################################################################
"""


class VersionInfo(object):
    """
    Class describing :py:class:`~.VersionFinder` result; the discovered
    information about the version and source of an installed package.
    """

    def __init__(self, pip_version=None, pip_url=None, pip_requirement=None,
                 pkg_resources_version=None, pkg_resources_url=None,
                 git_tag=None, git_commit=None, git_remotes=None,
                 git_is_dirty=None):
        """
        Construct a new VersionInfo object containing the specified version
        information.

        :param pip_version: the package version reported by pip
        :type pip_version: str
        :param pip_url: pip package "Home-page" metadata value
        :type pip_url: str
        :param pip_requirement: the package requirement as installed via pip
        :type pip_requirement: str
        :param pkg_resources_version: the package version reported by
          pkg_resources
        :type pkg_resources_version: str
        :param pkg_resources_url: pkg_resources package "Home-page" metadata
          value
        :type pkg_resources_url: str
        :param git_tag: if the package source has a git repository on disk,
          the tag matching the current commit
        :type git_tag: str
        :param git_commit: if the package source has a git repository on disk,
          the commit SHA that repository is currently at
        :type git_commit: str
        :param git_remotes: if the package source has a git repository on disk,
          a dict of name to URL pairs for each git remote
        :type git_remotes: dict
        :param git_is_dirty: if the package source has a git repository on disk,
          whether or not that repository has uncommitted changes or is behind
          origin.
        :type git_is_dirty: bool
        """
        self._pip_version = pip_version
        self._pip_url = pip_url
        self._pip_requirement = pip_requirement
        self._pkg_resources_version = pkg_resources_version
        self._pkg_resources_url = pkg_resources_url
        self._git_tag = git_tag
        self._git_commit = git_commit
        self._git_remotes = git_remotes
        self._git_is_dirty = git_is_dirty

    @property
    def as_dict(self):
        """
        Return the constructor arguments as a dictionary (effectively the
        kwargs to the constructor).

        :return: dict of constructor arguments
        :rtype: dict
        """
        return {
            'pip_version': self._pip_version,
            'pip_url': self._pip_url,
            'pip_requirement': self._pip_requirement,
            'pkg_resources_version': self._pkg_resources_version,
            'pkg_resources_url': self._pkg_resources_url,
            'git_tag': self._git_tag,
            'git_commit': self._git_commit,
            'git_remotes': self._git_remotes,
            'git_is_dirty': self._git_is_dirty,
        }

    def __repr__(self):
        """
        Return a string representation of the object.

        :return: representation of the object
        :rtype: str
        """
        d = self.as_dict
        p = ', '.join(['%s=%s' % (k, d[k]) for k in sorted(d.keys())])
        return 'VersionInfo(%s)' % p

    def __eq__(self, other):
        """

        :param other: class to compare
        :type other: VersionInfo
        :return: whether or not the class' as_dict properties are equal
        :rtype: bool
        """
        return self.as_dict == other.as_dict
