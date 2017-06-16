"""
versionfinder/tests/test_acceptance.py

SEE TestAcceptance class docstring for information!

!!!!!!!IMPORTANT!!!!!!
When adding test cases, also add them to the list in README.rst!

The latest version of this package is available at:
<https://github.com/jantman/versionfinder>

################################################################################
Copyright 2015 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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

import pytest
import sys
import os
import subprocess
import json
import inspect
import backoff
import requests
import logging
from versionfinder.versionfinder import chdir
from tempfile import mkdtemp
from contextlib import contextmanager

if sys.version_info >= (3, 3):
    from subprocess import DEVNULL
else:  # unreachable under 3.4+ - pragma: no cover
    DEVNULL = open(os.devnull, 'wb')

logger = logging.getLogger(__name__)

TEST_PROJECT = 'versionfinder_test_pkg'
TEST_GIT_HTTPS_URL = 'https://github.com/jantman/versionfinder-test-pkg.git'
TEST_FORK_HTTPS_URL = 'https://github.com/sniknej/versionfinder-test-pkg.git'
TEST_PROJECT_URL = 'https://github.com/jantman/versionfinder-test-pkg'
TEST_VERSION = '0.2.5'
TEST_TAG = '0.2.5'
TEST_TAG_COMMIT = '212d9950ca546013b5539133d7862c2fa4bea6f3'
TEST_MASTER_COMMIT = 'd3e34699fb7bf81c90ddd3e74c557a603aa22f98'
TEST_BRANCH = 'testbranch'
TEST_BRANCH_COMMIT = 'a5f7fa6b3b7aa57aa2661633896ba61eb78bbc97'

TEST_TARBALL = 'https://github.com/jantman/versionfinder-test-pkg/releases/' \
               'download/{ver}/versionfinder_test_pkg-{ver}.tar' \
               '.gz'.format(ver=TEST_VERSION)
TEST_TARBALL_PATH = None  # set by setup_module()
TEST_WHEEL = 'https://github.com/jantman/versionfinder-test-pkg/releases/' \
             'download/{ver}/versionfinder_test_pkg-{ver}-py2.py3-none-any' \
             '.whl'.format(ver=TEST_VERSION)
TEST_WHEEL_PATH = None  # set by setup_module()
TEST_EGG_FMT = 'https://github.com/jantman/versionfinder-test-pkg/releases/' \
               'download/{ver}/versionfinder_test_pkg-{ver}-%s.egg'.format(
                   ver=TEST_VERSION)
TEST_EGG_VERSIONS = ['py2.6', 'py2.7', 'py3.3', 'py3.4', 'py3.5']
TEST_EGG_PATH = None


def setup_module(module):
    global TEST_TARBALL_PATH, TEST_WHEEL_PATH, TEST_EGG_PATH
    TEST_TARBALL_PATH = get_package(TEST_TARBALL)
    TEST_WHEEL_PATH = get_package(TEST_WHEEL)
    pyver = 'py%s.%s' % (sys.version_info[0], sys.version_info[1])
    if pyver in TEST_EGG_VERSIONS:
        TEST_EGG_PATH = get_package(TEST_EGG_FMT % pyver)
    else:
        print("'%s' not in TEST_EGG_VERSIONS" % pyver)


def _get_git_commit():
    """
    Get the current (short) git commit hash of the current directory.

    :returns: short git hash
    :rtype: string
    """
    try:
        commit = _check_output([
            'git',
            'rev-parse',
            'HEAD'
        ], stderr=DEVNULL).strip()
        logger.debug("Found source git commit: %s", commit)
    except Exception:
        logger.debug("Unable to run git to get commit")
        commit = None
    return commit


def _check_output(args, stderr=None, env=None):
    """
    Python version compatibility wrapper for subprocess.check_output

    :param stderr: what to do with STDERR - None or an appropriate argument
     to subprocess.check_output / subprocess.Popen
    :raises: subprocess.CalledProcessError
    :returns: command output
    :rtype: string
    """
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=stderr, env=env)
    (res, err) = p.communicate()
    if p.returncode != 0:
        print("Command %s OUT/ERR:\n%s", args, res)
        raise subprocess.CalledProcessError(p.returncode, args)
    if not isinstance(res, type("")):
        res = res.decode('utf-8')
    return res


@contextmanager
def capsys_disabled(capsys):
    """
    Backport of pytest's ``capsys.disabled`` ContextManager to pytest versions
    < 3.0. Allows us to print/write directly to stdout and stderr from within
    tests.

    :param capsys: pytest capsys fixture
    """
    capmanager = capsys.request.config.pluginmanager.getplugin('capturemanager')
    capmanager.suspendcapture_item(capsys.request.node, "call", in_=True)
    try:
        yield
    finally:
        capmanager.resumecapture()


class AcceptanceHelpers(object):
    """
    Long-running acceptance tests for VersionFinder.

    The purpose of these tests is to create virtualenvs and then install an
    example package (https://github.com/jantman/versionfinder-test-pkg) in them
    using a variety of methods (i.e. setup.py, pip install from directory,
    git URL, tarball or wheel, etc.), and then call the package's console entry
    point (``versionfinder-test``) which calls ``versionfinder.find_version()``
    from a number of different locations in the package tree, and finally writes
    JSON to STDOUT describing the result of each of the ``find_version()`` calls
    (and any exceptions they raised). We then compare them to each other and,
    assuming they're all identical, compare them to our expected output.

    The goal is to confirm that versionfinder returns the correct information
    when the target package is installed with as many different methods as
    possible.

    This class defines a bunch of helper methods, which are used in the tests
    (in subclasses).
    """

    def setup_method(self, method):
        os.environ['VERSIONCHECK_DEBUG'] = 'true'
        print("\n")
        self.source_dir = self._get_source_dir()
        self._set_git_config()
        self.current_venv_path = sys.prefix

    def _get_source_dir(self):
        """
        Determine the directory containing the project source. This is assumed
        to be either the TOXINIDIR environment variable, or determined relative
        to this file.

        :returns: path to the awslimitchecker source
        :rtype: str
        """

        s = os.environ.get('TOXINIDIR', None)
        if s is None:
            s = os.path.abspath(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    '..',
                    '..'
                )
            )
        assert os.path.exists(s)
        return s

    def _git_add_remote(self, path, rmt_name, rmt_url):
        """
        Add a git remote to the repo at path

        :param path: path to the git repo
        :type path: str
        :param rmt_name: name for the remote
        :type rmt_name: str
        :param rmt_url: URL for the remote
        :type rmt_url: str
        """
        args = [
            'git',
            'remote',
            'add',
            rmt_name,
            rmt_url
        ]
        with chdir(path):
            res = _check_output(args)
            print(res)

    def _set_git_config(self, set_in_travis=False):
        if not set_in_travis and os.environ.get('TRAVIS', '') != 'true':
            print("not running in Travis; not setting git config")
            return
        try:
            res = _check_output([
                'git',
                'config',
                'user.email'
            ]).strip()
        except subprocess.CalledProcessError as ex:
            res = None
        if res != '' and res is not None:
            print("Got git config user.email as %s" % res)
        else:
            res = _check_output([
                'git',
                'config',
                'user.email',
                'travisci@jasonantman.com'
            ])
            print("Set git config user.email:\n%s" % res)
        # name
        try:
            res = _check_output([
                'git',
                'config',
                'user.name'
            ]).strip()
        except subprocess.CalledProcessError as ex:
            print(ex)
            res = None
        if res != '' and res is not None:
            print("Got git config user.name as %s" % res)
        else:
            res = _check_output([
                'git',
                'config',
                'user.name',
                'travisci'
            ])
            print("Set git config user.name:\n%s" % res)

    def _set_git_tag(self, path, tagname):
        """set a git tag for the current commit"""
        with chdir(path):
            self._set_git_config()
            commit = _check_output([
                'git',
                'rev-parse',
                'HEAD'
            ]).strip()
            print("Creating git tag 'versiontest' of %s" % commit)
            res = _check_output([
                'git',
                'tag',
                '-a',
                '-m',
                tagname,
                tagname
            ])
            print(res)
            print("Source git tag: %s" % tagname)
        return tagname

    def _git_add_commit(self, path, commit_msg):
        """
        git add -A and git commit -m commit_msg in ``path``.
        """
        print_header('_git_add_commit(%s, %s)' % (path, commit_msg))
        with chdir(path):
            self._set_git_config()
            out = _check_output([
                'git',
                'add',
                '-A'
            ])
            print(out)
            out = _check_output([
                'git',
                'commit',
                '-m',
                '"%s"' % commit_msg
            ])
            print(out)
            out = _check_output([
                'git',
                'rev-parse',
                'HEAD'
            ]).strip()
        return out

    def _make_venv(self, path):
        """
        Create a venv in ``path``. Make sure it exists.

        :param path: filesystem path to directory to make the venv base
        """
        virtualenv = os.path.join(self.current_venv_path, 'bin', 'virtualenv')
        assert os.path.exists(virtualenv) is True, 'virtualenv not found'
        args = [virtualenv, path]
        print_header(" _make_venv() running: " + ' '.join(args))
        try:
            res = _check_output(args, stderr=subprocess.STDOUT)
            print(res)
            print_header("DONE")
        except subprocess.CalledProcessError:
            print_header('FAILED')
        pypath = os.path.join(path, 'bin', 'python')
        assert os.path.exists(pypath) is True, "does not exist: %s" % pypath
        # install our source in the venv
        self._pip_install(path, [self.source_dir])

    def _pip_install(self, path, args):
        """
        In the virtualenv at ``path``, run ``pip install [args]``.

        :param path: venv base/root path
        :type path: str
        :param args: ``pip install`` arguments
        :type args: list
        """
        pip = os.path.join(path, 'bin', 'pip')
        # get pip version
        res = _check_output([pip, '--version']).strip()
        final_args = [pip, 'install']
        final_args.extend(args)
        print_header("_pip_install() running: " + ' '.join(final_args))
        res = _check_output(final_args, stderr=subprocess.STDOUT)
        print(res)
        print_header('DONE')

    def _easy_install(self, path, args):
        """
        In the virtualenv at ``path``, run ``easy_install [args]``.

        :param path: venv base/root path
        :type path: str
        :param args: ``easy_install`` arguments
        :type args: list
        """
        easy_install = os.path.join(path, 'bin', 'easy_install')
        final_args = [easy_install]
        final_args.extend(args)
        print_header("_easy_install() running: " + ' '.join(final_args))
        res = _check_output(final_args, stderr=subprocess.STDOUT)
        print(res)
        print_header('DONE')

    def _make_git_repo(self, path):
        """create a git repo under path; return the commit"""
        print_header("creating git repository in %s" % path)
        with chdir(path):
            _check_output(['git', 'init', '.'])
            self._set_git_config()
            with open('foo', 'w') as fh:
                fh.write('foo')
            _check_output(['git', 'add', 'foo'])
            self._set_git_config(set_in_travis=True)
            _check_output(['git', 'commit', '-m', 'foo'])
            commit = _get_git_commit()
            print_header("git repository in %s commit: %s" % (path, commit))
        return commit

    def _get_version(self, path, env=None):
        """
        In the virtualenv at ``path``, run ``versionfinder-test`` and
        return the JSON-decoded output dict.

        :param path: venv base/root path
        :type path: str
        :return: versionfinder-test command output
        :rtype: dict
        """
        args = [os.path.join(path, 'bin', 'versionfinder-test')]
        print_header("_get_version() running: " + ' '.join(args))
        res = _check_output(args, stderr=subprocess.STDOUT, env=env)
        print(res)
        print('DONE')
        j = json.loads(res.strip().split("\n")[-1])
        return strip_unicode(j)

    def _get_result(self, d):
        """
        Given the raw (JSON-decoded) result dict from :py:meth:`~._get_version`,
        iterate through all of the keys. Assert that their values are all
        identical, and don't contain exceptions. Return the identical result
        dict.

        :param d: result dict from :py:meth:`~._get_version`
        :type d: dict
        :return: dict describing identical results
        :rtype: dict
        """
        keys = sorted(d.keys())
        # use the first one as "expected" to compare the others against
        expected = d[keys[0]]
        err = ''
        # iterate each result; it's an error if either it failed, or it doesn't
        # match the expected value
        for k in keys:
            if d[k].get('failed', True) is True:
                err += "Key %s failed with %s %s: \n%s\n" % (
                    k, d[k].get('exc_type', ''), d[k].get('exc_str', ''),
                    d[k].get('traceback', ''))
            if d[k] != expected:
                err += "Key %s does not match expected:\n%s\n" % (
                    k, dictdiff(d[k], expected))
        # AssertionError on any error conditions, but we want to show ALL
        assert err == '', err
        # else return the indentical dict for all of them
        return expected

    def _git_checkout(self, path, ref):
        cmd = ['git', 'checkout', '-f', ref]
        print_header("_git_checkout() running: '%s' in: %s" % (
            ' '.join(cmd), path))
        with chdir(path):
            output = _check_output(cmd, stderr=subprocess.STDOUT)
            print(output)
        print_header('DONE')

    def _git_clone_test(self, ref=None, url=None):
        """
        Clone TEST_GIT_HTTPS_URL to a local temporary directory; checkout
        the specified ref.

        :return: path to git clone
        :rtype: str
        """
        if url is None:
            url = TEST_GIT_HTTPS_URL
        d = mkdtemp(prefix='pytest-versionfinder')
        print_header('_git_clone_test(%s) cloning %s into %s' % (
            ref, url, d))
        output = _check_output(
            ['git', 'clone', url, d],
            stderr=subprocess.STDOUT
        )
        print(output)
        print_header('DONE')
        if ref is not None:
            self._git_checkout(d, ref)
        return d


@pytest.mark.acceptance
class TestPip(AcceptanceHelpers):

    def test_install_local_master(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, test_src))
        self._pip_install(path, [test_src])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_local_e(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, test_src))
        self._pip_install(path, ['-e', test_src])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_MASTER_COMMIT,
                'git_tag': None,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=%s' % (
                    TEST_GIT_HTTPS_URL, TEST_MASTER_COMMIT, TEST_PROJECT
                )
            }
        }
        assert actual == expected

    def test_install_local_e_dirty(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, test_src))
        self._pip_install(path, ['-e', test_src])
        fpath = os.path.join(test_src, 'versionfinder_test_pkg', 'foo.py')
        print("Creating junk file at %s" % fpath)
        with open(fpath, 'w') as fh:
            fh.write("testing")
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_MASTER_COMMIT,
                'git_tag': None,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': True,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=%s' % (
                    TEST_GIT_HTTPS_URL, TEST_MASTER_COMMIT, TEST_PROJECT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_local_e_tag(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test(ref=TEST_TAG_COMMIT)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, test_src))
        self._pip_install(path, ['-e', test_src])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_TAG_COMMIT,
                'git_tag': TEST_TAG,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_GIT_HTTPS_URL, TEST_TAG_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_local_e_checkout_tag(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, test_src))
        self._pip_install(path, ['-e', test_src])
        self._git_checkout(test_src, TEST_TAG)
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_TAG_COMMIT,
                'git_tag': TEST_TAG,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_GIT_HTTPS_URL, TEST_TAG_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_local_e_checkout_commit(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, test_src))
        self._pip_install(path, ['-e', test_src])
        self._git_checkout(test_src, TEST_TAG_COMMIT)
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_TAG_COMMIT,
                'git_tag': TEST_TAG,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_GIT_HTTPS_URL, TEST_TAG_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_local_e_multiple_remotes(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, test_src))
        self._git_add_remote(test_src, 'testremote',
                             'https://github.com/jantman/awslimitchecker.git')
        self._pip_install(path, ['-e', test_src])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_MASTER_COMMIT,
                'git_tag': None,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                    'testremote': 'https://github.com/jantman/'
                                  'awslimitchecker.git',
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_GIT_HTTPS_URL, TEST_MASTER_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_sdist(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, TEST_TARBALL_PATH))
        self._pip_install(path, [TEST_TARBALL_PATH])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    @pytest.mark.skipif(
        sys.version_info[0:2] >= (3, 6),
        reason='pip 1.5.4 does not work on py >= 3.6'
    )
    def test_install_sdist_pip154(self, capsys, tmpdir):
        """regression test for issue #55"""
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, TEST_TARBALL_PATH))
        self._pip_install(path, ['--force-reinstall', 'pip==1.5.4'])
        self._pip_install(path, [TEST_TARBALL_PATH])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_bdist_wheel(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, TEST_WHEEL_PATH))
        self._pip_install(path, [TEST_WHEEL_PATH])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_bdist_wheel_no_git_binary(self, capsys, tmpdir):
        e = {x: os.environ[x] for x in os.environ}
        e['GIT_PYTHON_GIT_EXECUTABLE'] = '/tmp/NoSuchFile'
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, TEST_WHEEL_PATH))
        self._pip_install(path, [TEST_WHEEL_PATH])
        actual = self._get_result(self._get_version(path, env=e))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            'git+%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL
            )
        ])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git_fork(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            'git+%s#egg=versionfinder-test-pkg' % (
                TEST_FORK_HTTPS_URL
            )
        ])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git_commit(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_MASTER_COMMIT
            )
        ])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git_tag(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_TAG
            )
        ])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git_branch(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_BRANCH
            )
        ])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git_e(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            '-e',
            'git+%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL
            )
        ])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_MASTER_COMMIT,
                'git_tag': None,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_GIT_HTTPS_URL, TEST_MASTER_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git_e_fork(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            '-e',
            'git+%s#egg=versionfinder-test-pkg' % (
                TEST_FORK_HTTPS_URL
            )
        ])
        self._git_add_remote(
            os.path.join(path, 'src', 'versionfinder-test-pkg'),
            'upstream',
            TEST_GIT_HTTPS_URL
        )
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_MASTER_COMMIT,
                'git_tag': None,
                'git_remotes': {
                    'origin': TEST_FORK_HTTPS_URL,
                    'upstream': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_FORK_HTTPS_URL, TEST_MASTER_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git_e_multiple_remotes(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            '-e',
            'git+%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL
            )
        ])
        p = os.path.join(path, 'src', 'versionfinder-test-pkg')
        self._git_add_remote(p, 'testremote',
                             TEST_FORK_HTTPS_URL)
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_MASTER_COMMIT,
                'git_tag': None,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                    'testremote': TEST_FORK_HTTPS_URL
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_GIT_HTTPS_URL, TEST_MASTER_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git_e_dirty(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            '-e',
            'git+%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL
            )
        ])
        fpath = os.path.join(
            path, 'src', 'versionfinder-test-pkg', 'versionfinder_test_pkg',
            'foo.py'
        )
        print("Creating junk file at %s" % fpath)
        with open(fpath, 'w') as fh:
            fh.write("testing")
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_MASTER_COMMIT,
                'git_tag': None,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': True,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_GIT_HTTPS_URL, TEST_MASTER_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git_e_commit(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            '-e',
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_MASTER_COMMIT
            )
        ])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_MASTER_COMMIT,
                'git_tag': None,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_GIT_HTTPS_URL, TEST_MASTER_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git_e_tag(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            '-e',
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_TAG
            )
        ])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_TAG_COMMIT,
                'git_tag': TEST_TAG,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_GIT_HTTPS_URL, TEST_TAG_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_git_e_branch(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, 'git'))
        self._pip_install(path, [
            '-e',
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_BRANCH
            )
        ])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_BRANCH_COMMIT,
                'git_tag': None,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_GIT_HTTPS_URL, TEST_BRANCH_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_sdist_in_git_repo(self, capsys, tmpdir):
        """regression test for issue #73"""
        path = str(tmpdir)
        self._make_git_repo(path)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, TEST_TARBALL_PATH))
        self._pip_install(path, [TEST_TARBALL_PATH])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_wheel_in_git_repo(self, capsys, tmpdir):
        """regression test for issue #73"""
        path = str(tmpdir)
        self._make_git_repo(path)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, TEST_WHEEL_PATH))
        self._pip_install(path, [TEST_WHEEL_PATH])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected


