=============================
Tugboat Pull Request Explorer
=============================

Tugboat is a command line tool for exploring open pull requests on
Github or Github Enterprise, using the Github API.  It generates a
report of all open pull requests for all the repositories it was
requested to examine, sorted by the pull request's last update time.
Each pull request is listed with a link to the pull request, and an
indicator as to whether the pull request is mergeable.

Usage
=====

Tugboat uses ``cli_tools``, and so provides extensive help text,
accessible by using the "--help" argument.  The primary arguments it
needs have to do with authenticating to Github (see the help for
"--username", "--password", and "--github-url"; note that tugboat will
prompt for a password if none is provided).

Tugboat also must be told which repositories to examine; this is done
by passing one or more of the "--repo", "--user", or "--org" options.
(Note that tugboat will generate an empty report if none of these
options are passed.)  Any mix of these options may be used; tugboat
will explore all listed repositories, and all repositories it can see
under the listed users or organizations.
