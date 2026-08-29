# Security Policy

## Supported Versions

Only the latest published release on [PyPI](https://pypi.org/project/django-rentals/)
receives security fixes. There is no long-term-support branch at this stage.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for a security vulnerability.

Instead, use one of:

- GitHub's private vulnerability reporting: open the "Security" tab on this
  repository and select "Report a vulnerability".
- Email awaisdar001@gmail.com with a description of the issue, steps to
  reproduce, and its potential impact.

This is a small, single-maintainer project - please allow a few days for an
initial response. Once a report is confirmed, a fix will be released as a new
PATCH version (or MINOR if a behavior change is unavoidable) and credited in
`CHANGELOG.md`, unless you ask to remain anonymous.

## Scope notes

`django_rentals.RentalBooking` stores guest-provided personal data (name,
email). This package itself has no authentication/authorization layer of its
own by design (see `CLAUDE.md`'s "Tenancy-oblivious, on purpose" note) -
access control for that data is the responsibility of whatever project
installs this app. Reports about the *absence* of tenancy/permission
enforcement in this package aren't vulnerabilities in the usual sense (it's a
documented architectural choice), but reports about data leaking *within*
this package's own endpoints (e.g. the guest booking lookup returning another
guest's booking, or the authenticated booking retrieve/update/cancel endpoint
not actually scoping to `created_by=request.user`) are very much in scope.
