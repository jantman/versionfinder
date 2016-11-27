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

from versionfinder.versioninfo import VersionInfo


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
