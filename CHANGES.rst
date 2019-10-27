Changelog
=========

1.0.0 (2019-10-27)
------------------

**Important:** in keeping with the scheduled end-of-life of various Python versions, versionfinder now only officially supports Python 3.5 or greater. A DeprecationWarning will be generated when run with versions before 3.5, and they are no longer tested.

* Fix `Issue #7 <https://github.com/jantman/versionfinder/issues/7>`_ where certain new versions of pip throw an AttributeError on import if running in Lambda (or other environments where ``sys.stdin`` is ``None``).
* Stop testing Python 3.3 and drop official support for it.
* Stop testing Python 2.7 and 3.4.
* Add DeprecationWarnings for any Python version < 3.5.
* Multiple pip10 fixes.
* Test fixes:

  * Always install latest versions of ``coverage`` and ``pytest``.
  * Switch docs build to py37
  * Begin testing under py37 and py38

0.1.3 (2018-03-18)
------------------

* Fix minor unhandled exception in previous release.

0.1.2 (2018-03-18)
------------------

* Fix `Issue #5 <https://github.com/jantman/versionfinder/issues/5>`_ where ``import pip`` fails if ``requests`` has previously been imported. Also proactive fix for pip10 changes.
* Multiple test fixes

0.1.1 (2017-06-16)
------------------

* Prevent dieing with an exception if ``git`` is not installed on the system.
* Add hack to ``docs/source/conf.py`` as workaround for https://github.com/sphinx-doc/sphinx/issues/3860
* Add TravisCI testing for py36

0.1.0 (2016-12-04)
------------------

* Initial Release
