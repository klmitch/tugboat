# Copyright 2014 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the
#    License. You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing,
#    software distributed under the License is distributed on an "AS
#    IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#    express or implied. See the License for the specific language
#    governing permissions and limitations under the License.

from __future__ import print_function

import argparse
import datetime
import getpass
import os
import sys

import cli_tools
import github

from tugboat import pulls


class RepoSummary(object):
    """
    A container for information about repositories.  This is used by
    ``report()`` to maintain a count of pull requests and mergeable
    pull requests for reporting in the final summary data.
    """

    def __init__(self, name):
        """
        Initialize a ``RepoSummary`` object.

        :param name: The full name of the repository.
        """

        self.name = name
        self.pulls = 0
        self.mergeable = 0

    def __iadd__(self, other):
        """
        Add the pull request to the summary.

        :param other: The pull request to add to the summary.

        :returns: The ``RepoSummary`` object.
        """

        # Count it
        self.pulls += 1

        # Is it mergeable?
        if other.mergeable:
            self.mergeable += 1

        return self


# This maps the target name used in an argument declaration to the
# routine used to find the open pull requests for that target
targets = {
    'repo': pulls.PullRequest.from_repo,
    'organization': pulls.PullRequest.from_organization,
    'user': pulls.PullRequest.from_user,
}


class RepoAction(argparse.Action):
    """
    An ``argparse.Action`` subclass used for command line arguments
    that are used in indicating which repositories to report open pull
    requests on.
    """

    def __init__(self, option_strings, dest, **kwargs):
        """
        Initialize a ``RepoAction`` object.

        :param option_strings: A list of option strings.
        :param dest: The target attribute to store the option values
                     in.
        :param target: The target the option specifies.  Must be one
                       of the keys from the ``targets`` dictionary.
                       Defaults to "repo" if not provided.
        """

        # Need the target information
        target = kwargs.pop('target', 'repo')

        # Initialize the Action
        super(RepoAction, self).__init__(option_strings, dest, **kwargs)

        # Save the target information
        self.target = target

    def __call__(self, parser, namespace, values, option_string=None):
        """
        Called when encountering an argument bound to the ``RepoAction``
        object.

        :param parser: An ``argparse.ArgumentParser`` object.
        :param namespace: The ``argparse.Namespace`` into which to
                          store argument values.
        :param values: The values that were passed for the argument.
        :param option_string: The string used to invoke the option.
        """

        # Append the appropriate value to the namespace
        items = getattr(namespace, self.dest, [])
        items.append((self.target, values))
        setattr(namespace, self.dest, items)


@cli_tools.argument_group(
    'auth',
    title='Authentication-related Options',
    description='Options used to authenticate to Github.',
)
@cli_tools.argument(
    '--username', '-u',
    default=getpass.getuser(),
    help='Username for accessing the Github API.  Defaults to "%(default)s".',
    group='auth',
)
@cli_tools.argument(
    '--password', '-p',
    help='Password or personal access token for accessing the Github API.  '
    'If not provided, it will be prompted for.',
    group='auth',
)
@cli_tools.argument(
    '--github-url', '-g',
    default='https://api.github.com',
    help='API URL for accessing the Github API.  Defaults to "%(default)s".',
    group='auth',
)
@cli_tools.argument_group(
    'repo',
    title='Repositories to Report on',
    description='Options used to identify specific repositories to generate '
    'reports on.  These options may be used multiple times.',
)
@cli_tools.argument(
    '--repo', '-r',
    dest='repos',
    action=RepoAction,
    default=[],
    help='Identify a specific repository to generate a report for.  The '
    'full repository name must be provided, e.g., "<login>/<repo>".',
    group='repo',
)
@cli_tools.argument(
    '--user', '-U',
    dest='repos',
    action=RepoAction,
    help='Identify a user to generate a report for.  The user login name '
    'must be provided.  The report will include all visible repositories '
    'belonging to that user.',
    group='repo',
    target='user',
)
@cli_tools.argument(
    '--org', '-o',
    dest='repos',
    action=RepoAction,
    help='Identify an organization to generate a report for.  The '
    'organization name must be provided.  The report will include all '
    'visible repositories belonging to that user.',
    group='repo',
    target='organization',
)
@cli_tools.argument(
    '--output', '-O',
    default='-',
    help='Specify the file name the report should be emitted to.  If not '
    'provided, or if specified as "-", the report will be emitted to '
    'standard output.',
)
@cli_tools.argument(
    '--verbose', '-v',
    action='store_const',
    default=1,
    const=2,
    help='Request verbose output.  This will cause status messages to be '
    'emitted while producing the report.',
)
@cli_tools.argument(
    '--quiet', '-q',
    dest='verbose',
    action='store_const',
    const=0,
    help='Request quiet output.  This will suppress all status messages, '
    'emitting only the final report.',
)
@cli_tools.argument(
    '--debug', '-d',
    action='store_true',
    help='Enable debugging mode.  If errors occur, a more detailed output '
    'will be emitted.  This does not affect verbosity.'
)
def report(gh, repos, stream=sys.stdout, repo_callback=None):
    """
    Generate a report of all open pull requests on the specified
    repositories (see the "--repo", "--user", and "--org" options for
    how to specify repositories).

    :param gh: A ``github.Github`` handle for accessing the Github
               API.
    :param repos: A list of tuples specifying repositories to obtain
                  the report on.  For each element of the list, the
                  first element of the tuple is one of "repo", "user",
                  or "organization", and the second element is the
                  name of that repository, user, or organization,
                  respectively.
    :param stream: The output stream to receive the report.  Defaults
                   to ``sys.stdout``.
    :param repo_callback: A callback to invoke for each repository
                          visited.  The callback will be called twice.
                          The first time, it will be passed the
                          repository index, the total length of the
                          list of repositories, and the
                          ``github.Repository.Repository`` object;
                          this call will be made prior to retrieving
                          the list of pull requests.  The second call
                          will be made after retrieving the list of
                          pull requests, and will include that list as
                          the fourth argument.
    """

    start = datetime.datetime.now()

    # Build the list of pull requests
    pulls = []
    for target, name in repos:
        # Emit some status information
        if repo_callback:
            print(u'Looking up %s "%s"...' % (target, name),
                  file=sys.stderr)

        repo_pulls = targets[target](gh, name, repo_callback)

        pulls.extend(repo_pulls)

    # Now we need to sort the list of pulls...
    pulls.sort(key=lambda x: x.updated_at)

    # Emit one last piece of status information
    if repo_callback:
        print(u'Generating report...', file=sys.stderr)

    # Don't do anything if there are no pulls
    if not pulls:
        print(u"No open pull requests", file=stream)
        return

    # Emit a summary
    print(u"Open PRs: %d (%d mergeable); oldest last updated %s" %
          (len(pulls), sum(1 for pull in pulls if pull.mergeable),
           pulls[0].updated_at), file=stream)

    # Generate the report of pulls
    repos = {}
    for pull in pulls:
        print(u"\n"
              u"Pull request {pull.repo.full_name}#{pull.number}:\n"
              u"    URL: {pull.html_url}\n"
              u"    Merge {pull.head.label} -> {pull.base.label}\n"
              u"    Proposed {pull.created_at} by {username} "
              u"({pull.user.login})\n"
              u"    Last updated: {pull.updated_at}\n"
              u"    Mergeable: {mergeable}".format(
                  pull=pull,
                  mergeable=('yes' if pull.mergeable else 'no'),
                  username=(pull.user.name or '<unknown>')).encode('utf-8'),
              file=stream)

        # Add repository breakdown data
        repos.setdefault(pull.repo.full_name, RepoSummary(pull.repo.full_name))
        repos[pull.repo.full_name] += pull

    # Generate the repository breakdown
    print((u"\nRepositories with open pull requests: %d\n"
          "Breakdown by repository:" % len(repos)).encode('utf-8'),
          file=stream)
    for summary in sorted(repos.values(), key=lambda x: x.name):
        print((u"    Open PRs for %s: %d (%d mergeable)" %
               (summary.name, summary.pulls,
                summary.mergeable)).encode('utf-8'),
              file=stream)

    # Emit the time data
    end = datetime.datetime.now()
    print((u"\nReport generated in %s at %s" %
           (end - start, start)).encode('utf-8'),
          file=stream)


