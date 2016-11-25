versionfinder
=============

.. image:: https://img.shields.io/github/forks/jantman/versionfinder.svg
   :alt: GitHub Forks
   :target: https://github.com/jantman/versionfinder/network

.. image:: https://img.shields.io/github/issues/jantman/versionfinder.svg
   :alt: GitHub Open Issues
   :target: https://github.com/jantman/versionfinder/issues

.. image:: https://secure.travis-ci.org/jantman/versionfinder.png?branch=master
   :target: http://travis-ci.org/jantman/versionfinder
   :alt: travis-ci for master branch

.. image:: https://codecov.io/github/jantman/versionfinder/coverage.svg?branch=master
   :target: https://codecov.io/github/jantman/versionfinder?branch=master
   :alt: coverage report for master branch

.. image:: https://readthedocs.org/projects/versionfinder/badge/?version=latest
   :target: https://readthedocs.org/projects/versionfinder/?badge=latest
   :alt: sphinx documentation for latest release

.. image:: http://www.repostatus.org/badges/latest/active.svg
   :alt: Project Status: Active – The project has reached a stable, usable state and is being actively developed.
   :target: http://www.repostatus.org/#active

Python package to find the version of another package/distribution, whether installed via pip, setuptools or git

Overview
--------

versionfinder is a library intended to identify the version details of a specified Python
distribution, whether it was installed via pip, setuptools or git. In most cases, the
package to be identified will be the caller of versionfinder. This is intended to
allow packages to determine what version they are, beyond what is simply coded
in the package:

* For packages installed via pip, return the exact requirement that was installed,
  even if it was a source control URL (editable or not).
* For packages installed via setuptools, return the installed version.
* For packages that are a git clone, return the URL, commit, tag, and whether the
  repository is dirty (modified) or not.

This is mainly intended for projects that need to display their version information
to users (i.e. for use in filing bug reports or support requests) and wish to be as
specific as possible, including whether the package was installed from a fork, a specific
tag or commit from a git repo, or has local changes not committed to git.

Requirements
------------

* Python 2.6, 2.7, or Python 3.x

Usage
-----

@TODO

Bugs and Feature Requests
-------------------------

Bug reports and feature requests are happily accepted via the `GitHub Issue Tracker <https://github.com/jantman/versionfinder/issues>`_. Pull requests are
welcome. Issues that don't have an accompanying pull request will be worked on
as my time and priority allows.

Development
===========

To install for development:

1. Fork the `versionfinder <https://github.com/jantman/versionfinder>`_ repository on GitHub
2. Create a new branch off of master in your fork.

.. code-block:: bash

    $ virtualenv versionfinder
    $ cd versionfinder && source bin/activate
    $ pip install -e git+git@github.com:YOURNAME/versionfinder.git@BRANCHNAME#egg=versionfinder
    $ cd src/versionfinder

The git clone you're now in will probably be checked out to a specific commit,
so you may want to ``git checkout BRANCHNAME``.

Guidelines
----------

* pep8 compliant with some exceptions (see pytest.ini)
* 100% test coverage with pytest (with valid tests)

Testing
-------

Testing is done via `pytest <http://pytest.org/latest/>`_, driven by `tox <http://tox.testrun.org/>`_.

* testing is as simple as:

  * ``pip install tox``
  * ``tox``

* If you want to pass additional arguments to pytest, add them to the tox command line after "--". i.e., for verbose pytext output on py27 tests: ``tox -e py27 -- -v``

Acceptance Tests
----------------

Versionfinder has a suite of acceptance tests that create virtualenvs, install a
test package (`versionfinder-test-pkg <https://github.com/jantman/versionfinder-test-pkg>`_) in them,
and then call ``versionfinder.find_version()`` from multiple locations in the package, printing a JSON-serialized
dict of the results of each call (and an exception, if one was caught). For further information
on the acceptance tests, see ``versionfinder/tests/test_acceptance.py``.

Currently-tested scenarios are:

* Pip
  * Install from local git clone
  * Install editable from local git clone
  * Install editable from local git clone then change a file (dirty)
  * Install editable from local git clone then commit and tag
  * Install editable from local git clone checked out to a tag
  * Install editable from local git clone checked out to a commit
  * Install editable from local git clone with multiple remotes
  * Install from sdist
  * Install from sdist with pip 1.5.4
  * Install from wheel
  * Install from git URL
  * Install from git URL with commit
  * Install from git URL with tag
  * Install from git URL with branch
  * Install editable from git URL
  * Install editable from git URL with multiple remotes
  * Install editable from git URL and then change a file in the clone (dirty)
  * Install editable from git URL with commit
  * Install editable from git URL with tag
  * Install editable from git URL with branch
  * Install sdist in a venv that's also a git repo
  * Install wheel in a venv that's also a git repo
* setuptools / setup.py
  * setup.py develop
  * setup.py install

@TODO:

- install from a fork (pip git editable; with and without upstream remote)
- pip install egg; egg with venv in git repo
- easy_install https://setuptools.readthedocs.io/en/latest/easy_install.html
  - tarball
  - egg
  - source directory
  - each of those with the venv in a git repo

Release Checklist
-----------------

1. Open an issue for the release; cut a branch off master for that issue.
2. Confirm that there are CHANGES.rst entries for all major changes.
3. Ensure that Travis tests passing in all environments.
4. Ensure that test coverage is no less than the last release (ideally, 100%).
5. Increment the version number in versionfinder/version.py and add version and release date to CHANGES.rst, then push to GitHub.
6. Confirm that README.rst renders correctly on GitHub.
7. Upload package to testpypi:

   * Make sure your ~/.pypirc file is correct (a repo called ``test`` for https://testpypi.python.org/pypi)
   * ``rm -Rf dist``
   * ``python setup.py register -r https://testpypi.python.org/pypi``
   * ``python setup.py sdist bdist_wheel``
   * ``twine upload -r test dist/*``
   * Check that the README renders at https://testpypi.python.org/pypi/versionfinder

8. Create a pull request for the release to be merged into master. Upon successful Travis build, merge it.
9. Tag the release in Git, push tag to GitHub:

   * tag the release. for now the message is quite simple: ``git tag -a X.Y.Z -m 'X.Y.Z released YYYY-MM-DD'``
   * push the tag to GitHub: ``git push origin X.Y.Z``

11. Upload package to live pypi:

    * ``twine upload dist/*``

10. make sure any GH issues fixed in the release were closed.

License and Disclaimer
----------------------

This software is licensed under the `GNU Lesser General Public License (LGPL) 3.0 <https://www.gnu.org/licenses/lgpl-3.0.en.html>`_.