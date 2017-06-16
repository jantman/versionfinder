"""
versionfinder/versionfinder.py

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

import os
import logging
import inspect
from contextlib import contextmanager

from .versioninfo import VersionInfo

try:
    import pip
except ImportError:
    # this is used within try blocks; NBD if they fail
    pass

try:
    import pkg_resources
except ImportError:
    # this is used within try blocks; NBD if they fail
    pass

try:
    from git import Repo
except Exception:
    # this is used within try blocks; NBD if they fail
    pass

logger = logging.getLogger(__name__)


class VersionFinder(object):

    def __init__(self, package_name, package_file=None, log=False,
                 caller_frame=None):
        """
        Initialize a VersionFinder to find version information of the named
        package, which includes a given file. ``package_file`` must be a Python
        file in the package; if not specified, the file calling this class
        will be used.

        VersionFinder logs rather verbosely to ``logging.debug()`` if ``log``
        is True. To simplify use as a library, unless you set ``log`` to True,
        versionfinder's logger will be set to a level of ``logging.CRITICAL``,
        suppressing all log messages. This will also silence the ``pip`` logger.

        :param package_name: name of the package to find information about
        :type package_name: str
        :param package_file: absolute path to a Python source file in the
          package to find information about; if not specified, the file calling
          this class will be used
        :type package_file: str
        :param log: If not set to True, the "versionfinder" and "pip" loggers
          will be set to a level of :py:const:`logging.CRITICAL` to suppress
          log output. If set to True, you will see a LOT of debug-level log
          output, for debugging the internals of versionfinder.
        :type log: bool
        :param caller_frame: If the call to this method is wrapped by something
          else, this should be the stack frame representing the original caller.
          Not used if ``package_file`` is specified. See
          :py:func:`versionfinder.find_version` for an example.
        :type caller_frame: frame
        """
        if not log:
            logger.setLevel(logging.CRITICAL)
            pip_log = logging.getLogger("pip")
            pip_log.setLevel(logging.CRITICAL)
            pip_log.propagate = True
        logger.debug("Finding package version for: %s", package_name)
        self.package_name = package_name
        if package_file is not None:
            logger.debug("Explicit package file: %s", package_file)
            self.package_file = package_file
        else:
            if caller_frame is None:
                caller_frame = inspect.stack()[1][0]
            self.package_file = os.path.abspath(
                inspect.getframeinfo(caller_frame).filename)
            logger.debug("Found package_file as: %s", self.package_file)
        self.package_dir = os.path.dirname(self.package_file)
        logger.debug('package_dir: %s' % self.package_dir)
        self._pip_locations = []
        self._pkg_resources_locations = []

    def find_package_version(self):
        """
        Find the installed version of the specified package, and as much
        information about it as possible (source URL, git ref or tag, etc.)

        This attempts, to the best of our ability, to find out if the package
        was installed from git, and if so, provide information on the origin
        of that git repository and status of the clone. Otherwise, it uses
        pip and pkg_resources to find the version and homepage of the installed
        distribution.

        This class is not a sure-fire method of identifying the source of
        the distribution or ensuring AGPL compliance; it simply helps with this
        process _iff_ a modified version is installed from an editable git URL
        _and_ all changes are pushed up to the publicly-visible origin.

        Returns a dict with keys 'version', 'tag', 'commit', and 'url'.
        Values are strings or None.

        :param package_name: name of the package to find information for
        :type package_name: str
        :returns: information about the installed version of the package
        :rtype: :py:class:`~versionfinder.versioninfo.VersionInfo`
        """
        res = {
            'pip_version': None,
            'pip_url': None,
            'pip_requirement': None,
            'pkg_resources_version': None,
            'pkg_resources_url': None,
            'git_tag': None,
            'git_commit': None,
            'git_remotes': None,
            'git_is_dirty': None
        }
        try:
            pip_info = self._find_pip_info()
        except Exception:
            # we NEVER want this to crash the program
            logger.debug('Caught exception running _find_pip_info()')
            pip_info = {}
        logger.debug("pip info: %s", pip_info)
        for k, v in pip_info.items():
            if v is not None:
                res['pip_' + k] = v
        try:
            pkg_info = self._find_pkg_info()
        except Exception:
            logger.debug('Caught exception running _find_pkg_info()')
            pkg_info = {}
        logger.debug("pkg_resources info: %s", pkg_info)
        for k, v in pkg_info.items():
            res['pkg_resources_' + k] = v
        gitdir = self._git_repo_path
        if gitdir is not None:
            git_info = self._find_git_info(gitdir)
            logger.debug("Git info: %s", git_info)
            for k, v in git_info.items():
                if k == 'dirty':
                    res['git_is_dirty'] = v
                elif k == 'commit':
                    res['git_commit'] = v
                elif k == 'remotes':
                    res['git_remotes'] = v
                elif k == 'tag':
                    res['git_tag'] = v
        else:
            logger.debug("Install does not appear to be a git clone")
        logger.debug("Final package info: %s", res)
        return VersionInfo(**res)

    @property
    def _git_repo_path(self):
        """
        Attempt to determine whether this package is installed via git or not;
        if so, return the path to the git repository.

        :rtype: str
        :returns: path to git repo, or None
        """
        logger.debug('Checking for git directory in: %s', self._package_top_dir)
        for p in self._package_top_dir:
            gitdir = os.path.join(p, '.git')
            if os.path.exists(gitdir):
                logger.debug('_is_git_clone() true based on %s' % gitdir)
                return gitdir
        logger.debug('_is_git_clone() false')
        return None

    def _find_pkg_info(self):
        """
        Find information about the installed package from pkg_resources.

        :returns: information from pkg_resources about ``self.package_name``
        :rtype: dict
        """
        dist = pkg_resources.require(self.package_name)[0]
        self._pkg_resources_locations = [dist.location]
        ver, url = self._dist_version_url(dist)
        return {'version': ver, 'url': url}

    def _find_pip_info(self):
        """
        Try to find information about the installed package from pip.
        This should be wrapped in a try/except.

        :returns: information from pip about ``self.package_name``.
        :rtype: dict
        """
        res = {}
        dist = None
        dist_name = self.package_name.replace('_', '-')
        logger.debug('Checking for pip distribution named: %s', dist_name)
        for d in pip.get_installed_distributions():
            if d.project_name == dist_name:
                dist = d
        if dist is None:
            logger.debug('could not find dist matching package_name')
            return res
        logger.debug('found dist: %s', dist)
        self._pip_locations = [dist.location]
        ver, url = self._dist_version_url(dist)
        res['version'] = ver
        res['url'] = url
        # this is a bit of an ugly, lazy hack...
        req = pip.FrozenRequirement.from_dist(dist, [])
        logger.debug('pip FrozenRequirement: %s', req)
        res['requirement'] = str(req.req)
        return res

    def _dist_version_url(self, dist):
        """
        Get version and homepage for a pkg_resources.Distribution

        :param dist: the pkg_resources.Distribution to get information for
        :returns: 2-tuple of (version, homepage URL)
        :rtype: tuple
        """
        ver = str(dist.version)
        url = None
        for line in dist.get_metadata_lines(dist.PKG_INFO):
            line = line.strip()
            if ':' not in line:
                continue
            (k, v) = line.split(':', 1)
            if k == 'Home-page':
                url = v.strip()
        return (ver, url)

    def _find_git_info(self, gitdir):
        """
        Find information about the git repository, if this file is in a clone.

        :param gitdir: path to the git repo's .git directory
        :type gitdir: str
        :returns: information about the git clone
        :rtype: dict
        """
        res = {'remotes': None, 'tag': None, 'commit': None, 'dirty': None}
        try:
            logger.debug('opening %s as git.Repo', gitdir)
            repo = Repo(path=gitdir, search_parent_directories=False)
            res['commit'] = repo.head.commit.hexsha
            res['dirty'] = repo.is_dirty(untracked_files=True)
            res['remotes'] = {}
            for rmt in repo.remotes:
                # each is a git.Remote
                urls = [u for u in rmt.urls]  # generator
                if len(urls) > 0:
                    res['remotes'][rmt.name] = urls[0]
            for tag in repo.tags:
                # each is a git.Tag object
                if tag.commit.hexsha == res['commit']:
                    res['tag'] = tag.name
        except Exception:
            logger.debug('Exception getting git information', exc_info=True)
        return res

    @property
    def _package_top_dir(self):
        """
        Find one or more directories that we think may be the top-level
        directory of the package; return a list of their absolute paths.

        :return: list of possible package top-level directories (absolute paths)
        :rtype: list
        """
        r = [self.package_dir]
        for l in self._pip_locations:
            if l is not None:
                r.append(l)
        for l in self._pkg_resources_locations:
            if l is not None:
                r.append(l)
        return sorted(list(set(r)))


@contextmanager
def chdir(path):
    old_dir = os.getcwd()
    logger.debug('with chdir(%s) from %s', path, old_dir)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)
