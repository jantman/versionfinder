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

import pytest
import sys
import os
import subprocess
import shutil

from versionfinder.version import VERSION
from versionfinder.versionfinder import (
    _get_git_commit, _get_git_url, _get_git_tag, _check_output
)

import logging
logger = logging.getLogger(__name__)


@pytest.mark.acceptance
class Test_AGPLVersionChecker_Acceptance(object):
    """
    Long-running acceptance tests for AGPLVersionChecker, which create venvs,
    install the code in them, and test the output
    """

    git_commit = None
    git_tag = None

    def setup_method(self, method):
        os.environ['VERSIONCHECK_DEBUG'] = 'true'
        print("\n")
        self._set_git_config()
        self.current_venv_path = sys.prefix
        self.source_dir = self._get_source_dir()
        self.git_commit = _get_git_commit()
        self.git_tag = _get_git_tag(self.git_commit)
        self.git_url = _get_git_url()
        print({
            'self.source_dir': self.source_dir,
            'self.git_commit': self.git_commit,
            'self.git_tag': self.git_tag,
            'self.git_url': self.git_url,
        })
        print(_check_output([
                'git',
                'show-ref',
                '--tags'
        ]).strip())

    def teardown_method(self, method):
        tag = _get_git_tag(self.git_commit)
        print("\n")
        if tag is not None:
            subprocess.call([
                'git',
                'tag',
                '--delete',
                tag
            ])
        try:
            if 'testremote' in _check_output([
                'git',
                'remote',
                '-v'
            ]):
                print("Removing 'testremote' git remote")
                subprocess.call([
                    'git',
                    'remote',
                    'remove',
                    'testremote'
                ])
        except subprocess.CalledProcessError:
            pass

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

    def _set_git_tag(self, tagname):
        """set a git tag for the current commit"""
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
        self.git_tag = tag
        return tag

    def _make_venv(self, path):
        """
        Create a venv in ``path``. Make sure it exists.

        :param path: filesystem path to directory to make the venv base
        """
        virtualenv = os.path.join(self.current_venv_path, 'bin', 'virtualenv')
        assert os.path.exists(virtualenv) is True, 'virtualenv not found'
        args = [virtualenv, path]
        print("\n" + "#" * 20 + " running: " + ' '.join(args) + "#" * 20)
        res = subprocess.call(args)
        if res == 0:
            print("\n" + "#" * 20 + " DONE: " + ' '.join(args) + "#" * 20)
        else:
            print("\n" + "#" * 20 + " FAILED: " + ' '.join(args) + "#" * 20)
        pypath = os.path.join(path, 'bin', 'python')
        assert os.path.exists(pypath) is True, "does not exist: %s" % pypath

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
        print("\n" + "#" * 20 + " running: " + ' '.join(final_args) + "#" * 20)
        res = subprocess.call(final_args)
        print("\n" + "#" * 20 + " DONE: " + ' '.join(final_args) + "#" * 20)
        assert res == 0

    def _make_git_repo(self, path):
        """create a git repo under path; return the commit"""
        print("creating git repository in %s" % path)
        old_cwd = os.getcwd()
        os.chdir(path)
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
        print("git repository in %s commit: %s" % (path, commit))
        os.chdir(old_cwd)
        return commit

    def _get_alc_version(self, path):
        """
        In the virtualenv at ``path``, run ``awslimitchecker --version`` and
        return the string output.

        :param path: venv base/root path
        :return: version command output
        :rtype: str
        """
        alc = os.path.join(path, 'bin', 'awslimitchecker')
        args = [alc, '--version', '-vv']
        print("\n" + "#" * 20 + " running: " + ' '.join(args) + "#" * 20)
        res = _check_output(args, stderr=subprocess.STDOUT)
        print(res)
        print("\n" + "#" * 20 + " DONE: " + ' '.join(args) + "#" * 20)
        # confirm the git status
        print(self._get_git_status(path))
        # print(self._get_git_status(os.path.dirname(__file__)))
        return res

    def _get_git_status(self, path):
        header = "#" * 20 + " running: git status in: %s " % path + "#" * 20
        oldcwd = os.getcwd()
        os.chdir(path)
        try:
            status = _check_output(['git', 'status'],
                                   stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            status = ''
        os.chdir(oldcwd)
        footer = "#" * 20 + " DONE: git status " + "#" * 20
        if status == '':
            return "\n# git status exited non-0\n"
        return "\n" + header + "\n" + status + "\n" + footer + "\n"

    def _make_package(self, pkg_type, test_tmp_dir):
        """
        Use setup.py in the current (tox) virtualenv to build a package
        of the current project, of the specified ``pkg_type`` (sdist|bdist|
        bdist_wheel). Return the absolute path to the created archive/
        package.

        :param pkg_type: str, type of package to create
        :param test_tmp_dir: str, temporary dir for this test
        :return: absolute path to the package file
        :rtype: str
        """
        pkgdir = os.path.join(test_tmp_dir, 'pkg')
        if os.path.exists(pkgdir):
            print("removing: %s" % pkgdir)
            shutil.rmtree(pkgdir)
        args = [
            sys.executable,
            os.path.join(self.source_dir, 'setup.py'),
            pkg_type,
            '--dist-dir',
            pkgdir
        ]
        assert os.path.exists(
            args[0]) is True, "path does not exist: %s" % args[0]
        assert os.path.exists(
            args[1]) is True, "path does not exist: %s" % args[1]
        print("\n" + "#" * 20 + " running: " + ' '.join(args) + "#" * 20)
        print("# cwd: %s\n" % os.getcwd())
        try:
            subprocess.call(args)
        except Exception as ex:
            print("\nFAILED:")
            print(ex)
            print("\n")
        print("\n" + "#" * 20 + " DONE: " + ' '.join(args) + "#" * 20)
        assert os.path.exists(
            args[4]) is True, "path does not exist: %s" % args[4]
        files = os.listdir(pkgdir)
        assert len(files) == 1
        fpath = os.path.join(pkgdir, files[0])
        assert os.path.exists(fpath) is True
        return fpath

    def _check_git_pushed(self):
        """
        returns a trinary:
        0 - up-to-date and clean
        1 - not equal to origin
        2 - dirty

        :return: int
        """
        status = _check_output([
            'git',
            'status',
            '-u'
        ]).strip()
        if ('Your branch is up-to-date with' not in status and
                'HEAD detached at' not in status and
                '# Not currently on any branch' not in status):
            print("\ngit status -u:\n" + status + "\n")
            return 1
        if 'nothing to commit' not in status:
            print("\ngit status -u:\n" + status + "\n")
            return 2
        return 0

    ################
    # Actual Tests #
    ################

    def test_install_local(self, tmpdir):
        path = str(tmpdir)
        # make the venv
        self._make_venv(path)
        self._pip_install(path, [self.source_dir])
        version_output = self._get_alc_version(path)
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v=VERSION,
            u='https://github.com/jantman/awslimitchecker'
        )
        assert expected in version_output

    def test_install_local_e(self, tmpdir):
        path = str(tmpdir)
        # make the venv
        self._make_venv(path)
        self._pip_install(path, ['-e', self.source_dir])
        version_output = self._get_alc_version(path)
        expected_commit = self.git_commit
        if self._check_git_pushed() != 0:
            expected_commit += '*'
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v='%s@%s' % (VERSION, expected_commit),
            u=self.git_url
        )
        assert expected in version_output

    def test_install_local_e_dirty(self, tmpdir):
        path = str(tmpdir)
        # make the venv
        self._make_venv(path)
        self._pip_install(path, ['-e', self.source_dir])
        fpath = os.path.join(self.source_dir, 'awslimitchecker', 'testfile')
        print("Creating junk file at %s" % fpath)
        with open(fpath, 'w') as fh:
            fh.write("testing")
        version_output = self._get_alc_version(path)
        print("Removing junk file at %s" % fpath)
        os.unlink(fpath)
        expected_commit = self.git_commit + '*'
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v='%s@%s' % (VERSION, expected_commit),
            u=self.git_url
        )
        assert expected in version_output

    def test_install_local_e_tag(self, tmpdir):
        path = str(tmpdir)
        # make the venv
        self._set_git_tag('versioncheck')
        self._make_venv(path)
        self._pip_install(path, ['-e', self.source_dir])
        version_output = self._get_alc_version(path)
        expected_tag = 'versioncheck'
        if self._check_git_pushed() != 0:
            expected_tag += '*'
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v='%s@%s' % (VERSION, expected_tag),
            u=self.git_url
        )
        assert expected in version_output

    def test_install_local_e_multiple_remotes(self, tmpdir):
        path = str(tmpdir)
        url = self.git_url
        # make the venv
        subprocess.call([
                'git',
                'remote',
                'add',
                'testremote',
                'https://github.com/jantman/awslimitchecker.git'
            ])
        self._make_venv(path)
        self._pip_install(path, ['-e', self.source_dir])
        version_output = self._get_alc_version(path)
        expected_commit = self.git_commit
        if self._check_git_pushed() != 0:
            expected_commit += '*'
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v='%s@%s' % (VERSION, expected_commit),
            u=url
        )
        assert expected in version_output

    def test_install_sdist(self, tmpdir):
        path = str(tmpdir)
        # make the venv
        self._make_venv(path)
        # build the sdist
        pkg_path = self._make_package('sdist', path)
        # install ALC in it
        self._pip_install(path, [pkg_path])
        version_output = self._get_alc_version(path)
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v=VERSION,
            u='https://github.com/jantman/awslimitchecker'
        )
        assert expected in version_output

    def test_install_sdist_pip154(self, tmpdir):
        """regression test for issue #55"""
        path = str(tmpdir)
        # make the venv
        self._make_venv(path)
        # build the sdist
        pkg_path = self._make_package('sdist', path)
        # ensure pip at 1.5.4
        self._pip_install(path, ['--force-reinstall', 'pip==1.5.4'])
        # install ALC in it
        self._pip_install(path, [pkg_path])
        version_output = self._get_alc_version(path)
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v=VERSION,
            u='https://github.com/jantman/awslimitchecker'
        )
        assert expected in version_output

    def test_install_bdist_wheel(self, tmpdir):
        path = str(tmpdir)
        # make the venv
        self._make_venv(path)
        # build the sdist
        pkg_path = self._make_package('bdist_wheel', path)
        # install ALC in it
        self._pip_install(path, [pkg_path])
        version_output = self._get_alc_version(path)
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v=VERSION,
            u='https://github.com/jantman/awslimitchecker'
        )
        assert expected in version_output

    # this doesn't work on PRs, because we can't check out the hash
    @pytest.mark.skipif(os.environ.get('TRAVIS_PULL_REQUEST', 'false') !=
                        'false', reason='git tests dont work on PRs')
    def test_install_git(self, tmpdir):
        # https://pip.pypa.io/en/latest/reference/pip_install.html#git
        status = self._check_git_pushed()
        assert status != 1, "git clone not equal to origin"
        assert status != 2, 'git clone is dirty'
        commit = _get_git_commit()
        path = str(tmpdir)
        # make the venv
        self._make_venv(path)
        self._pip_install(path, [
            'git+https://github.com/jantman/awslimitchecker.git'
            '@{c}#egg=awslimitchecker'.format(c=commit)
        ])
        version_output = self._get_alc_version(path)
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v=VERSION,
            u='https://github.com/jantman/awslimitchecker'
        )
        assert expected in version_output

    def get_commit_or_tag(self):
        """return tag if there is one, else commit"""
        commit = _get_git_commit()
        tag = _get_git_tag(commit)
        print("Found commit=%s, tag=%s" % (commit, tag))
        if tag is not None:
            return tag
        return commit

    # this doesn't work on PRs, because we can't check out the hash
    @pytest.mark.skipif(os.environ.get('TRAVIS_PULL_REQUEST', 'false') !=
                        'false', reason='git tests dont work on PRs')
    def test_install_git_e(self, tmpdir):
        # https://pip.pypa.io/en/latest/reference/pip_install.html#git
        print("### execute: git fetch --tags")
        print(_check_output(['git', 'fetch', '--tags']))
        print("### fetched DONE")
        status = self._check_git_pushed()
        assert status != 1, "git clone not equal to origin"
        assert status != 2, 'git clone is dirty'
        commit = self.get_commit_or_tag()
        path = str(tmpdir)
        print(_check_output([
            'git',
            'show-ref',
            '--tags'
        ]).strip())
        print("# commit=%s path=%s" % (commit, path))
        # make the venv
        self._make_venv(path)
        self._pip_install(path, [
            '-e',
            'git+https://github.com/jantman/awslimitchecker.git'
            '@{c}#egg=awslimitchecker'.format(c=commit)
        ])
        version_output = self._get_alc_version(path)
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v='%s@%s' % (VERSION, commit),
            u='https://github.com/jantman/awslimitchecker.git'
        )
        assert expected in version_output

    # this doesn't work on PRs, because we can't check out the hash
    @pytest.mark.skipif(os.environ.get('TRAVIS_PULL_REQUEST', 'false') !=
                        'false', reason='git tests dont work on PRs')
    def test_install_git_e_dirty(self, tmpdir):
        # https://pip.pypa.io/en/latest/reference/pip_install.html#git
        print("### execute: git fetch --tags")
        print(_check_output(['git', 'fetch', '--tags']))
        print("### fetched DONE")
        status = self._check_git_pushed()
        assert status != 1, "git clone not equal to origin"
        assert status != 2, 'git clone is dirty'
        commit = self.get_commit_or_tag()
        path = str(tmpdir)
        print(_check_output([
            'git',
            'show-ref',
            '--tags'
        ]).strip())
        print("# commit=%s path=%s" % (commit, path))
        # make the venv
        self._make_venv(path)
        self._pip_install(path, [
            '-e',
            'git+https://github.com/jantman/awslimitchecker.git'
            '@{c}#egg=awslimitchecker'.format(c=commit)
        ])
        fpath = os.path.join(path, 'src', 'awslimitchecker', 'testfile')
        print("Creating junk file at %s" % fpath)
        with open(fpath, 'w') as fh:
            fh.write("testing")
        version_output = self._get_alc_version(path)
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v='%s@%s*' % (VERSION, commit),
            u='https://github.com/jantman/awslimitchecker.git'
        )
        assert expected in version_output

    def test_install_sdist_in_git_repo(self, tmpdir):
        """regression test for issue #73"""
        path = str(tmpdir)
        # setup a git repo in tmpdir
        self._make_git_repo(path)
        # make the venv
        self._make_venv(path)
        # build the sdist
        pkg_path = self._make_package('sdist', path)
        # install ALC in it
        self._pip_install(path, [pkg_path])
        version_output = self._get_alc_version(path)
        expected = 'awslimitchecker {v} (see <{u}> for source code)'.format(
            v=VERSION,
            u='https://github.com/jantman/awslimitchecker'
        )
        assert expected in version_output