@pytest.mark.acceptance
class TestSetupPy(AcceptanceHelpers):

    def test_develop(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, test_src))
        with chdir(test_src):
            cmd = [
                os.path.join(path, 'bin', 'python'),
                os.path.join(test_src, 'setup.py'),
                'develop'
            ]
            print_header('running: %s' % ' '.join(cmd))
            output = _check_output(cmd, stderr=subprocess.STDOUT)
            print(output)
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': TEST_MASTER_COMMIT,
                'git_tag': None,
                'git_remotes': {
                    'origin': TEST_GIT_HTTPS_URL,
                },
                'git_is_dirty': False,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'git+%s@%s#egg=versionfinder_test_pkg' % (
                    TEST_GIT_HTTPS_URL, TEST_MASTER_COMMIT
                ),
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, test_src))
        with chdir(test_src):
            cmd = [
                os.path.join(path, 'bin', 'python'),
                os.path.join(test_src, 'setup.py'),
                'install'
            ]
            print_header('running: %s' % ' '.join(cmd))
            output = _check_output(cmd, stderr=subprocess.STDOUT)
            print(output)
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected


@pytest.mark.acceptance
class TestEasyInstall(AcceptanceHelpers):

    def test_install_local_master(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, test_src))
        self._easy_install(path, [test_src])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_sdist(self, capsys, tmpdir):
        """regression test for issue #73"""
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, TEST_TARBALL_PATH))
        self._easy_install(path, [TEST_TARBALL_PATH])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_egg(self, capsys, tmpdir):
        """regression test for issue #73"""
        if TEST_EGG_PATH is None:
            pytest.skip("No egg for python version")
        path = str(tmpdir)
        self._make_venv(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, TEST_EGG_PATH))
        self._easy_install(path, [TEST_TARBALL_PATH])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_local_master_in_git_repo(self, capsys, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._make_git_repo(path)
        test_src = self._git_clone_test()
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, test_src))
        self._easy_install(path, [test_src])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_sdist_in_git_repo(self, capsys, tmpdir):
        """regression test for issue #73"""
        path = str(tmpdir)
        self._make_venv(path)
        self._make_git_repo(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, TEST_TARBALL_PATH))
        self._easy_install(path, [TEST_TARBALL_PATH])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected

    def test_install_egg_in_git_repo(self, capsys, tmpdir):
        """regression test for issue #73"""
        if TEST_EGG_PATH is None:
            pytest.skip("No egg for python version")
        path = str(tmpdir)
        self._make_venv(path)
        self._make_git_repo(path)
        with capsys_disabled(capsys):
            print("\n%s() venv=%s src=%s" % (
                inspect.stack()[0][0].f_code.co_name, path, TEST_EGG_PATH))
        self._easy_install(path, [TEST_TARBALL_PATH])
        actual = self._get_result(self._get_version(path))
        expected = {
            'failed': False,
            'result': {
                'git_commit': None,
                'git_tag': None,
                'git_remotes': None,
                'git_is_dirty': None,
                'pip_version': TEST_VERSION,
                'pip_url': TEST_PROJECT_URL,
                'pip_requirement': 'versionfinder-test-pkg==%s' % TEST_VERSION,
                'pkg_resources_version': TEST_VERSION,
                'pkg_resources_url': TEST_PROJECT_URL,
            }
        }
        assert actual == expected


