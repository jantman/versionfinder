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
import os
import subprocess
import shutil
from textwrap import dedent
from pip._vendor.packaging.version import Version

from versionfinder.version import VERSION
import versionfinder.versionfinder
from versionfinder.versionfinder import (
    _get_git_commit, _get_git_url, _get_git_tag, _check_output, DEVNULL,
    VersionFinder
)

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


class Test_Init(object):

    def test_init(self):
        cls = VersionFinder('foobar')
        assert cls.package_name == 'foobar'


class Test_VersionFinder(object):
    """
    Mocked unit tests for VersionFinder
    """

    def test_is_git_dirty_false(self):
        cls = VersionFinder()
        with patch('%s._check_output' % self.mpb) as mock_check_out:
            mock_check_out.return_value = dedent("""
            On branch current_module
            Your branch is up-to-date with 'origin/current_module'.
            nothing to commit, working directory clean
            """)
            res = cls._is_git_dirty()
        assert res is False
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]

    def test_is_git_dirty_false_detatched(self):
        cls = VersionFinder()
        with patch('%s._check_output' % self.mpb) as mock_check_out:
            mock_check_out.return_value = dedent("""
            HEAD detached at 9247d43
            nothing to commit, working directory clean
            """)
            res = cls._is_git_dirty()
        assert res is False
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]

    def test_is_git_dirty_false_no_branch(self):
        cls = VersionFinder()
        with patch('%s._check_output' % self.mpb) as mock_check_out:
            mock_check_out.return_value = dedent("""
            Not currently on any branch.
            nothing to commit, working directory clean
            """)
            res = cls._is_git_dirty()
        assert res is False
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]

    def test_is_git_dirty_true_ahead(self):
        cls = VersionFinder()
        with patch('%s._check_output' % self.mpb) as mock_check_out:
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
            res = cls._is_git_dirty()
        assert res is True
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]

    def test_is_git_dirty_true_detatched(self):
        cls = VersionFinder()
        with patch('%s._check_output' % self.mpb) as mock_check_out:
            mock_check_out.return_value = dedent("""
            HEAD detached at 9247d43
            Untracked files:
              (use "git add <file>..." to include in what will be committed)

                    foo

            nothing added to commit but untracked files present
            """)
            res = cls._is_git_dirty()
        assert res is True
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]

    def test_is_git_dirty_true_changes(self):
        cls = VersionFinder()
        with patch('%s._check_output' % self.mpb) as mock_check_out:
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
            res = cls._is_git_dirty()
        assert res is True
        assert mock_check_out.mock_calls == [
            call(['git', 'status', '-u'], stderr=DEVNULL)
        ]

    def test_find_git_info(self):
        cls = VersionFinder()
        # this is a horribly ugly way to get this to work on py26-py34
        mocks = {}
        with patch.multiple(
            self.mpb,
            _get_git_commit=DEFAULT,
            _get_git_tag=DEFAULT,
            _get_git_url=DEFAULT,
        ) as mocks1:
            mocks.update(mocks1)
            with patch.multiple(
                self.pb,
                _is_git_dirty=DEFAULT,
            ) as mocks2:
                mocks.update(mocks2)
                with patch.multiple(
                    '%s.os' % self.mpb,
                    getcwd=DEFAULT,
                    chdir=DEFAULT,
                ) as mocks3:
                    mocks.update(mocks3)
                    mocks['getcwd'].return_value = '/my/cwd'
                    mocks['_get_git_commit'].return_value = '12345678'
                    mocks['_get_git_tag'].return_value = 'mytag'
                    mocks['_get_git_url'].return_value = 'http://my.git/url'
                    mocks['_is_git_dirty'].return_value = False
                    res = cls._find_git_info()
        assert mocks['_get_git_commit'].mock_calls == [call()]
        assert mocks['_get_git_tag'].mock_calls == [call('12345678')]
        assert mocks['_get_git_url'].mock_calls == [call()]
        assert mocks['_is_git_dirty'].mock_calls == [call()]
        assert mocks['getcwd'].mock_calls == [call()]
        assert mocks['chdir'].mock_calls == [
            call(os.path.dirname(os.path.abspath(
                versionfinder.versionfinder.__file__))),
            call('/my/cwd')
        ]
        assert res == {
            'commit': '12345678',
            'dirty': False,
            'tag': 'mytag',
            'url': 'http://my.git/url'
        }

    def test_find_git_info_no_git(self):
        cls = VersionFinder()

        def se_exc():
            raise Exception("foo")

        # this is a horribly ugly way to get this to work on py26-py34
        mocks = {}
        with patch.multiple(
            self.mpb,
            _get_git_commit=DEFAULT,
            _get_git_tag=DEFAULT,
            _get_git_url=DEFAULT,
        ) as mocks1:
            mocks.update(mocks1)
            with patch.multiple(
                self.pb,
                _is_git_dirty=DEFAULT,
            ) as mocks2:
                mocks.update(mocks2)
                with patch.multiple(
                    '%s.os' % self.mpb,
                    getcwd=DEFAULT,
                    chdir=DEFAULT,
                ) as mocks3:
                    mocks.update(mocks3)
                    mocks['getcwd'].return_value = '/my/cwd'
                    mocks['_get_git_commit'].return_value = None
                    mocks['_get_git_tag'].return_value = 'mytag'
                    mocks['_get_git_url'].return_value = 'http://my.git/url'
                    mocks['_is_git_dirty'].side_effect = se_exc
                    res = cls._find_git_info()
        assert mocks['_get_git_commit'].mock_calls == [call()]
        assert mocks['_get_git_tag'].mock_calls == []
        assert mocks['_get_git_url'].mock_calls == []
        assert mocks['_is_git_dirty'].mock_calls == [call()]
        assert mocks['getcwd'].mock_calls == [call()]
        assert mocks['chdir'].mock_calls == [
            call(os.path.dirname(os.path.abspath(
                versionfinder.versionfinder.__file__))),
            call('/my/cwd')
        ]
        assert res == {
            'commit': None,
            'tag': None,
            'url': None,
            'dirty': None,
        }

    def test_get_dist_version_url(self):
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
        cls = VersionFinder()
        res = cls._dist_version_url(dist)
        assert res == ('2.4.2',
                       'https://github.com/jantman/awslimitchecker')

    def test_get_dist_version_url_pip1(self):
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
        cls = VersionFinder()
        res = cls._dist_version_url(dist)
        assert res == ('2.4.2',
                       'https://github.com/jantman/awslimitchecker')

    def test_get_dist_version_url_no_homepage(self):
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
        cls = VersionFinder()
        res = cls._dist_version_url(dist)
        assert res == ('1.2.3', None)

    def test_find_pip_info(self):
        cls = VersionFinder()
        mock_distA = Mock(autospec=True, project_name='awslimitchecker')
        mock_distB = Mock(autospec=True, project_name='other')
        mock_distC = Mock(autospec=True, project_name='another')
        installed_dists = [mock_distA, mock_distB, mock_distC]
        mock_frozen = Mock(
            autospec=True,
            req='awslimitchecker==0.1.0'
        )

        with patch('%s.pip.get_installed_distributions' % self.mpb
                   ) as mock_pgid:
            with patch('%s.pip.FrozenRequirement.from_dist' % self.mpb
                       ) as mock_from_dist:
                with patch('%s._dist_version_url' % self.pb) as mock_dist_vu:
                    mock_pgid.return_value = installed_dists
                    mock_from_dist.return_value = mock_frozen
                    mock_dist_vu.return_value = ('4.5.6', 'http://foo')
                    res = cls._find_pip_info()
        assert res == {'version': '4.5.6', 'url': 'http://foo'}
        assert mock_pgid.mock_calls == [call()]
        assert mock_from_dist.mock_calls == [call(mock_distA, [])]
        assert mock_dist_vu.mock_calls == [call(mock_distA)]

    def test_find_pip_info_no_dist(self):
        cls = VersionFinder()
        mock_distB = Mock(autospec=True, project_name='other')
        mock_distC = Mock(autospec=True, project_name='another')
        installed_dists = [mock_distB, mock_distC]
        mock_frozen = Mock(
            autospec=True,
            req='awslimitchecker==0.1.0'
        )

        with patch('%s.pip.get_installed_distributions' % self.mpb
                   ) as mock_pgid:
            with patch('%s.pip.FrozenRequirement.from_dist' % self.mpb
                       ) as mock_from_dist:
                with patch('%s._dist_version_url' % self.pb) as mock_dist_vu:
                    mock_pgid.return_value = installed_dists
                    mock_from_dist.return_value = mock_frozen
                    mock_dist_vu.return_value = ('4.5.6', 'http://foo')
                    res = cls._find_pip_info()
        assert res == {}
        assert mock_pgid.mock_calls == [call()]
        assert mock_from_dist.mock_calls == []
        assert mock_dist_vu.mock_calls == []

    def test_find_pip_info_req_https(self):
        req_str = 'git+https://github.com/jantman/awslimitchecker.git@76c7e51' \
                  'f6e83350c72a1d3e8122ee03e589bbfde#egg=awslimitchecker-master'
        cls = VersionFinder()
        mock_distA = Mock(autospec=True, project_name='awslimitchecker')
        mock_distB = Mock(autospec=True, project_name='other')
        mock_distC = Mock(autospec=True, project_name='another')
        installed_dists = [mock_distA, mock_distB, mock_distC]
        mock_frozen = Mock(
            autospec=True,
            req=req_str
        )

        with patch('%s.pip.get_installed_distributions' % self.mpb
                   ) as mock_pgid:
            with patch('%s.pip.FrozenRequirement.from_dist' % self.mpb
                       ) as mock_from_dist:
                with patch('%s._dist_version_url' % self.pb) as mock_dist_vu:
                    mock_pgid.return_value = installed_dists
                    mock_from_dist.return_value = mock_frozen
                    mock_dist_vu.return_value = ('4.5.6', 'http://foo')
                    res = cls._find_pip_info()
        assert res == {'version': '4.5.6', 'url': req_str}
        assert mock_pgid.mock_calls == [call()]
        assert mock_from_dist.mock_calls == [call(mock_distA, [])]
        assert mock_dist_vu.mock_calls == [call(mock_distA)]

    def test_find_pip_info_req_git(self):
        req_str = 'git+git@github.com:jantman/awslimitchecker.git@76c7e51f6e8' \
                  '3350c72a1d3e8122ee03e589bbfde#egg=awslimitchecker-master'
        cls = VersionFinder()
        mock_distA = Mock(autospec=True, project_name='awslimitchecker')
        mock_distB = Mock(autospec=True, project_name='other')
        mock_distC = Mock(autospec=True, project_name='another')
        installed_dists = [mock_distA, mock_distB, mock_distC]
        mock_frozen = Mock(
            autospec=True,
            req=req_str
        )

        with patch('%s.pip.get_installed_distributions' % self.mpb
                   ) as mock_pgid:
            with patch('%s.pip.FrozenRequirement.from_dist' % self.mpb
                       ) as mock_from_dist:
                with patch('%s._dist_version_url' % self.pb) as mock_dist_vu:
                    mock_pgid.return_value = installed_dists
                    mock_from_dist.return_value = mock_frozen
                    mock_dist_vu.return_value = ('4.5.6', 'http://foo')
                    res = cls._find_pip_info()
        assert res == {'version': '4.5.6', 'url': req_str}
        assert mock_pgid.mock_calls == [call()]
        assert mock_from_dist.mock_calls == [call(mock_distA, [])]
        assert mock_dist_vu.mock_calls == [call(mock_distA)]

    def test_find_pkg_info(self):
        cls = VersionFinder()
        mock_distA = Mock(autospec=True, project_name='awslimitchecker')
        with patch('%s.pkg_resources.require' % self.mpb) as mock_require:
            with patch('%s._dist_version_url' % self.pb) as mock_dvu:
                mock_require.return_value = [mock_distA]
                mock_dvu.return_value = ('7.8.9', 'http://foobar')
                res = cls._find_pkg_info()
        assert res == {'version': '7.8.9', 'url': 'http://foobar'}

    def test_find_package_version_git_notag(self):
        cls = VersionFinder()
        with patch.multiple(
            self.pb,
            autospec=True,
            _find_git_info=DEFAULT,
            _find_pip_info=DEFAULT,
            _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'url': 'git+https://foo',
                'tag': None,
                'commit': '12345678',
                'dirty': False
            }
            mocks['_find_pip_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pip'
            }
            mocks['_find_pkg_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pkg_resources'
            }
            with patch('%s._is_git_clone' % self.pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = True
                res = cls.find_package_version()
        assert res == {
            'version': '1.2.3',
            'url': 'git+https://foo',
            'tag': None,
            'commit': '12345678',
            'dirty': False,
        }
        assert mocks['_find_git_info'].mock_calls == [call(cls)]
        assert mocks['_find_pip_info'].mock_calls == [call(cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_find_package_version_git_notag_dirty(self):
        cls = VersionFinder()
        with patch.multiple(
            self.pb,
            autospec=True,
            _find_git_info=DEFAULT,
            _find_pip_info=DEFAULT,
            _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'url': 'git+https://foo',
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
            with patch('%s._is_git_clone' % self.pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = True
                res = cls.find_package_version()
        assert res == {
            'version': '1.2.3',
            'url': 'git+https://foo',
            'tag': None,
            'commit': '12345678*',
            'dirty': True,
        }
        assert mocks['_find_git_info'].mock_calls == [call(cls)]
        assert mocks['_find_pip_info'].mock_calls == [call(cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_find_package_version_git_tag(self):
        cls = VersionFinder()
        with patch.multiple(
            self.pb,
            autospec=True,
            _find_git_info=DEFAULT,
            _find_pip_info=DEFAULT,
            _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'url': 'git+https://foo',
                'tag': 'mytag',
                'commit': '12345678',
                'dirty': False
            }
            mocks['_find_pip_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pip'
            }
            mocks['_find_pkg_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pkg_resources'
            }
            with patch('%s._is_git_clone' % self.pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = True
                res = cls.find_package_version()
        assert res == {
            'version': '1.2.3',
            'url': 'git+https://foo',
            'tag': 'mytag',
            'commit': '12345678',
            'dirty': False,
        }
        assert mocks['_find_git_info'].mock_calls == [call(cls)]
        assert mocks['_find_pip_info'].mock_calls == [call(cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_find_package_version_git_tag_dirty(self):
        cls = VersionFinder()
        with patch.multiple(
            self.pb,
            autospec=True,
            _find_git_info=DEFAULT,
            _find_pip_info=DEFAULT,
            _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'url': 'git+https://foo',
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
            with patch('%s._is_git_clone' % self.pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = True
                res = cls.find_package_version()
        assert res == {
            'version': '1.2.3',
            'url': 'git+https://foo',
            'tag': 'mytag*',
            'commit': '12345678*',
            'dirty': True,
        }
        assert mocks['_find_git_info'].mock_calls == [call(cls)]
        assert mocks['_find_pip_info'].mock_calls == [call(cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_find_package_version_pkg_res_exception(self):
        cls = VersionFinder()

        def se_exception():
            raise Exception("some exception")

        with patch.multiple(
            self.pb,
            autospec=True,
            _find_git_info=DEFAULT,
            _find_pip_info=DEFAULT,
            _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'url': 'git+https://foo',
                'tag': None,
                'commit': '12345678',
                'dirty': False
            }
            mocks['_find_pip_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pip'
            }
            mocks['_find_pkg_info'].side_effect = se_exception
            with patch('%s._is_git_clone' % self.pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = True
                res = cls.find_package_version()
        assert res == {
            'version': '1.2.3',
            'url': 'git+https://foo',
            'tag': None,
            'commit': '12345678',
            'dirty': False,
        }
        assert mocks['_find_git_info'].mock_calls == [call(cls)]
        assert mocks['_find_pip_info'].mock_calls == [call(cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_find_package_version_pip_exception(self):
        cls = VersionFinder()

        def se_exception():
            raise Exception("some exception")

        with patch.multiple(
            self.pb,
            autospec=True,
            _find_git_info=DEFAULT,
            _find_pip_info=DEFAULT,
            _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'url': 'git+https://foo',
                'tag': None,
                'commit': '12345678',
                'dirty': False
            }
            mocks['_find_pip_info'].side_effect = se_exception
            mocks['_find_pkg_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pkg_resources'
            }
            with patch('%s._is_git_clone' % self.pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = True
                res = cls.find_package_version()
        assert res == {
            'version': '1.2.3',
            'url': 'git+https://foo',
            'tag': None,
            'commit': '12345678',
            'dirty': False,
        }
        assert mocks['_find_git_info'].mock_calls == [call(cls)]
        assert mocks['_find_pip_info'].mock_calls == [call(cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_find_package_version_no_git(self):
        cls = VersionFinder()

        with patch.multiple(
            self.pb,
            autospec=True,
            _find_git_info=DEFAULT,
            _find_pip_info=DEFAULT,
            _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'url': None,
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
            with patch('%s._is_git_clone' % self.pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = False
                res = cls.find_package_version()
        assert res == {
            'version': '1.2.3',
            'url': 'http://my.package.url/pip',
            'tag': None,
            'commit': None,
        }
        assert mocks['_find_git_info'].mock_calls == []
        assert mocks['_find_pip_info'].mock_calls == [call(cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_find_package_version_no_git_no_pip(self):
        cls = VersionFinder()

        def se_exception():
            raise Exception("some exception")

        with patch.multiple(
            self.pb,
            autospec=True,
            _find_git_info=DEFAULT,
            _find_pip_info=DEFAULT,
            _find_pkg_info=DEFAULT,
        ) as mocks:
            mocks['_find_git_info'].return_value = {
                'url': None,
                'tag': None,
                'commit': None,
                'dirty': None,
            }
            mocks['_find_pip_info'].side_effect = se_exception
            mocks['_find_pkg_info'].return_value = {
                'version': '1.2.3',
                'url': 'http://my.package.url/pkg_resources'
            }
            with patch('%s._is_git_clone' % self.pb,
                       new_callable=PropertyMock) as mock_is_git:
                mock_is_git.return_value = False
                res = cls.find_package_version()
        assert res == {
            'version': '1.2.3',
            'url': 'http://my.package.url/pkg_resources',
            'tag': None,
            'commit': None,
        }
        assert mocks['_find_git_info'].mock_calls == []
        assert mocks['_find_pip_info'].mock_calls == [call(cls)]
        assert mocks['_find_pkg_info'].mock_calls == [call(cls)]
        assert mock_is_git.mock_calls == [call()]

    def test_find_package_version_debug(self):
        mock_pip_logger = Mock(spec_set=logging.Logger)

        with patch.dict('%s.os.environ' % self.mpb,
                        {'VERSIONCHECK_DEBUG': 'true'}):
            with patch('%s.logging' % self.mpb) as mock_logging:
                cls = VersionFinder()
                with patch.multiple(
                        self.pb,
                        autospec=True,
                        _find_git_info=DEFAULT,
                        _find_pip_info=DEFAULT,
                        _find_pkg_info=DEFAULT,
                ) as mocks:
                    mocks['_find_git_info'].return_value = {
                        'url': None,
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
                    with patch('%s.logger' % self.mpb,
                               spec_set=logging.Logger) as mock_mod_logger:
                        mock_logging.getLogger.return_value = mock_pip_logger
                        with patch('%s._is_git_clone' % self.pb,
                                   new_callable=PropertyMock) as mock_is_git:
                            mock_is_git.return_value = False
                            cls.find_package_version()
        assert mock_logging.mock_calls == []
        assert mock_pip_logger.mock_calls == []
        assert mock_mod_logger.mock_calls == [
            call.debug('Install does not appear to be a git clone'),
            call.debug('pip info: %s', {'url': 'http://my.package.url/pip',
                                        'version': '1.2.3'}),
            call.debug('pkg_resources info: %s',
                       {'url': 'http://my.package.url/pkg_resources',
                        'version': '1.2.3'}),
            call.debug('Final package info: %s',
                       {'url': 'http://my.package.url/pip', 'commit': None,
                        'version': '1.2.3', 'tag': None})
        ]
        assert mock_is_git.mock_calls == [call()]

    def test_find_package_version_no_debug(self):
        mock_pip_logger = Mock()
        type(mock_pip_logger).propagate = False

        with patch.dict('%s.os.environ' % self.mpb,
                        {'VERSIONCHECK_DEBUG': 'false'}):
            with patch('%s.logging' % self.mpb) as mock_logging:
                mock_logging.getLogger.return_value = mock_pip_logger
                cls = VersionFinder()
                with patch.multiple(
                        self.pb,
                        autospec=True,
                        _find_git_info=DEFAULT,
                        _find_pip_info=DEFAULT,
                        _find_pkg_info=DEFAULT,
                ) as mocks:
                    mocks['_find_git_info'].return_value = {
                        'url': None,
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
                    with patch('%s.logger' % self.mpb,
                               spec_set=logging.Logger) as mock_mod_logger:
                        with patch('%s._is_git_clone' % self.pb,
                                   new_callable=PropertyMock) as mock_is_git:
                            mock_is_git.return_value = False
                            cls.find_package_version()
        assert mock_logging.mock_calls == [
            call.getLogger("pip"),
            call.getLogger().setLevel(mock_logging.WARNING)
        ]
        assert mock_pip_logger.mock_calls == [
            call.setLevel(mock_logging.WARNING),
        ]
        assert mock_mod_logger.mock_calls == [
            call.setLevel(mock_logging.WARNING),
            call.debug('Install does not appear to be a git clone'),
            call.debug('pip info: %s', {'url': 'http://my.package.url/pip',
                                        'version': '1.2.3'}),
            call.debug('pkg_resources info: %s',
                       {'url': 'http://my.package.url/pkg_resources',
                        'version': '1.2.3'}),
            call.debug('Final package info: %s',
                       {'url': 'http://my.package.url/pip', 'commit': None,
                        'version': '1.2.3', 'tag': None})
        ]
        assert mock_is_git.mock_calls == [call()]

    def test_is_git_clone_true(self):
        foo_path = '/foo/bar/awslimitchecker/awslimitchecker/versioncheck.pyc'

        with patch.multiple(
                '%s.os.path' % self.mpb,
                abspath=DEFAULT,
                exists=DEFAULT,
        ) as mocks:
            mocks['abspath'].return_value = foo_path
            mocks['exists'].return_value = True
            cls = VersionFinder()
            res = cls._is_git_clone
        assert res is True
        assert mocks['abspath'].call_count == 1
        assert mocks['exists'].mock_calls == [
            call('/foo/bar/awslimitchecker/.git')
        ]

    def test_is_git_clone_false(self):
        foo_path = '/foo/bar/awslimitchecker/awslimitchecker/versioncheck.pyc'

        with patch.multiple(
                '%s.os.path' % self.mpb,
                abspath=DEFAULT,
                exists=DEFAULT,
        ) as mocks:
            mocks['abspath'].return_value = foo_path
            mocks['exists'].return_value = False
            cls = VersionFinder()
            res = cls._is_git_clone
        assert res is False
        assert mocks['abspath'].call_count == 1
        assert mocks['exists'].mock_calls == [
            call('/foo/bar/awslimitchecker/.git')
        ]


class Test_VersionCheck_Funcs(object):
    """
    Mocked unit tests for versioncheck functions
    """

    pb = 'awslimitchecker.versioncheck'

    def test_get_git_url_simple(self):
        cmd_out = '' \
                "origin  git@github.com:jantman/awslimitchecker.git (fetch)\n" \
                "origin  git@github.com:jantman/awslimitchecker.git (push)\n"
        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.return_value = cmd_out
            res = _get_git_url()
        assert res == 'git@github.com:jantman/awslimitchecker.git'
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]

    def test_get_git_url_fork(self):
        cmd_out = "origin  git@github.com:someone/awslimitchecker.git (fetch" \
                  ")\n" \
                  "origin  git@github.com:someone/awslimitchecker.git (push)" \
                  "\n" \
                  "upstream        https://github.com/jantman/awslimitchecke" \
                  "r.git (fetch)\n" \
                  "upstream        https://github.com/jantman/awslimitchecker" \
                  ".git (push)\n"
        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.return_value = cmd_out
            res = _get_git_url()
        assert res == 'git@github.com:someone/awslimitchecker.git'
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]

    def test_get_git_url_no_origin(self):
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
        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.return_value = cmd_out
            res = _get_git_url()
        assert res == 'https://github.com/foo/awslimitchecker.git'
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]

    def test_get_git_url_exception(self):

        def se(foo, stderr=None):
            raise subprocess.CalledProcessError(3, 'mycommand')

        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.side_effect = se
            res = _get_git_url()
        assert res is None
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]

    def test_get_git_url_none(self):
        cmd_out = ''
        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.return_value = cmd_out
            res = _get_git_url()
        assert res is None
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]

    def test_get_git_url_no_fetch(self):
        cmd_out = "mine  git@github.com:someone/awslimitchecker.git (push)" \
                  "\n" \
                  "upstream        https://github.com/jantman/awslimitchecker" \
                  ".git (push)\n" \
                  "another        https://github.com/jantman/awslimitchecker" \
                  ".git (push)\n"
        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.return_value = cmd_out
            res = _get_git_url()
        assert res is None
        assert mock_check_out.mock_calls == [
            call(['git', 'remote', '-v'], stderr=DEVNULL)
        ]

    def test_get_git_tag(self):
        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.return_value = 'mytag'
            res = _get_git_tag('abcd')
        assert res == 'mytag'
        assert mock_check_out.mock_calls == [
            call(['git', 'describe', '--exact-match', '--tags', 'abcd'],
                 stderr=DEVNULL)
        ]

    def test_get_git_tag_commit_none(self):
        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.return_value = 'mytag'
            res = _get_git_tag(None)
        assert res is None
        assert mock_check_out.mock_calls == []

    def test_get_git_tag_no_tags(self):
        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.return_value = ''
            res = _get_git_tag('abcd')
        assert res is None
        assert mock_check_out.mock_calls == [
            call(['git', 'describe', '--exact-match', '--tags', 'abcd'],
                 stderr=DEVNULL)
        ]

    def test_get_git_tag_exception(self):

        def se(foo, stderr=None):
            raise subprocess.CalledProcessError(3, 'mycommand')

        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.side_effect = se
            res = _get_git_tag('abcd')
        assert res is None
        assert mock_check_out.mock_calls == [
            call(['git', 'describe', '--exact-match', '--tags', 'abcd'],
                 stderr=DEVNULL)
        ]

    def test_get_git_commit(self):
        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.return_value = '1234abcd'
            res = _get_git_commit()
        assert res == '1234abcd'
        assert mock_check_out.mock_calls == [
            call(['git', 'rev-parse', '--short', 'HEAD'],
                 stderr=DEVNULL)
        ]

    def test_get_git_commit_exception(self):

        def se(foo):
            raise subprocess.CalledProcessError(3, 'mycommand')

        with patch('%s._check_output' % self.pb) as mock_check_out:
            mock_check_out.side_effect = se
            res = _get_git_commit()
        assert res is None
        assert mock_check_out.mock_calls == [
            call(['git', 'rev-parse', '--short', 'HEAD'],
                 stderr=DEVNULL)
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
    def test_check_output_py26(self):
        mock_p = Mock(returncode=0)
        mock_p.communicate.return_value = ('foo', 'bar')
        with patch('%s.subprocess.Popen' % self.pb) as mock_popen:
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
    def test_check_output_py26_exception(self):
        mock_p = Mock(returncode=2)
        mock_p.communicate.return_value = ('foo', 'bar')
        with patch('%s.subprocess.Popen' % self.pb) as mock_popen:
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
    def test_check_output_py27(self):
        with patch('%s.subprocess.check_output' % self.pb) as mock_check_out:
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
    def test_check_output_py3(self):
        with patch('%s.subprocess.check_output' % self.pb) as mock_check_out:
            mock_check_out.return_value = 'foobar'.encode('utf-8')
            res = _check_output(['foo', 'bar'], stderr='something')
        assert res == 'foobar'
        assert mock_check_out.mock_calls == [
            call(['foo', 'bar'], stderr='something')
        ]
