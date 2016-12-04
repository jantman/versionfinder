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
from pip._vendor.packaging.version import Version
from git import Repo

from versionfinder.versionfinder import (VersionFinder, chdir)
from versionfinder.versioninfo import VersionInfo

import logging
logger = logging.getLogger(__name__)

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import patch, call, DEFAULT, Mock, PropertyMock, MagicMock
else:
    from unittest.mock import (
        patch, call, DEFAULT, Mock, PropertyMock, MagicMock)

pbm = 'versionfinder.versionfinder'
pb = '%s.VersionFinder' % pbm


def mockrepo(commit=None, dirty=False, remotes={}, tag=None):
    """return a mock Repo"""
    m = MagicMock(spec_set=Repo)
    m.is_dirty.return_value = dirty
    m.head.commit.hexsha = commit
    tag1 = MagicMock()
    tag1.name = 'wrongTagName'
    tag1.commit.hexsha = '1234'
    tags = [tag1]
    if tag is not None:
        tag2 = MagicMock()
        tag2.name = tag
        tag2.commit.hexsha = commit
        tags.append(tag2)
    m.tags = tags
    rmts = []
    for name, url in remotes.items():
        rmt = MagicMock()
        rmt.name = name
        if isinstance(url, type([])):
            rmt.urls = url
        else:
            rmt.urls = [url]
        rmts.append(rmt)
    m.remotes = rmts
    return m


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
        with patch('%s.Repo' % pbm, autospec=True) as mock_repo:
            mock_repo.return_value = mockrepo(
                commit='12345678',
                dirty=False,
                remotes={
                    'origin': 'http://my.git/url',
                    'upstream': ['git@github.com:/foo/bar', 'bar'],
                    'foo': [],
                },
                tag='mytag'
            )
            res = self.cls._find_git_info('/git/repo/.git')
        assert res == {
            'commit': '12345678',
            'dirty': False,
            'tag': 'mytag',
            'remotes': {
                'origin': 'http://my.git/url',
                'upstream': 'git@github.com:/foo/bar'
            }
        }
        assert mock_repo.mock_calls == [
            call(path='/git/repo/.git', search_parent_directories=False),
            call().is_dirty(untracked_files=True)
        ]

    def test_no_git(self):

        def se_exc():
            raise Exception("foo")

        with patch('%s.Repo' % pbm, autospec=True) as mock_repo:
            mock_repo.side_effect = se_exc
            res = self.cls._find_git_info('/git/repo/.git')
        assert res == {
            'commit': None,
            'tag': None,
            'remotes': None,
            'dirty': None,
        }
        assert mock_repo.mock_calls == [
            call(path='/git/repo/.git', search_parent_directories=False)
        ]


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
