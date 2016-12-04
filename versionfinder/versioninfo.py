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
    def version(self):
        """
        Return the package/distribution version, from pip if possible or else
        from pkg_resources, or else None if neither can be found.

        :return: package/distribution version
        :rtype: :py:obj:`str` or :py:data:`None`
        """
        if self._pip_version is not None:
            return self._pip_version
        return self._pkg_resources_version

    @property
    def url(self):
        """
        Return the package/distribution "Home-page", from pip if possible or
        else from pkg_resources, or else None if neither can be found.

        :return: package/distribution Home-page/URL
        :rtype: :py:obj:`str` or :py:data:`None`
        """
        if self._pip_url is not None:
            return self._pip_url
        return self._pkg_resources_url

    @property
    def pip_version(self):
        """
        Return the pip distribution version, or None if the distribution cannot
        be found with pip.

        :return: pip distribution version
        :rtype: :py:obj:`str` or :py:data:`None`
        """
        return self._pip_version

    @property
    def pip_url(self):
        """
        Return the pip distribution "Home-page", or None if the distribution
        cannot be found with pip.

        :return: pip distribution Home-page/URL
        :rtype: :py:obj:`str` or :py:data:`None`
        """
        return self._pip_url

    @property
    def pip_requirement(self):
        """
        Return the pip requirement for the current installation of the
        distribution, or None if the distribution cannot be found with pip.

        :return: pip requirement string
        :rtype: :py:obj:`str` or :py:data:`None`
        """
        return self._pip_requirement

    @property
    def pkg_resources_version(self):
        """
        Return the pkg_resources distribution version, or None if the
        distribution cannot be found with pkg_resources.

        :return: pkg_resources distribution version
        :rtype: :py:obj:`str` or :py:data:`None`
        """
        return self._pkg_resources_version

    @property
    def pkg_resources_url(self):
        """
        Return the pkg_resources distribution "Home-page", or None if the
        distribution cannot be found with pkg_resources.

        :return: pkg_resources distribution Home-page/URL
        :rtype: :py:obj:`str` or :py:data:`None`
        """
        return self._pkg_resources_url

    @property
    def git_tag(self):
        """
        Return the name of the git that that the distribution is installed at,
        or None if there is no tag matching the current commit, or if not
        installed via git.

        :return: current git tag
        :rtype: :py:obj:`str` or :py:data:`None`
        """
        return self._git_tag

    @property
    def git_commit(self):
        """
        Return the hex SHA of the current git commit that the distribution is
        installed at, or None if not installed via git.

        :return: git commit hex SHA
        :rtype: :py:obj:`str` or :py:data:`None`
        """
        return self._git_commit

    @property
    def git_remotes(self):
        """
        If the distribution is installed via git, return a dict of all remotes
        configured on the git repository; keys are the remote name and values
        are the remote's first URL. If not installed via git, return None.

        :return: dict of git remotes, name (str) to first URL (str)
        :rtype: :py:obj:`dict` or :py:data:`None`
        """
        return self._git_remotes

    @property
    def git_remote(self):
        """
        If the distribution is installed via git, return the first URL of the
        'origin' remote if one is configured for the repo, or else the first
        URL of the lexicographically-first remote, or else None.

        :return: origin or first remote URL
        :rtype: :py:obj:`str` or :py:data:`None`
        """
        if self._git_remotes is None or len(self._git_remotes) < 1:
            return None
        if 'origin' in self._git_remotes:
            return self._git_remotes['origin']
        k = sorted(self._git_remotes.keys())[0]
        return self._git_remotes[k]

    @property
    def git_is_dirty(self):
        """
        Return True if the distribution is installed via git and has uncommitted
        changes or untracked files in the repo; Return False if the distribution
        is installed via git and does not have uncommitted changes or untracked
        files in the repo; return None if the distribution is not installed
        via git.

        :return: whether or not the git repo has uncommitted changes or
          untracked files
        :rtype: :py:obj:`bool` or :py:data:`None`
        """
        return self._git_is_dirty

    @property
    def git_str(self):
        """
        If the distribution is not installed via git, return an empty string.

        If the distribution is installed via git and pip recognizes the git
        source, return the pip requirement string specifying the git URL and
        commit, with an '*' appended if :py:attr:`~.git_is_dirty` is True.

        Otherwise, return a string of the form:

            url@ref[*]

        Where URL is the remote URL, ref is the tag name if the repo is checked
        out to a commit that matches a tag or else the commit hex SHA, and '*'
        is appended if :py:attr:`~.git_is_dirty` is True.

        :return: description of the git repo remote and state
        :rtype: str
        """
        dirty = '*' if self._git_is_dirty else ''
        if 'git' in self._pip_requirement:
            return self._pip_requirement + dirty
        if self._git_commit is None and self._git_remotes is None:
            return ''
        ref = self._git_tag if self._git_tag is not None else self._git_commit
        return '%s@%s%s' % (self.git_remote, ref, dirty)

    @property
    def short_str(self):
        """
        Return a string of the form "ver <url>" where ver is the distribution
        version and URL is the distribution Home-Page url, or '' if neither
        can be found.

        :return: version and URL
        :rtype: str
        """
        if self.version is None and self.url is None:
            return ''
        return '%s <%s>' % (self.version, self.url)

    @property
    def long_str(self):
        """
        Return a long version and installation specifier string of the form:

        If :py:attr:`~.git_str` == '':

            SHORT_STR

        otherwise:

            SHORT_STR (GIT_STR)

        Where ``SHORT_STR`` is :py:attr:`~.short_str` and ``GIT_STR`` is
        :py:attr:`~.git_str`.

        :return: long version/installation specifier string
        :rtype: str
        """
        gs = self.git_str
        if gs == '':
            return self.short_str
        return self.short_str + ' (' + gs + ')'

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
