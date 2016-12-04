"""
versionfinder/tests/test_versioninfo.py

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

import sys
from versionfinder.versioninfo import VersionInfo

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import patch, PropertyMock
else:
    from unittest.mock import patch, PropertyMock

pb = 'versionfinder.versioninfo.VersionInfo'


class TestInit(object):

    def test_init_all(self):
        v = VersionInfo(
            pip_version='pipver',
            pip_url='pipurl',
            pip_requirement='preq',
            pkg_resources_version='prver',
            pkg_resources_url='prurl',
            git_tag='tag',
            git_commit='commit',
            git_remotes={
                'origin': 'ourl'
            },
            git_is_dirty=True
        )
        assert v._pip_version == 'pipver'
        assert v._pip_url == 'pipurl'
        assert v._pip_requirement == 'preq'
        assert v._pkg_resources_version == 'prver'
        assert v._pkg_resources_url == 'prurl'
        assert v._git_tag == 'tag'
        assert v._git_commit == 'commit'
        assert v._git_remotes == {
            'origin': 'ourl'
        }
        assert v._git_is_dirty is True

    def test_init_empty(self):
        v = VersionInfo()
        assert v._pip_version is None
        assert v._pip_url is None
        assert v._pip_requirement is None
        assert v._pkg_resources_version is None
        assert v._pkg_resources_url is None
        assert v._git_tag is None
        assert v._git_commit is None
        assert v._git_remotes is None
        assert v._git_is_dirty is None


class TestAsDict(object):

    def test_dict(self):
        d = {
            'pip_version': 'pipver',
            'pip_url': 'pipurl',
            'pip_requirement': 'preq',
            'pkg_resources_version': 'prver',
            'pkg_resources_url': 'prurl',
            'git_tag': 'tag',
            'git_commit': 'commit',
            'git_remotes': {
                'origin': 'ourl'
            },
            'git_is_dirty': True
        }
        v = VersionInfo(**d)
        assert v.as_dict == d


class TestProperties(object):

    def setup_method(self, _):
        self.cls = VersionInfo(
            pip_version='pipver',
            pip_url='pipurl',
            pip_requirement='preq',
            pkg_resources_version='prver',
            pkg_resources_url='prurl',
            git_tag='tag',
            git_commit='commit',
            git_remotes={
                'origin': 'ourl'
            },
            git_is_dirty=True
        )

    def test_version(self):
        assert self.cls.version == 'pipver'

    def test_version_no_pip(self):
        self.cls._pip_version = None
        assert self.cls.version == 'prver'

    def test_url(self):
        assert self.cls.url == 'pipurl'

    def test_url_no_pip(self):
        self.cls._pip_url = None
        assert self.cls.url == 'prurl'

    def test_pip_version(self):
        assert self.cls.pip_version == 'pipver'

    def test_pip_url(self):
        assert self.cls.pip_url == 'pipurl'

    def test_pip_requirement(self):
        assert self.cls.pip_requirement == 'preq'

    def test_pkg_resources_version(self):
        assert self.cls.pkg_resources_version == 'prver'

    def test_pkg_resources_url(self):
        assert self.cls.pkg_resources_url == 'prurl'

    def test_git_tag(self):
        assert self.cls.git_tag == 'tag'

    def test_git_commit(self):
        assert self.cls.git_commit == 'commit'

    def test_git_remotes(self):
        assert self.cls.git_remotes == {
            'origin': 'ourl'
        }

    def test_git_remote(self):
        assert self.cls.git_remote == 'ourl'

    def test_git_remote_none(self):
        self.cls._git_remotes = None
        assert self.cls.git_remote is None

    def test_git_remote_no_origin(self):
        self.cls._git_remotes = {
            'a': 'rmta',
            'k': 'rmtk',
            'z': 'rmtz'
        }
        assert self.cls.git_remote == 'rmta'

    def test_git_is_dirty(self):
        assert self.cls.git_is_dirty is True

    def test_git_str(self):
        assert self.cls.git_str == 'ourl@tag*'

    def test_git_str_no_git(self):
        self.cls._git_commit = None
        self.cls._git_remotes = None
        assert self.cls.git_str == ''

    def test_git_str_no_tag(self):
        self.cls._git_tag = None
        assert self.cls.git_str == 'ourl@commit*'

    def test_git_str_not_dirty(self):
        self.cls._git_is_dirty = False
        assert self.cls.git_str == 'ourl@tag'

    def test_git_str_pip_req_not_dirty(self):
        self.cls._git_is_dirty = False
        self.cls._pip_requirement = 'git+https://foo'
        assert self.cls.git_str == 'git+https://foo'

    def test_git_str_pip_req_dirty(self):
        self.cls._pip_requirement = 'git+https://foo'
        assert self.cls.git_str == 'git+https://foo*'

    def test_short_str_pip(self):
        assert self.cls.short_str == 'pipver <pipurl>'

    def test_short_str_pkg_resources(self):
        self.cls._pip_version = None
        self.cls._pip_url = None
        assert self.cls.short_str == 'prver <prurl>'

    def test_short_str_none(self):
        with patch('%s.version' % pb, new_callable=PropertyMock) as m_ver:
            with patch('%s.url' % pb, new_callable=PropertyMock) as m_url:
                m_ver.return_value = None
                m_url.return_value = None
                assert self.cls.short_str == ''

    def test_long_str_git(self):
        self.cls._git_is_dirty = False
        with patch('%s.git_str' % pb, new_callable=PropertyMock) as m_git_str:
            with patch('%s.short_str' % pb,
                       new_callable=PropertyMock) as m_short:
                m_git_str.return_value = 'gitstr'
                m_short.return_value = 'shortstr'
                assert self.cls.long_str == 'shortstr (gitstr)'

    def test_long_str_no_git(self):
        with patch('%s.git_str' % pb, new_callable=PropertyMock) as m_git_str:
            with patch('%s.short_str' % pb,
                       new_callable=PropertyMock) as m_short:
                m_git_str.return_value = ''
                m_short.return_value = 'shortstr'
                assert self.cls.long_str == 'shortstr'


class TestRepr(object):

    def test_repr(self):
        v = VersionInfo(
            pip_version='pipver',
            pip_url='pipurl',
            pip_requirement='preq',
            pkg_resources_version='prver',
            pkg_resources_url='prurl',
            git_tag='tag',
            git_commit='commit',
            git_remotes={
                'origin': 'ourl'
            },
            git_is_dirty=True
        )
        s = 'VersionInfo('
        s += 'git_commit=commit, '
        s += 'git_is_dirty=True, '
        s += "git_remotes={'origin': 'ourl'}, "
        s += 'git_tag=tag, '
        s += 'pip_requirement=preq, '
        s += 'pip_url=pipurl, '
        s += 'pip_version=pipver, '
        s += 'pkg_resources_url=prurl, '
        s += 'pkg_resources_version=prver'
        s += ')'
        assert v.__repr__() == s


class TestEq(object):

    def test_equal(self):
        v1 = VersionInfo(
            pip_version='pipver',
            pip_url='pipurl',
            pip_requirement='preq',
            pkg_resources_version='prver',
            pkg_resources_url='prurl',
            git_tag='tag',
            git_commit='commit',
            git_remotes={
                'origin': 'ourl'
            },
            git_is_dirty=True
        )
        v2 = VersionInfo(
            pip_version='pipver',
            pip_url='pipurl',
            pip_requirement='preq',
            pkg_resources_version='prver',
            pkg_resources_url='prurl',
            git_tag='tag',
            git_commit='commit',
            git_remotes={
                'origin': 'ourl'
            },
            git_is_dirty=True
        )
        assert v1 == v2

    def test_not_equal(self):
        v1 = VersionInfo(
            pip_version='pipver',
            pip_url='pipurl',
            pip_requirement='preq',
            pkg_resources_version='prver',
            pkg_resources_url='prurl',
            git_tag='tag',
            git_commit='commit',
            git_remotes={
                'origin': 'ourl'
            },
            git_is_dirty=True
        )
        v2 = VersionInfo(
            pip_version='pipver',
            pip_url='pipurl',
            pip_requirement='preq',
            pkg_resources_version='prver',
            pkg_resources_url='prurl',
            git_tag='tag',
            git_commit='commit',
            git_remotes={
                'origin': 'ourl'
            },
            git_is_dirty=False
        )
        v3 = VersionInfo(
            pip_version='pipver',
            pip_url='pipurl',
            pip_requirement='preq',
            pkg_resources_version='prver',
            pkg_resources_url='prurl',
            git_tag='tag',
            git_commit='commit',
            git_remotes={
                'origin': 'ourl2'
            },
            git_is_dirty=True
        )
        assert v1 != v2
        assert v1 != v3
