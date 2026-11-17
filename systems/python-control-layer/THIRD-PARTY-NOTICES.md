# Third-party dependencies

The first-party application source is MIT licensed. Dependencies are separately
obtained from PyPI; the Python SDK and Linux image are separately obtained from
their upstreams. No dependency code, wheel, interpreter or container image is
redistributed in this source ZIP.

DEPENDENCIES.json records exact package versions, upstream metadata URLs and
reported license expressions/classifiers for the complete validation lock,
including platform-conditional packages. These packages retain their upstream
licenses. Follow their metadata/license links and installed distribution notices
for redistribution obligations. Metadata is a release review aid, not a replacement
for an upstream license or legal advice.

The universal dependency locks were generated with [uv](https://github.com/astral-sh/uv),
version 0.13.8. The advisory check used [pip-audit](https://github.com/pypa/pip-audit),
version 2.10.1, against exact package versions. Those review tools are not required
by the running health service and are not bundled.

Native qualification pins complete [Python Build Standalone](https://github.com/astral-sh/python-build-standalone)
SDK archives. Docker qualification pins the [official Python image](https://hub.docker.com/_/python)
by OCI index digest. These are separate upstream distributions with their own
licenses and component notices. No independent binary rebuild or library security
certification is claimed.
