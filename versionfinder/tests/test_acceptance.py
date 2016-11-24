"""
versionfinder/tests/test_acceptance.py

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

"""
@TODO:

Install methods should include:
- install from a fork
"""

import pytest
import sys
import os
import subprocess
import shutil
import json
import requests
from tempfile import mkdtemp

from versionfinder.version import VERSION
from versionfinder.versionfinder import (
    _get_git_commit, _get_git_url, _get_git_tag, _check_output, chdir
)

import logging
logger = logging.getLogger(__name__)

TEST_PROJECT = 'versionfinder_test_pkg'
TEST_GIT_HTTPS_URL = 'https://github.com/jantman/versionfinder-test-pkg.git'
TEST_PROJECT_URL = 'https://github.com/jantman/versionfinder-test-pkg'
TEST_VERSION = '0.2.1'
TEST_TAG = '0.2.1'
TEST_TAG_COMMIT = 'e6a8778111043d0d0172281f3a33b0c00bd239b9'
TEST_MASTER_COMMIT = '2665f9969af060a876db4dc3b030dabc15034c41'
TEST_BRANCH = 'testbranch'
TEST_BRANCH_COMMIT = '1b289fdf7e187cb8a67c8e1dd9aafeb54c389c8f'
TEST_TARBALL = 'https://github.com/jantman/versionfinder-test-pkg/releases/' \
               'download/0.2.1/versionfinder_test_pkg-0.2.1.tar.gz'
TEST_WHEEL = 'https://github.com/jantman/versionfinder-test-pkg/releases/' \
             'download/0.2.1/versionfinder_test_pkg-0.2.1-py2.py3-none-any.whl'


def print_header(s):
    print("%s %s %s" % ("#" * 20, s, "#" * 20))


@pytest.mark.acceptance
class TestAcceptance(object):
    """
    Long-running acceptance tests for VersionFinder, which create venvs,
    install the code in them, and test the output
    """

    def setup_method(self, method):
        os.environ['VERSIONCHECK_DEBUG'] = 'true'
        print("\n")
        self._set_git_config()
        self.current_venv_path = sys.prefix
        self.source_dir = self._get_source_dir()
        self.test_tarball = self._get_package(TEST_TARBALL)
        self.test_wheel = self._get_package(TEST_WHEEL)

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
            subprocess.call([
                'git',
                'config',
                'user.email',
                'travisci@jasonantman.com'
            ])
            print("Set git config user.email")
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
            subprocess.call([
                'git',
                'config',
                'user.name',
                'travisci'
            ])
            print("Set git config user.name")

    def _set_git_tag(self, path, tagname):
        """set a git tag for the current commit"""
        with chdir(path):
            tag = _get_git_tag(self.git_commit)
            if tag != tagname:
                print("Creating git tag 'versiontest' of %s" % self.git_commit)
                subprocess.call([
                    'git',
                    'tag',
                    '-a',
                    '-m',
                    tagname,
                    tagname
                ])
                tag = _get_git_tag(self.git_commit)
            print("Source git tag: %s" % tag)
        return tag

    def _git_add_commit(self, path, commit_msg):
        """
        git add -A and git commit -m commit_msg in ``path``.
        """
        print_header('_git_add_commit(%s, %s)' % (path, commit_msg))
        with chdir(path):
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
        res = subprocess.call(args)
        if res == 0:
            print_header("DONE")
        else:
            print_header('FAILED')
        pypath = os.path.join(path, 'bin', 'python')
        assert os.path.exists(pypath) is True, "does not exist: %s" % pypath
        # install our source in the venv
        self._pip_install(path, [self.source_dir])

    def _pip_install(self, path, args):
        """
        In the virtualenv at ``path``, run ``pip install [args]``.

        :param path: venv base/root path
        :param args: ``pip install`` arguments
        """
        pip = os.path.join(path, 'bin', 'pip')
        # get pip version
        res = subprocess.call([pip, '--version'])
        assert res == 0
        # install ALC in it
        final_args = [pip, 'install']
        final_args.extend(args)
        print_header("_pip_install() running: " + ' '.join(final_args))
        res = subprocess.call(final_args)
        print_header('DONE')
        assert res == 0

    def _make_git_repo(self, path):
        """create a git repo under path; return the commit"""
        print_header("creating git repository in %s" % path)
        with chdir(path):
            res = subprocess.call(['git', 'init', '.'])
            assert res == 0
            with open('foo', 'w') as fh:
                fh.write('foo')
            res = subprocess.call(['git', 'add', 'foo'])
            assert res == 0
            self._set_git_config(set_in_travis=True)
            res = subprocess.call(['git', 'commit', '-m', 'foo'])
            assert res == 0
            commit = _get_git_commit()
            print_header("git repository in %s commit: %s" % (path, commit))
        return commit

    def _get_version(self, path):
        """
        In the virtualenv at ``path``, run ``versionfinder-test`` and
        return the JSON-decoded output.

        :param path: venv base/root path
        :type path: str
        :return: versionfinder-test command output
        :rtype: dict
        """
        args = [os.path.join(path, 'bin', 'versionfinder-test')]
        print_header("_get_version() running: " + ' '.join(args))
        res = _check_output(args)
        print(res)
        print('DONE')
        j = json.loads(res.strip())
        return strip_unicode(j)

    def _git_checkout(self, path, ref):
        cmd = ['git', 'checkout', '-f', ref]
        print_header("_git_checkout() running: '%s' in: %s" % (
            ' '.join(cmd), path))
        with chdir(path):
            output = _check_output(cmd, stderr=subprocess.STDOUT)
            print(output)
        print_header('DONE')

    def _git_clone_test(self, ref=None):
        """
        Clone TEST_GIT_HTTPS_URL to a local temporary directory; checkout
        the specified ref.

        :return: path to git clone
        :rtype: str
        """
        d = mkdtemp(prefix='pytest-versionfinder')
        print_header('_git_clone_test(%s) cloning %s into %s' % (
            ref, TEST_GIT_HTTPS_URL, d))
        output = _check_output(
            ['git', 'clone', TEST_GIT_HTTPS_URL, d],
            stderr=subprocess.STDOUT
        )
        print(output)
        print_header('DONE')
        if ref is not None:
            self._git_checkout(d, ref)
        return d

    def _get_package(self, pkg_url):
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
        r = requests.get(pkg_url, stream=True)
        assert r.status_code == 200
        with open(p, 'wb') as fh:
            for chunk in r:
                fh.write(chunk)
        return p

    def _expected_dict(self, tag, commit, origin=None, dirty=None):
        """
        Build a dict of the expected return values for a given install method.

        :return: expected dict
        :rtype: dict
        """
        d = {}
        for k in ["entrypoint", "entrypoint_other_file", "nested_check_file",
                  "nested_class_check", "nested_class_check_file",
                  "nested_file_check", "top_level_class_check",
                  "top_level_class_check_file", "top_level_file_check",
                  "top_level_file_check_file"]:
            d[k] = {
                'failed': False,
                'result': {
                    'git_commit': commit,
                    'git_tag': tag,
                    'git_origin': origin,
                    'git_is_dirty': dirty,
                    'version': TEST_VERSION,
                    'url': TEST_PROJECT_URL,
                }
            }
        return d

    ################
    # Actual Tests #
    ################

    def test_install_local_master(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        self._pip_install(path, [test_src])
        actual = self._get_version(path)
        expected = self._expected_dict(None, None)
        assert actual == expected

    def test_install_local_e(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        self._pip_install(path, ['-e', test_src])
        actual = self._get_version(path)
        expected = self._expected_dict(None, TEST_MASTER_COMMIT)
        assert actual == expected

    def test_install_local_e_dirty(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        self._pip_install(path, ['-e', test_src])
        fpath = os.path.join(test_src, 'versionfinder_test_pkg', 'foo.py')
        print("Creating junk file at %s" % fpath)
        with open(fpath, 'w') as fh:
            fh.write("testing")
        actual = self._get_version(path)
        expected = self._expected_dict(None, TEST_MASTER_COMMIT, dirty=True)
        assert sorted(actual) == sorted(expected)

    def test_install_local_e_tag(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        self._pip_install(path, ['-e', test_src])
        fpath = os.path.join(test_src, 'versionfinder_test_pkg', 'foo.py')
        print("Creating junk file at %s" % fpath)
        with open(fpath, 'w') as fh:
            fh.write("testing")
        commit = self._git_add_commit(test_src, 'versioncheck tag')
        self._set_git_tag(test_src, 'versioncheck')
        actual = self._get_version(path)
        expected = self._expected_dict('versioncheck', TEST_MASTER_COMMIT)
        assert sorted(actual) == sorted(expected)

    def test_install_local_e_checkout_tag(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        self._pip_install(path, ['-e', test_src])
        self._git_checkout(test_src, TEST_TAG)
        actual = self._get_version(path)
        expected = self._expected_dict(TEST_TAG, TEST_TAG_COMMIT)
        assert sorted(actual) == sorted(expected)

    def test_install_local_e_checkout_commit(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        self._pip_install(path, ['-e', test_src])
        self._git_checkout(test_src, TEST_TAG_COMMIT)
        actual = self._get_version(path)
        expected = self._expected_dict(TEST_TAG, TEST_TAG_COMMIT)
        assert sorted(actual) == sorted(expected)

    def test_install_local_e_multiple_remotes(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with chdir(test_src):
            subprocess.call([
                'git',
                'remote',
                'add',
                'testremote',
                'https://github.com/jantman/awslimitchecker.git'
            ])
        self._pip_install(path, ['-e', test_src])
        actual = self._get_version(path)
        expected = self._expected_dict(
            None, TEST_MASTER_COMMIT,
            origin='https://github.com/jantman/awslimitchecker.git')
        assert sorted(actual) == sorted(expected)

    def test_install_sdist(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, [self.test_tarball])
        actual = self._get_version(path)
        expected = self._expected_dict(None, None)
        assert sorted(actual) == sorted(expected)

    def test_install_sdist_pip154(self, tmpdir):
        """regression test for issue #55"""
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, ['--force-reinstall', 'pip==1.5.4'])
        self._pip_install(path, [self.test_tarball])
        actual = self._get_version(path)
        expected = self._expected_dict(None, None)
        assert sorted(actual) == sorted(expected)

    def test_install_bdist_wheel(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, [self.test_wheel])
        actual = self._get_version(path)
        expected = self._expected_dict(None, None)
        assert sorted(actual) == sorted(expected)

    def test_install_git(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, [
            'git+%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL
            )
        ])
        actual = self._get_version(path)
        expected = self._expected_dict(None, TEST_MASTER_COMMIT)
        assert sorted(actual) == sorted(expected)

    def test_install_git_commit(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, [
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_MASTER_COMMIT
            )
        ])
        actual = self._get_version(path)
        expected = self._expected_dict(None, TEST_MASTER_COMMIT)
        assert sorted(actual) == sorted(expected)

    def test_install_git_tag(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, [
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_TAG
            )
        ])
        actual = self._get_version(path)
        expected = self._expected_dict(TEST_TAG, TEST_TAG_COMMIT)
        assert sorted(actual) == sorted(expected)

    def test_install_git_branch(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, [
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_BRANCH
            )
        ])
        actual = self._get_version(path)
        expected = self._expected_dict(None, TEST_BRANCH_COMMIT)
        assert sorted(actual) == sorted(expected)

    def test_install_git_e(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, [
            '-e',
            'git+%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL
            )
        ])
        actual = self._get_version(path)
        expected = self._expected_dict(None, TEST_MASTER_COMMIT,
                                       origin=TEST_GIT_HTTPS_URL)
        assert sorted(actual) == sorted(expected)

    def test_install_git_e_multiple_remotes(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, [
            '-e',
            'git+%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL
            )
        ])
        p = os.path.join(path, 'src', 'versionfinder-test-pkg')
        with chdir(p):
            subprocess.call([
                'git',
                'remote',
                'add',
                'testremote',
                'https://github.com/jantman/awslimitchecker.git'
            ])
        actual = self._get_version(path)
        expected = self._expected_dict(None, TEST_MASTER_COMMIT,
                                       origin=TEST_GIT_HTTPS_URL)
        assert sorted(actual) == sorted(expected)

    def test_install_git_e_dirty(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
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
        actual = self._get_version(path)
        expected = self._expected_dict(None, TEST_MASTER_COMMIT, dirty=True,
                                       origin=TEST_GIT_HTTPS_URL)
        assert sorted(actual) == sorted(expected)

    def test_install_git_e_commit(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, [
            '-e',
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_MASTER_COMMIT
            )
        ])
        actual = self._get_version(path)
        expected = self._expected_dict(None, TEST_MASTER_COMMIT,
                                       origin=TEST_GIT_HTTPS_URL)
        assert sorted(actual) == sorted(expected)

    def test_install_git_e_tag(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, [
            '-e',
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_TAG
            )
        ])
        actual = self._get_version(path)
        expected = self._expected_dict(TEST_TAG, TEST_TAG_COMMIT,
                                       origin=TEST_GIT_HTTPS_URL)
        assert sorted(actual) == sorted(expected)

    def test_install_git_e_branch(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        self._pip_install(path, [
            '-e',
            'git+%s@%s#egg=versionfinder-test-pkg' % (
                TEST_GIT_HTTPS_URL,
                TEST_BRANCH
            )
        ])
        actual = self._get_version(path)
        expected = self._expected_dict(None, TEST_BRANCH_COMMIT,
                                       origin=TEST_GIT_HTTPS_URL)
        assert sorted(actual) == sorted(expected)

    def test_install_sdist_in_git_repo(self, tmpdir):
        """regression test for issue #73"""
        path = str(tmpdir)
        self._make_git_repo(path)
        self._make_venv(path)
        self._pip_install(path, [self.test_tarball])
        actual = self._get_version(path)
        expected = self._expected_dict(None, None)
        assert sorted(actual) == sorted(expected)

    def test_install_wheel_in_git_repo(self, tmpdir):
        """regression test for issue #73"""
        path = str(tmpdir)
        self._make_git_repo(path)
        self._make_venv(path)
        self._pip_install(path, [self.test_wheel])
        actual = self._get_version(path)
        expected = self._expected_dict(None, None)
        assert sorted(actual) == sorted(expected)

    def test_install_setuppy_develop(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with chdir(test_src):
            cmd = [
                os.path.join(path, 'bin', 'python'),
                os.path.join(test_src, 'setup.py'),
                'develop'
            ]
            print_header('running: %s' % ' '.join(cmd))
            output = _check_output(cmd, stderr=subprocess.STDOUT)
            print(output)
        actual = self._get_version(path)
        expected = self._expected_dict(None, None)
        assert sorted(actual) == sorted(expected)

    def test_install_setuppy_install(self, tmpdir):
        path = str(tmpdir)
        self._make_venv(path)
        test_src = self._git_clone_test()
        with chdir(test_src):
            cmd = [
                os.path.join(path, 'bin', 'python'),
                os.path.join(test_src, 'setup.py'),
                'install'
            ]
            print_header('running: %s' % ' '.join(cmd))
            output = _check_output(cmd, stderr=subprocess.STDOUT)
            print(output)
        actual = self._get_version(path)
        expected = self._expected_dict(None, None)
        assert sorted(actual) == sorted(expected)

def strip_unicode(d):
    n = {}
    for k, v in d.iteritems():
        if isinstance(v, type({})):
            n[str(k)] = strip_unicode(v)
        elif v is True or v is False or v is None:
            n[str(k)] = v
        else:
            n[str(k)] = str(v)
    return n
