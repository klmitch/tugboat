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


class PullRequest(object):
    """
    Wrap a ``github.PullRequest.PullRequest`` object.  This provides
    some caching to reduce the number of round trips necessary when
    processing a list of pull requests.
    """

    @classmethod
    def _from_repos(cls, repos, repo_callback):
        """
        Given a list of repositories, builds and returns a list of all
        pull requests in those repositories.

        :param repos: A sequence of repositories.
        :param repo_callback: A callback to invoke for each repository
                              visited.  The callback will be called
                              twice.  The first time, it will be
                              passed the repository index, the total
                              length of the list of repositories, and
                              the ``github.Repository.Repository``
                              object; this call will be made prior to
                              retrieving the list of pull requests.
                              The second call will be made after
                              retrieving the list of pull requests,
                              and will include that list as the fourth
                              argument.

        :returns: A list of ``PullRequest`` objects.
        """

        repos = list(repos)
        pulls = []
        for idx, repo in enumerate(repos):
            # Emit a status update
            if repo_callback:
                repo_callback(idx, len(repos), repo)

            repo_pulls = [cls(repo, pr) for pr in repo.get_pulls()]

            # Emit a second status update with the pulls
            if repo_callback:
                repo_callback(idx, len(repos), repo, repo_pulls)

            pulls.extend(repo_pulls)

        return pulls

    @classmethod
    def from_repo(cls, gh, repo_name, repo_callback=None):
        """
        Retrieve all open pull requests from the named repository.

        :param gh: A ``github.Github`` handle.
        :param repo_name: The full name of the repository.
        :param repo_callback: A callback to invoke for each repository
                              visited.  The callback will be called
                              twice.  The first time, it will be
                              passed the repository index, the total
                              length of the list of repositories, and
                              the ``github.Repository.Repository``
                              object; this call will be made prior to
                              retrieving the list of pull requests.
                              The second call will be made after
                              retrieving the list of pull requests,
                              and will include that list as the fourth
                              argument.

        :returns: A list of ``PullRequest`` objects for each open pull
                  request against the named repository.  The list is
                  not sorted.
        """

        # This is pretty simple...
        return cls._from_repos([gh.get_repo(repo_name)], repo_callback)

    @classmethod
    def from_organization(cls, gh, org_name, repo_callback=None):
        """
        Retrieve all open pull requests from all repositories in a given
        organization.

        :param gh: A ``github.Github`` handle.
        :param org_name: The name of the organization.
        :param repo_callback: A callback to invoke for each repository
                              visited.  The callback will be called
                              twice.  The first time, it will be
                              passed the repository index, the total
                              length of the list of repositories, and
                              the ``github.Repository.Repository``
                              object; this call will be made prior to
                              retrieving the list of pull requests.
                              The second call will be made after
                              retrieving the list of pull requests,
                              and will include that list as the fourth
                              argument.

        :returns: A list of ``PullRequest`` objects for each open pull
                  request against all repositories in the named
                  organization.  The list is not sorted.
        """

        # First, get the organization
        org = gh.get_organization(org_name)

        # Now build and return the list of pull requests
        return cls._from_repos(org.get_repos(), repo_callback)

    @classmethod
    def from_user(cls, gh, user_name, repo_callback=None):
        """
        Retrieve all open pull requests from all repositories belonging to
        a given user.

        :param gh: A ``github.Github`` handle.
        :param user_name: The user login name.
        :param repo_callback: A callback to invoke for each repository
                              visited.  The callback will be called
                              twice.  The first time, it will be
                              passed the repository index, the total
                              length of the list of repositories, and
                              the ``github.Repository.Repository``
                              object; this call will be made prior to
                              retrieving the list of pull requests.
                              The second call will be made after
                              retrieving the list of pull requests,
                              and will include that list as the fourth
                              argument.

        :returns: A list of ``PullRequest`` objects for each open pull
                  request against all repositories belonging to the
                  named user.  The list is not sorted.
        """

        # First, get the user
        user = gh.get_user(user_name)

        # Now build and return the list of pull requests
        return cls._from_repos(user.get_repos(), repo_callback)

    @classmethod
    def from_all(cls, gh, repo_callback=None):
        """
        Retrieve all open pull requests from all repositories on Github.

        :param gh: A ``github.Github`` handle.
        :param repo_callback: A callback to invoke for each repository
                              visited.  The callback will be called
                              twice.  The first time, it will be
                              passed the repository index, the total
                              length of the list of repositories, and
                              the ``github.Repository.Repository``
                              object; this call will be made prior to
                              retrieving the list of pull requests.
                              The second call will be made after
                              retrieving the list of pull requests,
                              and will include that list as the fourth
                              argument.

        :returns: A list of ``PullRequest`` objects for each open pull
                  request against all repositories on Github which are
                  accessible to the user used when constructing
                  ``gh``.
        """

        # Build and return the list of all pull requests
        return cls._from_repos(gh.get_repos(), repo_callback)

    def __init__(self, repo, pr):
        """
        Initialize a ``PullRequest`` object.

        :param repo: The ``github.Repository.Repository`` object
                     describing the repository the pull request is
                     against.
        :param pr: The ``github.PullRequest.PullRequest`` object
                   describing the pull request.
        """

        self._repo = repo
        self._pr = pr

        self._mergeable = None

    def __getattr__(self, name):
        """
        Delegate attribute access to the underlying
        ``github.PullRequest.PullRequest`` object.

        :param name: The name of the desired attribute.

        :returns: The value of the desired attribute.
        """

        return getattr(self._pr, name)

    @property
    def mergeable(self):
        """
        Determine if the pull request is mergeable.  This is cached to
        inhibit round-tripping.  Use ``del x.mergeable`` to force a
        cache invalidation.
        """

        # Do we have the value cached?
        if self._mergeable is None:
            self._mergeable = self._pr.mergeable

        return self._mergeable

    @mergeable.deleter
    def mergeable(self):
        """
        Invalidate the caching of ``mergeable``.  This will force a round
        trip next time the ``mergeable`` property is accessed,
        yielding the most up-to-date value.
        """

        self._mergeable = None

    @property
    def repo(self):
        """
        Return the underlying ``github.Repository.Repository`` object that
        the pull request is against.
        """

        return self._repo

    @property
    def pr(self):
        """
        Return the underlying ``github.PullRequest.PullRequest`` object.
        """

        return self._pr
