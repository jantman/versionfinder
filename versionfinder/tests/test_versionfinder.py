"""
versionfinder/tests/test_versionfinder.py

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
import subprocess
from textwrap import dedent
from pip._vendor.packaging.version import Version

from versionfinder.versionfinder import (
    _get_git_commit, _get_git_remotes, _get_git_tag, _check_output, DEVNULL,
    VersionFinder, chdir
)
from versionfinder.versioninfo import VersionInfo

import logging
logger = logging.getLogger(__name__)

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import patch, call, DEFAULT, Mock, PropertyMock
else:
    from unittest.mock import patch, call, DEFAULT, Mock, PropertyMock

pbm = 'versionfinder.versionfinder'
pb = '%s.VersionFinder' % pbm


class BaseTest(object):

    def setup_method(self, _):
        self.cls = VersionFinder('foo', package_file='/foo/bar/baz.py')


class TestInit(object):

    def test_init(self):
        m_pip_logger = Mock()
        with patch('%s.inspect.stack' % pbm, autospec=True) as m_stack:
            with patch('%s.logger' % pbm, autospec=True) as m_logger:
                with patch('%s.logging.getLogger' % pbm,
                           autospec=True) as m_log_pip:
                    m_log_pip.return_value = m_pip_logger
                    cls = VersionFinder('foobar',
                                        package_file='/foo/bar/baz.py')
        assert m_stack.mock_calls == []
        assert cls.package_name == 'foobar'
        assert cls.package_file == '/foo/bar/baz.py'
        assert cls.package_dir == '/foo/bar'
        assert m_logger.mock_calls == [
            call.setLevel(logging.CRITICAL),
            call.debug('Finding package version for: %s', 'foobar'),
            call.debug('Explicit package file: %s', '/foo/bar/baz.py'),
            call.debug('package_dir: /foo/bar')
        ]
        assert m_log_pip.mock_calls == [call('pip')]
        assert m_pip_logger.mock_calls == [call.setLevel(logging.CRITICAL)]

    def test_init_log_true(self):
        m_pip_logger = Mock()
        with patch('%s.inspect.stack' % pbm, autospec=True) as m_stack:
            with patch('%s.logger' % pbm, autospec=True) as m_logger:
                with patch('%s.logging.getLogger' % pbm,
                           autospec=True) as m_log_pip:
                    m_log_pip.return_value = m_pip_logger
                    cls = VersionFinder('foobar', log=True,
                                        package_file='/foo/bar/baz.py')
        assert m_stack.mock_calls == []
        assert cls.package_name == 'foobar'
        assert cls.package_file == '/foo/bar/baz.py'
        assert cls.package_dir == '/foo/bar'
        assert m_logger.mock_calls == [
            call.debug('Finding package version for: %s', 'foobar'),
            call.debug('Explicit package file: %s', '/foo/bar/baz.py'),
            call.debug('package_dir: /foo/bar')
        ]
        assert m_log_pip.mock_calls == []
        assert m_pip_logger.mock_calls == []

    def test_init_no_file_no_frame(self):
        m_frame = Mock()
        type(m_frame).filename = '/tmp/foo.py'
        m_stack_frame = Mock()
        with patch('%s.inspect.stack' % pbm, autospec=True) as m_stack:
            with patch('%s.inspect.getframeinfo' % pbm) as m_get_frame:
                m_stack.return_value = [None, [m_stack_frame]]
                m_get_frame.return_value = m_frame
                cls = VersionFinder('foobar')
        assert m_stack.mock_calls == [call()]
        assert m_get_frame.mock_calls == [call(m_stack_frame)]
        assert cls.package_name == 'foobar'
        assert cls.package_file == '/tmp/foo.py'
        assert cls.package_dir == '/tmp'

    def test_init_no_file(self):
        m_frame = Mock()
        type(m_frame).filename = '/tmp/foo.py'
        m_stack_frame = Mock()
        with patch('%s.inspect.stack' % pbm, autospec=True) as m_stack:
            with patch('%s.inspect.getframeinfo' % pbm) as m_get_frame:
                m_stack.return_value = [None, []]
                m_get_frame.return_value = m_frame
                cls = VersionFinder('foobar', caller_frame=m_stack_frame)
        assert m_stack.mock_calls == []
        assert m_get_frame.mock_calls == [call(m_stack_frame)]
        assert cls.package_name == 'foobar'
        assert cls.package_file == '/tmp/foo.py'
        assert cls.package_dir == '/tmp'


class TestFindPackageVersion(BaseTest):

    def test_git_notag(self):
        with patch.multiple(
                pb,
                autospec=True,
                _find_git_info=DEFAULT,
                _find_pip_info=DEFAULT,
                _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'remotes': {'origin': 'git+https://foo'},
                'tag': None,
                'commit': '12345678',
                'dirty': False
            }
            mocks['_find_pip_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pip',
                'foo': None
            }
            mocks['_find_pkg_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pkg_resources'
            }
            with patch('%s._git_repo_path' % pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = '/git/repo/.git'
                res = self.cls.find_package_version()
        assert res.as_dict == VersionInfo(
            pip_version='1.2.3',
            pip_url='http://my.package.url/pip',
            pkg_resources_version='1.2.3',
            pkg_resources_url='http://my.package.url/pkg_resources',
            git_commit='12345678',
            git_is_dirty=False,
            git_remotes={'origin': 'git+https://foo'}
        ).as_dict
        assert mocks['_find_git_info'].mock_calls == [
            call(self.cls, '/git/repo/.git')
        ]
        assert mocks['_find_pip_info'].mock_calls == [call(self.cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(self.cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_git_notag_dirty(self):
        with patch.multiple(
                pb,
                autospec=True,
                _find_git_info=DEFAULT,
                _find_pip_info=DEFAULT,
                _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'remotes': {'origin': 'git+https://foo'},
                'tag': None,
                'commit': '12345678',
                'dirty': True
            }
            mocks['_find_pip_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pip'
            }
            mocks['_find_pkg_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pkg_resources'
            }
            with patch('%s._git_repo_path' % pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = '/git/repo/.git'
                res = self.cls.find_package_version()
        assert res.as_dict == VersionInfo(
            pip_version='1.2.3',
            pip_url='http://my.package.url/pip',
            pkg_resources_version='1.2.3',
            pkg_resources_url='http://my.package.url/pkg_resources',
            git_commit='12345678',
            git_is_dirty=True,
            git_remotes={'origin': 'git+https://foo'}
        ).as_dict
        assert mocks['_find_git_info'].mock_calls == [
            call(self.cls, '/git/repo/.git')
        ]
        assert mocks['_find_pip_info'].mock_calls == [call(self.cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(self.cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_git_tag(self):
        with patch.multiple(
                pb,
                autospec=True,
                _find_git_info=DEFAULT,
                _find_pip_info=DEFAULT,
                _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'remotes': {'origin': 'git+https://foo'},
                'tag': 'mytag',
                'commit': '12345678',
                'dirty': False,
                'foo': None
            }
            mocks['_find_pip_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pip'
            }
            mocks['_find_pkg_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pkg_resources'
            }
            with patch('%s._git_repo_path' % pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = '/git/repo/.git'
                res = self.cls.find_package_version()
        assert res.as_dict == VersionInfo(
            pip_version='1.2.3',
            pip_url='http://my.package.url/pip',
            pkg_resources_version='1.2.3',
            pkg_resources_url='http://my.package.url/pkg_resources',
            git_commit='12345678',
            git_is_dirty=False,
            git_tag='mytag',
            git_remotes={'origin': 'git+https://foo'}
        ).as_dict
        assert mocks['_find_git_info'].mock_calls == [
            call(self.cls, '/git/repo/.git')
        ]
        assert mocks['_find_pip_info'].mock_calls == [call(self.cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(self.cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_git_tag_dirty(self):
        with patch.multiple(
                pb,
                autospec=True,
                _find_git_info=DEFAULT,
                _find_pip_info=DEFAULT,
                _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'remotes': {'origin': 'git+https://foo'},
                'tag': 'mytag',
                'commit': '12345678',
                'dirty': True
            }
            mocks['_find_pip_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pip'
            }
            mocks['_find_pkg_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pkg_resources'
            }
            with patch('%s._git_repo_path' % pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = '/git/repo/.git'
                res = self.cls.find_package_version()
        assert res.as_dict == VersionInfo(
            pip_version='1.2.3',
            pip_url='http://my.package.url/pip',
            pkg_resources_version='1.2.3',
            pkg_resources_url='http://my.package.url/pkg_resources',
            git_commit='12345678',
            git_is_dirty=True,
            git_tag='mytag',
            git_remotes={'origin': 'git+https://foo'}
        ).as_dict
        assert mocks['_find_git_info'].mock_calls == [
            call(self.cls, '/git/repo/.git')
        ]
        assert mocks['_find_pip_info'].mock_calls == [call(self.cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(self.cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_pkg_res_exception(self):

        def se_exception():
            raise Exception("some exception")

        with patch.multiple(
                pb,
                autospec=True,
                _find_git_info=DEFAULT,
                _find_pip_info=DEFAULT,
                _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'remotes': {'origin': 'git+https://foo'},
                'tag': None,
                'commit': '12345678',
                'dirty': False
            }
            mocks['_find_pip_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pip'
            }
            mocks['_find_pkg_info'].side_effect = se_exception
            with patch('%s._git_repo_path' % pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = '/git/repo/.git'
                res = self.cls.find_package_version()
        assert res.as_dict == VersionInfo(
            pip_version='1.2.3',
            pip_url='http://my.package.url/pip',
            git_commit='12345678',
            git_is_dirty=False,
            git_remotes={'origin': 'git+https://foo'}
        ).as_dict
        assert mocks['_find_git_info'].mock_calls == [
            call(self.cls, '/git/repo/.git')
        ]
        assert mocks['_find_pip_info'].mock_calls == [call(self.cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(self.cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_pip_exception(self):

        def se_exception():
            raise Exception("some exception")

        with patch.multiple(
                pb,
                autospec=True,
                _find_git_info=DEFAULT,
                _find_pip_info=DEFAULT,
                _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'remotes': {'origin': 'git+https://foo'},
                'tag': None,
                'commit': '12345678',
                'dirty': False
            }
            mocks['_find_pip_info'].side_effect = se_exception
            mocks['_find_pkg_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pkg_resources'
            }
            with patch('%s._git_repo_path' % pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = '/git/repo/.git'
                res = self.cls.find_package_version()
        assert res.as_dict == VersionInfo(
            pkg_resources_version='1.2.3',
            pkg_resources_url='http://my.package.url/pkg_resources',
            git_commit='12345678',
            git_is_dirty=False,
            git_remotes={'origin': 'git+https://foo'}
        ).as_dict
        assert mocks['_find_git_info'].mock_calls == [
            call(self.cls, '/git/repo/.git')
        ]
        assert mocks['_find_pip_info'].mock_calls == [call(self.cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(self.cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_no_git(self):

        with patch.multiple(
                pb,
                autospec=True,
                _find_git_info=DEFAULT,
                _find_pip_info=DEFAULT,
                _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'remotes': {},
                'tag': None,
                'commit': None,
                'dirty': None,
            }
            mocks['_find_pip_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pip'
            }
            mocks['_find_pkg_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pkg_resources'
            }
            with patch('%s._git_repo_path' % pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = None
                res = self.cls.find_package_version()
        assert res.as_dict == VersionInfo(
            pip_version='1.2.3',
            pip_url='http://my.package.url/pip',
            pkg_resources_version='1.2.3',
            pkg_resources_url='http://my.package.url/pkg_resources',
        ).as_dict
        assert mocks['_find_git_info'].mock_calls == []
        assert mocks['_find_pip_info'].mock_calls == [call(self.cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(self.cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_no_git_no_pip(self):

        def se_exception():
            raise Exception("some exception")

        with patch.multiple(
                pb,
                autospec=True,
                _find_git_info=DEFAULT,
                _find_pip_info=DEFAULT,
                _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'remotes': {},
                'tag': None,
                'commit': None,
                'dirty': None,
            }
            mocks['_find_pip_info'].side_effect = se_exception
            mocks['_find_pkg_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pkg_resources'
            }
            with patch('%s._git_repo_path' % pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = None
                res = self.cls.find_package_version()
        assert res.as_dict == VersionInfo(
            pkg_resources_version='1.2.3',
            pkg_resources_url='http://my.package.url/pkg_resources',
        ).as_dict
        assert mocks['_find_git_info'].mock_calls == []
        assert mocks['_find_pip_info'].mock_calls == [call(self.cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(self.cls)]
        assert mock_is_git.mock_calls == [call()]


class TestIsGitDirty(BaseTest):

    def test_is_git_dirty_false(self):
        with patch('%s._check_output' % pbm) as mock_check_out:
            with patch('%s.chdir' % pbm) as mock_chdir:
                mock_check_out.return_value = dedent("""
                On branch current_module
                Your branch is up-to-date with 'origin/current_module'.
                nothing to commit, working directory clean
                """)
                res = self.cls._is_git_dirty()
        assert res is False
        assert mock_chdir.mock_calls == [
            call('/foo/bar'),
            call().__enter__(),
            call().__exit__(None, None, None)
        ]
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]

    def test_is_git_dirty_false_detatched(self):
        with patch('%s.chdir' % pbm) as mock_chdir:
            with patch('%s._check_output' % pbm) as mock_check_out:
                mock_check_out.return_value = dedent("""
                HEAD detached at 9247d43
                nothing to commit, working directory clean
                """)
                res = self.cls._is_git_dirty()
        assert res is False
        assert mock_chdir.mock_calls == [
            call('/foo/bar'),
            call().__enter__(),
            call().__exit__(None, None, None)
        ]
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]

    def test_is_git_dirty_false_no_branch(self):
        with patch('%s.chdir' % pbm) as mock_chdir:
            with patch('%s._check_output' % pbm) as mock_check_out:
                mock_check_out.return_value = dedent("""
                Not currently on any branch.
                nothing to commit, working directory clean
                """)
                res = self.cls._is_git_dirty()
        assert res is False
        assert mock_chdir.mock_calls == [
            call('/foo/bar'),
            call().__enter__(),
            call().__exit__(None, None, None)
        ]
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]

    def test_is_git_dirty_true_ahead(self):
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = dedent("""
            On branch issues/8
            Your branch is ahead of 'origin/issues/8' by 1 commit.
              (use "git push" to publish your local commits)
            Changes not staged for commit:
              (use "git add <file>..." to update what will be committed)
              (use "git checkout -- <file>..." to discard changes in )

                    modified:   awslimitchecker/tests/test_versioncheck.py
                    modified:   awslimitchecker/versioncheck.py

            no changes added to commit (use "git add" and/or "git commit -a")
            """)
            with patch('%s.chdir' % pbm) as mock_chdir:
                res = self.cls._is_git_dirty()
        assert res is True
        assert mock_chdir.mock_calls == [
            call('/foo/bar'),
            call().__enter__(),
            call().__exit__(None, None, None)
        ]
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]

    def test_is_git_dirty_true_detatched(self):
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = dedent("""
            HEAD detached at 9247d43
            Untracked files:
              (use "git add <file>..." to include in what will be committed)

                    foo

            nothing added to commit but untracked files present
            """)
            with patch('%s.chdir' % pbm) as mock_chdir:
                res = self.cls._is_git_dirty()
        assert res is True
        assert mock_chdir.mock_calls == [
            call('/foo/bar'),
            call().__enter__(),
            call().__exit__(None, None, None)
        ]
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]

    def test_is_git_dirty_true_changes(self):
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = dedent("""
            On branch issues/8
            Your branch is up-to-date with 'origin/issues/8'.
            Changes not staged for commit:
              (use "git add <file>..." to update what will be committed)
              (use "git checkout -- <file>..." to discard changes in working

                    modified:   awslimitchecker/tests/test_versioncheck.py
                    modified:   awslimitchecker/versioncheck.py

            no changes added to commit (use "git add" and/or "git commit -a")
            """)
            with patch('%s.chdir' % pbm) as mock_chdir:
                res = self.cls._is_git_dirty()
        assert res is True
        assert mock_chdir.mock_calls == [
            call('/foo/bar'),
            call().__enter__(),
            call().__exit__(None, None, None)
        ]
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]


class TestGitRepoPath(BaseTest):

    def test_true(self):
        with patch('%s.os.path.exists' % pbm) as mock_exists:
            with patch('%s._package_top_dir' % pb,
                       new_callable=PropertyMock) as mock_top_dir:
                mock_top_dir.return_value = ['/foo/bar', '/foo/bar/baz']
                mock_exists.side_effect = [False, True]
                res = self.cls._git_repo_path
        assert res == '/foo/bar/baz/.git'
        assert mock_exists.mock_calls == [
            call('/foo/bar/.git'),
            call('/foo/bar/baz/.git')
        ]

    def test_false(self):
        with patch('%s.os.path.exists' % pbm) as mock_exists:
            with patch('%s._package_top_dir' % pb,
                       new_callable=PropertyMock) as mock_top_dir:
                mock_top_dir.return_value = ['/foo/bar', '/foo/bar/baz']
                mock_exists.return_value = False
                res = self.cls._git_repo_path
        assert res is None
        assert mock_exists.mock_calls == [
            call('/foo/bar/.git'),
            call('/foo/bar/baz/.git')
        ]

    @pytest.mark.skip
    def test_not_yet(self):
        print("TODO: get rid of this naive package path finding, and"
              "do something better that actually looks for the package"
              "top directory")
        assert 1 == 0


class TestFindGitInfo(BaseTest):

    def test_find(self):
        # this is a horribly ugly way to get this to work on py26-py34
        mocks = {}
        with patch.multiple(
            pbm,
            _get_git_commit=DEFAULT,
            _get_git_tag=DEFAULT,
            _get_git_remotes=DEFAULT,
            chdir=DEFAULT,
        ) as mocks1:
            mocks.update(mocks1)
            with patch.multiple(
                pb,
                _is_git_dirty=DEFAULT,
            ) as mocks2:
                mocks.update(mocks2)
                mocks['_get_git_commit'].return_value = '12345678'
                mocks['_get_git_tag'].return_value = 'mytag'
                mocks['_get_git_remotes'].return_value = {
                    'origin': 'http://my.git/url'
                }
                mocks['_is_git_dirty'].return_value = False
                res = self.cls._find_git_info('/git/repo/.git')
        assert mocks['_get_git_commit'].mock_calls == [call()]
        assert mocks['_get_git_tag'].mock_calls == [call('12345678')]
        assert mocks['_get_git_remotes'].mock_calls == [call()]
        assert mocks['_is_git_dirty'].mock_calls == [call()]
        assert mocks['chdir'].mock_calls == [
            call('/git/repo/.git'),
            call().__enter__(),
            call().__exit__(None, None, None)
        ]
        assert res == {
            'commit': '12345678',
            'dirty': False,
            'tag': 'mytag',
            'remotes': {'origin': 'http://my.git/url'}
        }

    def test_no_git(self):

        def se_exc():
            raise Exception("foo")

        # this is a horribly ugly way to get this to work on py26-py34
        mocks = {}
        with patch.multiple(
            pbm,
            _get_git_commit=DEFAULT,
            _get_git_tag=DEFAULT,
            _get_git_remotes=DEFAULT,
            chdir=DEFAULT,
        ) as mocks1:
            mocks.update(mocks1)
            with patch.multiple(
                pb,
                _is_git_dirty=DEFAULT,
            ) as mocks2:
                mocks.update(mocks2)
                mocks['_get_git_commit'].return_value = None
                mocks['_get_git_tag'].return_value = 'mytag'
                mocks['_get_git_remotes'].return_value = 'http://my.git/url'
                mocks['_is_git_dirty'].side_effect = se_exc
                res = self.cls._find_git_info('/git/repo/.git')
        assert mocks['_get_git_commit'].mock_calls == [call()]
        assert mocks['_get_git_tag'].mock_calls == []
        assert mocks['_get_git_remotes'].mock_calls == []
        assert mocks['_is_git_dirty'].mock_calls == [call()]
        assert mocks['chdir'].mock_calls == [
            call('/git/repo/.git'),
            call().__enter__(),
            call().__exit__(None, None, None)
        ]
        assert res == {
            'commit': None,
            'tag': None,
            'remotes': None,
            'dirty': None,
        }


class TestGetDistVersionUrl(BaseTest):

    def test_get(self):
        """pip 6.0+ - see issue #55"""
        dist = Mock(
            parsed_version=Version('1.2.3'),
            version='2.4.2',
            PKG_INFO='PKG-INFO',
        )
        metadata = [
            'Metadata-Version: 1.1',
            'Name: awslimitchecker',
            'Version: 0.1.0',
            'Summary: A script and python module to check your AWS service ',
            'Home-page: https://github.com/jantman/awslimitchecker',
            'Author: Jason Antman',
            'Author-email: jason@jasonantman.com',
            'License: UNKNOWN',
            'Description: awslimitchecker',
            '========================',
            '.. image:: https://pypip.in/v/awslimitchecker/badge.png',
            ':target: https://crate.io/packages/awslimitchecker',
            ':alt: PyPi package version',
            'Status',
            '------',
            'Keywords: AWS EC2 Amazon boto boto3 limits cloud',
            'Platform: UNKNOWN',
            'Classifier: Environment :: Console',
        ]

        def se_metadata(foo):
            for line in metadata:
                yield line

        dist.get_metadata_lines.side_effect = se_metadata
        res = self.cls._dist_version_url(dist)
        assert res == ('2.4.2',
                       'https://github.com/jantman/awslimitchecker')

    def test_pip1(self):
        """pip 1.x - see issue #54"""
        dist = Mock(
            parsed_version=('00000002', '00000004', '00000002', '*final'),
            version='2.4.2',
            PKG_INFO='PKG-INFO',
        )
        metadata = [
            'Metadata-Version: 1.1',
            'Name: awslimitchecker',
            'Version: 0.1.0',
            'Summary: A script and python module to check your AWS service ',
            'Home-page: https://github.com/jantman/awslimitchecker',
            'Author: Jason Antman',
            'Author-email: jason@jasonantman.com',
            'License: UNKNOWN',
            'Description: awslimitchecker',
            '========================',
            '.. image:: https://pypip.in/v/awslimitchecker/badge.png',
            ':target: https://crate.io/packages/awslimitchecker',
            ':alt: PyPi package version',
            'Status',
            '------',
            'Keywords: AWS EC2 Amazon boto boto3 limits cloud',
            'Platform: UNKNOWN',
            'Classifier: Environment :: Console',
        ]

        def se_metadata(foo):
            for line in metadata:
                yield line

        dist.get_metadata_lines.side_effect = se_metadata
        res = self.cls._dist_version_url(dist)
        assert res == ('2.4.2',
                       'https://github.com/jantman/awslimitchecker')

    def test_no_homepage(self):
        dist = Mock(
            version='1.2.3',
            PKG_INFO='PKG-INFO',
        )
        metadata = [
            'Metadata-Version: 1.1',
            'Name: awslimitchecker',
            'Version: 0.1.0',
            'Summary: A script and python module to check your AWS service ',
            'Author: Jason Antman',
            'Author-email: jason@jasonantman.com',
            'License: UNKNOWN',
            'Description: awslimitchecker',
            '========================',
            '.. image:: https://pypip.in/v/awslimitchecker/badge.png',
            ':target: https://crate.io/packages/awslimitchecker',
            ':alt: PyPi package version',
            'Status',
            '------',
            'Keywords: AWS EC2 Amazon boto boto3 limits cloud',
            'Platform: UNKNOWN',
            'Classifier: Environment :: Console',
        ]

        def se_metadata(foo):
            for line in metadata:
                yield line

        dist.get_metadata_lines.side_effect = se_metadata
        res = self.cls._dist_version_url(dist)
        assert res == ('1.2.3', None)


class TestFindPipInfo(BaseTest):

    def test_find(self):
        mock_distA = Mock(autospec=True, project_name='awslimitchecker')
        mock_distB = Mock(autospec=True, project_name='foo')
        mock_distC = Mock(autospec=True, project_name='another')
        installed_dists = [mock_distA, mock_distB, mock_distC]
        mock_frozen = Mock(
            autospec=True,
            req='foo==4.5.6'
        )

        with patch('%s.pip.get_installed_distributions' % pbm
                   ) as mock_pgid:
            with patch('%s.pip.FrozenRequirement.from_dist' % pbm
                       ) as mock_from_dist:
                with patch('%s._dist_version_url' % pb) as mock_dist_vu:
                    mock_pgid.return_value = installed_dists
                    mock_from_dist.return_value = mock_frozen
                    mock_dist_vu.return_value = ('4.5.6', 'http://foo')
                    res = self.cls._find_pip_info()
        assert res == {'version': '4.5.6', 'url': 'http://foo',
                       'requirement': 'foo==4.5.6'}
        assert mock_pgid.mock_calls == [call()]
        assert mock_from_dist.mock_calls == [call(mock_distB, [])]
        assert mock_dist_vu.mock_calls == [call(mock_distB)]

    def test_no_dist(self):
        mock_distB = Mock(autospec=True, project_name='other')
        mock_distC = Mock(autospec=True, project_name='another')
        installed_dists = [mock_distB, mock_distC]
        mock_frozen = Mock(
            autospec=True,
            req='awslimitchecker==0.1.0'
        )

        with patch('%s.pip.get_installed_distributions' % pbm
                   ) as mock_pgid:
            with patch('%s.pip.FrozenRequirement.from_dist' % pbm
                       ) as mock_from_dist:
                with patch('%s._dist_version_url' % pb) as mock_dist_vu:
                    mock_pgid.return_value = installed_dists
                    mock_from_dist.return_value = mock_frozen
                    mock_dist_vu.return_value = ('4.5.6', 'http://foo')
                    res = self.cls._find_pip_info()
        assert res == {}
        assert mock_pgid.mock_calls == [call()]
        assert mock_from_dist.mock_calls == []
        assert mock_dist_vu.mock_calls == []

    def test_req_https(self):
        req_str = 'git+https://github.com/jantman/foo.git@76c7e51' \
                  'f6e83350c72a1d3e8122ee03e589bbfde#egg=foo-master'
        mock_distA = Mock(autospec=True, project_name='awslimitchecker')
        mock_distB = Mock(autospec=True, project_name='foo')
        mock_distC = Mock(autospec=True, project_name='another')
        installed_dists = [mock_distA, mock_distB, mock_distC]
        mock_frozen = Mock(
            autospec=True,
            req=req_str
        )

        with patch('%s.pip.get_installed_distributions' % pbm
                   ) as mock_pgid:
            with patch('%s.pip.FrozenRequirement.from_dist' % pbm
                       ) as mock_from_dist:
                with patch('%s._dist_version_url' % pb) as mock_dist_vu:
                    mock_pgid.return_value = installed_dists
                    mock_from_dist.return_value = mock_frozen
                    mock_dist_vu.return_value = ('4.5.6', 'http://foo')
                    res = self.cls._find_pip_info()
        assert res == {'version': '4.5.6', 'url': 'http://foo',
                       'requirement': req_str}
        assert mock_pgid.mock_calls == [call()]
        assert mock_from_dist.mock_calls == [call(mock_distB, [])]
        assert mock_dist_vu.mock_calls == [call(mock_distB)]

    def test_req_git(self):
        req_str = 'git+git@github.com:jantman/foo.git@76c7e51f6e8' \
                  '3350c72a1d3e8122ee03e589bbfde#egg=foo-master'
        mock_distA = Mock(autospec=True, project_name='awslimitchecker')
        mock_distB = Mock(autospec=True, project_name='foo')
        mock_distC = Mock(autospec=True, project_name='another')
        installed_dists = [mock_distA, mock_distB, mock_distC]
        mock_frozen = Mock(
            autospec=True,
            req=req_str
        )

        with patch('%s.pip.get_installed_distributions' % pbm
                   ) as mock_pgid:
            with patch('%s.pip.FrozenRequirement.from_dist' % pbm
                       ) as mock_from_dist:
                with patch('%s._dist_version_url' % pb) as mock_dist_vu:
                    mock_pgid.return_value = installed_dists
                    mock_from_dist.return_value = mock_frozen
                    mock_dist_vu.return_value = ('4.5.6', 'http://foo')
                    res = self.cls._find_pip_info()
        assert res == {'version': '4.5.6', 'url': 'http://foo',
                       'requirement': req_str}
        assert mock_pgid.mock_calls == [call()]
        assert mock_from_dist.mock_calls == [call(mock_distB, [])]
        assert mock_dist_vu.mock_calls == [call(mock_distB)]


class TestFindPkgInfo(BaseTest):

    def test_find_pkg_info(self):
        mock_distA = Mock(autospec=True, project_name='awslimitchecker')
        with patch('%s.pkg_resources.require' % pbm) as mock_require:
            with patch('%s._dist_version_url' % pb) as mock_dvu:
                mock_require.return_value = [mock_distA]
                mock_dvu.return_value = ('7.8.9', 'http://foobar')
                res = self.cls._find_pkg_info()
        assert res == {'version': '7.8.9', 'url': 'http://foobar'}


class TestGetGitRemotes(object):

    def test_simple(self):
        cmd_out = '' \
                "origin  git@github.com:jantman/awslimitchecker.git (fetch)\n" \
                "origin  git@github.com:jantman/awslimitchecker.git (push)\n"
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = cmd_out
            res = _get_git_remotes()
        assert res == {
            'origin': 'git@github.com:jantman/awslimitchecker.git'
        }
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]

    def test_fork(self):
        cmd_out = "origin  git@github.com:someone/awslimitchecker.git (fetch" \
                  ")\n" \
                  "origin  git@github.com:someone/awslimitchecker.git (push)" \
                  "\n" \
                  "upstream        https://github.com/jantman/awslimitchecke" \
                  "r.git (fetch)\n" \
                  "upstream        https://github.com/jantman/awslimitchecker" \
                  ".git (push)\n"
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = cmd_out
            res = _get_git_remotes()
        assert res == {
            'origin': 'git@github.com:someone/awslimitchecker.git',
            'upstream': 'https://github.com/jantman/awslimitchecker.git'
        }
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]

    def test_no_origin(self):
        cmd_out = "mine  git@github.com:someone/awslimitchecker.git (fetch" \
                  ")\n" \
                  "mine  git@github.com:someone/awslimitchecker.git (push)" \
                  "\n" \
                  "upstream        https://github.com/jantman/awslimitchecke" \
                  "r.git (fetch)\n" \
                  "upstream        https://github.com/jantman/awslimitchecker" \
                  ".git (push)\n" \
                  "another        https://github.com/foo/awslimitchecke" \
                  "r.git (fetch)\n" \
                  "another        https://github.com/foo/awslimitchecker" \
                  ".git (push)\n"
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = cmd_out
            res = _get_git_remotes()
        assert res == {
            'another': 'https://github.com/foo/awslimitchecker.git',
            'upstream': 'https://github.com/jantman/awslimitchecker.git',
            'mine': 'git@github.com:someone/awslimitchecker.git'
        }
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]

    def test_exception(self):

        def se(foo, stderr=None):
            raise subprocess.CalledProcessError(3, 'mycommand')

        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.side_effect = se
            res = _get_git_remotes()
        assert res == {}
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]

    def test_none(self):
        cmd_out = ''
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = cmd_out
            res = _get_git_remotes()
        assert res == {}
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]

    def test_no_fetch(self):
        cmd_out = "mine  git@github.com:someone/awslimitchecker.git (push)" \
                  "\n" \
                  "upstream        https://github.com/jantman/awslimitchecker" \
                  ".git (push)\n" \
                  "another        https://github.com/jantman/awslimitchecker" \
                  ".git (push)\n"
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = cmd_out
            res = _get_git_remotes()
        assert res == {}
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]


