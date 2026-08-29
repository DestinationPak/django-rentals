"""Sphinx configuration for django-rentals."""

from importlib.metadata import version as pkg_version

project = "django-rentals"
author = "Awais Jibran"
copyright = "2026, Awais Jibran"
release = pkg_version("django-rentals")
version = release

extensions = ["myst_parser"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

html_theme = "furo"