def _normal_callback(idx, count, repo, pulls=None):
    """
    A ``repo_callback`` callback to implement "normal" behavior.  This
    implementation emits a status line indicating the name of the
    repository being processed.

    :param idx: The index of the repository in the list being
                processed.
    :param count: The number of repositories in the list being
                  processed.
    :param repo: The repository being processed.
    :param pulls: The list of ``tugboat.pulls.PullRequest`` objects
                  for all open pull requests on the repository.
    """

    if pulls is None:
        print(u'Processing repository "%s" (%d/%d)...' %
              (repo.full_name, idx + 1, count), file=sys.stderr)


def _verbose_callback(idx, count, repo, pulls=None):
    """
    A ``repo_callback`` callback to implement "verbose" ("-v")
    behavior.  This implementation emits a status line indicating the
    name of the repository being processed, then indicates the total
    number of pull requests and counts the number of mergeable pull
    requests.

    :param idx: The index of the repository in the list being
                processed.
    :param count: The number of repositories in the list being
                  processed.
    :param repo: The repository being processed.
    :param pulls: The list of ``tugboat.pulls.PullRequest`` objects
                  for all open pull requests on the repository.
    """

    if pulls is None:
        print(u'Processing repository "%s" (%d/%d)...' %
              (repo.full_name, idx + 1, count), file=sys.stderr, end=' ')
    else:
        print(u'%d pulls' % len(pulls), file=sys.stderr, end=' ')
        print(u'(%d mergeable)' % sum(1 for pull in pulls if pull.mergeable),
              file=sys.stderr)


# Used to translate the verbosity level into an appropriate verbosity
# callback
verbosity = [None, _normal_callback, _verbose_callback]


@report.processor
def _process_report(args):
    """
    A ``cli_tools`` processor that adapts between the command line
    interface and the ``report()`` function.  The processor obtains a
    ``github.Github`` object, using the authentication data collected
    by the argument processor; it then selects the correct output
    stream and ``repo_callback`` function for the verbosity level.
    After ``report()`` returns, it ensures that the output stream is
    closed, if required.

    :param args: The ``argparse.Namespace`` object constructed by
                 ``cli_tools``.

    :returns: A ``cli_tools`` processor generator.
    """

    # Get the user's password
    password = args.password
    if not password:
        password = getpass.getpass(u'Password for %s> ' % args.username)

    # Create a github handle
    args.gh = github.Github(args.username, password, args.github_url)

    # Select the correct output stream
    if args.output == '-':
        args.stream = sys.stdout
        close = False
    else:
        args.stream = open(args.output, 'w')
        close = True

    # Select the correct verbosity
    args.repo_callback = verbosity[args.verbose]

    # Generate the report as requested
    try:
        yield
    finally:
        # Make sure the stream gets closed
        if close:
            args.stream.close()