def get_package(pkg_url):
    """
    Download the package from ``pkg_url`` to a tempdir.

    :param pkg_url: url of the package to download
    :type pkg_url: str
    :return: path to the package on disk
    :rtype: str
    """
    fname = pkg_url.split('/')[-1]
    d = mkdtemp(prefix='pytest-versionfinder')
    p = os.path.join(d, fname)
    r = requests_get(pkg_url)
    assert r.status_code == 200
    with open(p, 'wb') as fh:
        for chunk in r:
            fh.write(chunk)
    return p


# try up to 10 times to get a response that isn't rate-limited
@backoff.on_predicate(backoff.expo,
                      lambda r: r.status_code == 429, max_tries=10)
def requests_get(pkg_url):
    r = requests.get(pkg_url, stream=True)
    return r


def dictdiff(actual, expected, prefix=None):
    s = ''
    keys = set(actual.keys() + expected.keys())
    for k in sorted(keys):
        a = actual.get(k, '<missing>')
        e = expected.get(k, '<missing>')
        if prefix is None:
            k_str = k
        else:
            k_str = prefix + '->' + k
        if isinstance(a, type({})) and isinstance(e, type({})):
            s += dictdiff(a, e, prefix=k)
        else:
            if a != e:
                s += "*%s: actual='%s' expected='%s'\n" % (k_str, a, e)
            else:
                s += "%s: actual='%s' expected='%s'\n" % (k_str, a, e)
    return s


def print_header(s):
    print("%s %s %s" % ("#" * 20, s, "#" * 20))


def strip_unicode(d):
    n = {}
    for k, v in d.items():
        if isinstance(v, type({})):
            n[str(k)] = strip_unicode(v)
        elif v is True or v is False or v is None:
            n[str(k)] = v
        else:
            n[str(k)] = str(v)
    return n
