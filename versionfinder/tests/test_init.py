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
from versionfinder import find_version

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import patch, call, Mock
else:
    from unittest.mock import patch, call, Mock


class TestFindVersion(object):

    def test_caller_passed(self):
        m_frame = Mock()
        m_result = Mock()
        with patch('versionfinder.VersionFinder', autospec=True) as mock_vf:
            with patch('versionfinder.inspect.stack') as mock_stack:
                mock_vf.return_value.find_package_version.\
                    return_value = m_result
                res = find_version('pname', caller_frame=m_frame)
        assert mock_vf.mock_calls == [
            call('pname', caller_frame=m_frame),
            call().find_package_version()
        ]
        assert mock_stack.mock_calls == []
        assert res == m_result

    def test_caller_not_passed(self):
        m_frame = Mock()
        m_result = Mock()
        with patch('versionfinder.VersionFinder', autospec=True) as mock_vf:
            with patch('versionfinder.inspect.stack') as mock_stack:
                mock_vf.return_value.find_package_version.\
                    return_value = m_result
                mock_stack.return_value = [None, [m_frame]]
                res = find_version('pname')
        assert mock_vf.mock_calls == [
            call('pname', caller_frame=m_frame),
            call().find_package_version()
        ]
        assert mock_stack.mock_calls == [call()]
        assert res == m_result