class TestGetGitTag(object):

    def test_get(self):
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = 'mytag'
            res = _get_git_tag('abcd')
        assert res == 'mytag'
        assert mock_check_out.mock_calls == [
            call(['git', 'describe', '--exact-match', '--tags', 'abcd'],
                 stderr=DEVNULL)
        ]

    def test_commit_none(self):
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = 'mytag'
            res = _get_git_tag(None)
        assert res is None
        assert mock_check_out.mock_calls == []

    def test_no_tags(self):
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = ''
            res = _get_git_tag('abcd')
        assert res is None
        assert mock_check_out.mock_calls == [
            call(['git', 'describe', '--exact-match', '--tags', 'abcd'],
                 stderr=DEVNULL)
        ]

    def test_exception(self):

        def se(foo, stderr=None):
            raise subprocess.CalledProcessError(3, 'mycommand')

        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.side_effect = se
            res = _get_git_tag('abcd')
        assert res is None
        assert mock_check_out.mock_calls == [
            call(['git', 'describe', '--exact-match', '--tags', 'abcd'],
                 stderr=DEVNULL)
        ]


class TestGetGitCommit(object):

    def test_get(self):
        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = '1234abcd'
            res = _get_git_commit()
        assert res == '1234abcd'
        assert mock_check_out.mock_calls == [
            call(['git', 'rev-parse', 'HEAD'],
                 stderr=DEVNULL)
        ]

    def test_exception(self):

        def se(foo):
            raise subprocess.CalledProcessError(3, 'mycommand')

        with patch('%s._check_output' % pbm) as mock_check_out:
            mock_check_out.side_effect = se
            res = _get_git_commit()
        assert res is None
        assert mock_check_out.mock_calls == [
            call(['git', 'rev-parse', 'HEAD'],
                 stderr=DEVNULL)
        ]


