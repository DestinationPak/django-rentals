# Packaging and releases

django-rentals is published to PyPI, so it's public no matter how many projects use it today. Treat every change as a public release. Before changing anything packaging-related (`pyproject.toml`, module layout, `__init__.py`, dependency ranges) or a public import path or behavior, check it against real installs:

- `pip install django-rentals` still works,
- an editable VCS install (`pip install -e git+https://...#egg=django-rentals`) still resolves,
- `python -m build` and `twine check dist/*` pass.

A change that only works when edited in place inside this repo isn't finished.

## `pyproject.toml`

All metadata lives in `pyproject.toml` (no `setup.py`, `setup.cfg` or `MANIFEST.in`): a PEP 621 `[project]` table plus `[tool.setuptools]` for the `src/` layout and package discovery.

- **The version comes from the git tag.** `src/django_rentals/__init__.py` reads `__version__` with `importlib.metadata.version("django-rentals")`; `setuptools-scm` computes it from `git describe` at build time, so tagging is the version bump and nothing can drift from what's published. Local Docker has no tag history, so the `Dockerfile` sets `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0.dev0`. Tags have no `v` prefix. If `__version__` looks stale locally, delete any `django_rentals.egg-info/` left at the repo root by an old flat-layout install (gitignored, so it survives a fresh checkout): `importlib.metadata` reads its frozen version whenever the repo root is on `sys.path`.
- **`include-package-data` is off.** PEP 621 defaults it to `true`, which with setuptools-scm's git file finder sweeps every tracked file under a package into the wheel, bypassing `packages.find`'s `exclude`. The package ships no data files. Don't re-enable it without checking `python -m zipfile -l dist/*.whl`.
- `django_rentals.tests` (the factories) ships on purpose so projects can use it in their own tests.

## Releasing

Releases are CI-only. Tag the merge commit on `main` and push the tag: `.github/workflows/release.yaml` checks that `python -m setuptools_scm` matches the tag exactly, builds, runs `twine check`, and publishes with PyPI Trusted Publishing (OIDC, no stored token). There's no local publish path: the old `make publish.test`/`publish.prod` duplicated this pipeline with a legacy `setup.py sdist bdist_wheel` and bypassed the version check and OIDC, so it was removed.