class TestPackageTopDir(BaseTest):

    def test_none(self):
        self.cls.package_dir = '/foo'
        self.cls._pip_locations = []
        self.cls._pkg_resources_locations = []
        assert self.cls._package_top_dir == ['/foo']

    def test_pip(self):
        self.cls.package_dir = '/foo'
        self.cls._pip_locations = ['/bar', '/baz', None]
        self.cls._pkg_resources_locations = []
        assert self.cls._package_top_dir == ['/bar', '/baz', '/foo']

    def test_pkg_resources(self):
        self.cls.package_dir = '/foo'
        self.cls._pip_locations = []
        self.cls._pkg_resources_locations = ['/bar', '/baz', None]
        assert self.cls._package_top_dir == ['/bar', '/baz', '/foo']

    def test_all(self):
        self.cls.package_dir = '/foo'
        self.cls._pip_locations = ['/bar', None]
        self.cls._pkg_resources_locations = ['/baz', None]
        assert self.cls._package_top_dir == ['/bar', '/baz', '/foo']


class TestCheckOutput(object):

    @pytest.mark.skipif(
        (
                sys.version_info[0] != 2 or
                (sys.version_info[0] == 2 and sys.version_info[1] != 6)
        ),
        reason='not running py26 test on %d.%d.%d' % (
                sys.version_info[0],
                sys.version_info[1],
                sys.version_info[2]
        ))
    def test_py26(self):
        mock_p = Mock(returncode=0)
        mock_p.communicate.return_value = ('foo', 'bar')
        with patch('%s.subprocess.Popen' % pbm) as mock_popen:
            mock_popen.return_value = mock_p
            res = _check_output(['mycmd'], stderr='something')
        assert res == 'foo'
        assert mock_popen.mock_calls == [
            call(
                ['mycmd'],
                stderr='something',
                stdout=subprocess.PIPE
            ),
            call().communicate()
        ]

    @pytest.mark.skipif(
        (
                sys.version_info[0] != 2 or
                (sys.version_info[0] == 2 and sys.version_info[1] != 6)
        ),
        reason='not running py26 test on %d.%d.%d' % (
                sys.version_info[0],
                sys.version_info[1],
                sys.version_info[2]
        ))
    def test_py26_exception(self):
        mock_p = Mock(returncode=2)
        mock_p.communicate.return_value = ('foo', 'bar')
        with patch('%s.subprocess.Popen' % pbm) as mock_popen:
            mock_popen.return_value = mock_p
            with pytest.raises(subprocess.CalledProcessError) as exc:
                _check_output(['mycmd'], stderr='something')
        assert mock_popen.mock_calls == [
            call(
                ['mycmd'],
                stderr='something',
                stdout=subprocess.PIPE
            ),
            call().communicate()
        ]
        assert exc.value.cmd == ['mycmd']
        assert exc.value.returncode == 2

    @pytest.mark.skipif(
        (
                sys.version_info[0] != 2 or
                (sys.version_info[0] == 2 and sys.version_info[1] != 7)
        ),
        reason='not running py27 test on %d.%d.%d' % (
                sys.version_info[0],
                sys.version_info[1],
                sys.version_info[2]
        ))
    def test_py27(self):
        with patch('%s.subprocess.check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = 'foobar'
            res = _check_output(['foo', 'bar'], stderr='something')
        assert res == 'foobar'
        assert mock_check_out.mock_calls == [
            call(['foo', 'bar'], stderr='something')
        ]

    @pytest.mark.skipif(sys.version_info[0] < 3,
                        reason='not running py3 test on %d.%d.%d' % (
                            sys.version_info[0],
                            sys.version_info[1],
                            sys.version_info[2]
                        ))
    def test_py3(self):
        with patch('%s.subprocess.check_output' % pbm) as mock_check_out:
            mock_check_out.return_value = 'foobar'.encode('utf-8')
            res = _check_output(['foo', 'bar'], stderr='something')
        assert res == 'foobar'
        assert mock_check_out.mock_calls == [
            call(['foo', 'bar'], stderr='something')
        ]


class TestChdir(object):

    def test_chdir(self):
        with patch('%s.os.getcwd' % pbm, autospec=True) as mock_getcwd:
            with patch('%s.os.chdir' % pbm, autospec=True) as mock_chdir:
                mock_getcwd.return_value = '/old/cwd'
                with chdir('/new/dir'):
                    pass
        assert mock_chdir.mock_calls == [
            call('/new/dir'),
            call('/old/cwd')
        ]
