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

import unittest

import mock

from tugboat import pulls


class PullRequestTest(unittest.TestCase):
    @mock.patch.object(pulls.PullRequest, '__init__', return_value=None)
    def test_from_repos_no_callback(self, mock_init):
        prs1 = ['pr1_1', 'pr1_2', 'pr1_3']
        prs2 = ['pr2_1', 'pr2_2']
        repo1 = mock.Mock(**{'get_pulls.return_value': prs1})
        repo2 = mock.Mock(**{'get_pulls.return_value': prs2})

        result = pulls.PullRequest._from_repos(
            (r for r in (repo1, repo2)), None)

        self.assertEqual(len(result), 5)
        for pr in result:
            self.assertTrue(isinstance(pr, pulls.PullRequest))
        repo1.get_pulls.assert_called_once_with()
        repo2.get_pulls.assert_called_once_with()
        mock_init.assert_has_calls([
            mock.call(repo1, 'pr1_1'),
            mock.call(repo1, 'pr1_2'),
            mock.call(repo1, 'pr1_3'),
            mock.call(repo2, 'pr2_1'),
            mock.call(repo2, 'pr2_2'),
        ])
        self.assertEqual(mock_init.call_count, 5)

    @mock.patch.object(pulls.PullRequest, '__init__', return_value=None)
    def test_from_repos_with_callback(self, mock_init):
        prs1 = ['pr1_1', 'pr1_2', 'pr1_3']
        prs2 = ['pr2_1', 'pr2_2']
        repo1 = mock.Mock(**{'get_pulls.return_value': prs1})
        repo2 = mock.Mock(**{'get_pulls.return_value': prs2})
        cb = mock.Mock()

        result = pulls.PullRequest._from_repos(
            (r for r in (repo1, repo2)), cb)

        self.assertEqual(len(result), 5)
        for pr in result:
            self.assertTrue(isinstance(pr, pulls.PullRequest))
        repo1.get_pulls.assert_called_once_with()
        repo2.get_pulls.assert_called_once_with()
        mock_init.assert_has_calls([
            mock.call(repo1, 'pr1_1'),
            mock.call(repo1, 'pr1_2'),
            mock.call(repo1, 'pr1_3'),
            mock.call(repo2, 'pr2_1'),
            mock.call(repo2, 'pr2_2'),
        ])
        self.assertEqual(mock_init.call_count, 5)
        cb.assert_has_calls([
            mock.call(0, 2, repo1),
            mock.call(0, 2, repo1, result[:3]),
            mock.call(1, 2, repo2),
            mock.call(1, 2, repo2, result[3:]),
        ])
        self.assertEqual(cb.call_count, 4)

    @mock.patch.object(pulls.PullRequest, '_from_repos', return_value='pulls')
    def test_from_repo(self, mock_from_repos):
        gh = mock.Mock(**{'get_repo.return_value': 'repo'})

        result = pulls.PullRequest.from_repo(gh, 'spam')

        self.assertEqual(result, 'pulls')
        gh.get_repo.assert_called_once_with('spam')
        mock_from_repos.assert_called_once_with(['repo'], None)

    @mock.patch.object(pulls.PullRequest, '_from_repos', return_value='pulls')
    def test_from_repo_callback(self, mock_from_repos):
        gh = mock.Mock(**{'get_repo.return_value': 'repo'})

        result = pulls.PullRequest.from_repo(gh, 'spam', 'call')

        self.assertEqual(result, 'pulls')
        gh.get_repo.assert_called_once_with('spam')
        mock_from_repos.assert_called_once_with(['repo'], 'call')

    @mock.patch.object(pulls.PullRequest, '_from_repos', return_value='pulls')
    def test_from_organization(self, mock_from_repos):
        org = mock.Mock(**{'get_repos.return_value': ['repo1', 'repo2']})
        gh = mock.Mock(**{'get_organization.return_value': org})

        result = pulls.PullRequest.from_organization(gh, 'spam')

        self.assertEqual(result, 'pulls')
        gh.get_organization.assert_called_once_with('spam')
        org.get_repos.assert_called_once_with()
        mock_from_repos.assert_called_once_with(['repo1', 'repo2'], None)

    @mock.patch.object(pulls.PullRequest, '_from_repos', return_value='pulls')
    def test_from_organization_callback(self, mock_from_repos):
        org = mock.Mock(**{'get_repos.return_value': ['repo1', 'repo2']})
        gh = mock.Mock(**{'get_organization.return_value': org})

        result = pulls.PullRequest.from_organization(gh, 'spam', 'call')

        self.assertEqual(result, 'pulls')
        gh.get_organization.assert_called_once_with('spam')
        org.get_repos.assert_called_once_with()
        mock_from_repos.assert_called_once_with(['repo1', 'repo2'], 'call')

    @mock.patch.object(pulls.PullRequest, '_from_repos', return_value='pulls')
    def test_from_user(self, mock_from_repos):
        user = mock.Mock(**{'get_repos.return_value': ['repo1', 'repo2']})
        gh = mock.Mock(**{'get_user.return_value': user})

        result = pulls.PullRequest.from_user(gh, 'spam')

        self.assertEqual(result, 'pulls')
        gh.get_user.assert_called_once_with('spam')
        user.get_repos.assert_called_once_with()
        mock_from_repos.assert_called_once_with(['repo1', 'repo2'], None)

    @mock.patch.object(pulls.PullRequest, '_from_repos', return_value='pulls')
    def test_from_user_callback(self, mock_from_repos):
        user = mock.Mock(**{'get_repos.return_value': ['repo1', 'repo2']})
        gh = mock.Mock(**{'get_user.return_value': user})

        result = pulls.PullRequest.from_user(gh, 'spam', 'call')

        self.assertEqual(result, 'pulls')
        gh.get_user.assert_called_once_with('spam')
        user.get_repos.assert_called_once_with()
        mock_from_repos.assert_called_once_with(['repo1', 'repo2'], 'call')

    @mock.patch.object(pulls.PullRequest, '_from_repos', return_value='pulls')
    def test_from_all(self, mock_from_repos):
        gh = mock.Mock(**{'get_repos.return_value': ['repo1', 'repo2']})

        result = pulls.PullRequest.from_all(gh)

        self.assertEqual(result, 'pulls')
        gh.get_repos.assert_called_once_with()
        mock_from_repos.assert_called_once_with(['repo1', 'repo2'], None)

    @mock.patch.object(pulls.PullRequest, '_from_repos', return_value='pulls')
    def test_from_all_callback(self, mock_from_repos):
        gh = mock.Mock(**{'get_repos.return_value': ['repo1', 'repo2']})

        result = pulls.PullRequest.from_all(gh, 'call')

        self.assertEqual(result, 'pulls')
        gh.get_repos.assert_called_once_with()
        mock_from_repos.assert_called_once_with(['repo1', 'repo2'], 'call')

    def test_init(self):
        pr = pulls.PullRequest('repo', 'pr')

        self.assertEqual(pr._repo, 'repo')
        self.assertEqual(pr._pr, 'pr')
        self.assertEqual(pr._mergeable, None)

    def test_getattr(self):
        pr = pulls.PullRequest('repo', mock.Mock(attr='spam'))

        self.assertEqual(pr.attr, 'spam')

    def test_mergeable_cached(self):
        pr = pulls.PullRequest('repo', mock.Mock(mergeable='mergeable'))
        pr._mergeable = 'cached'

        self.assertEqual(pr.mergeable, 'cached')
        self.assertEqual(pr._mergeable, 'cached')

    def test_mergeable_uncached(self):
        pr = pulls.PullRequest('repo', mock.Mock(mergeable='mergeable'))

        self.assertEqual(pr.mergeable, 'mergeable')
        self.assertEqual(pr._mergeable, 'mergeable')

    def test_mergeable_clear(self):
        pr = pulls.PullRequest('repo', 'pr')
        pr._mergeable = 'cached'

        del pr.mergeable

        self.assertEqual(pr._mergeable, None)

    def test_repo(self):
        pr = pulls.PullRequest('repo', 'pr')

        self.assertEqual(pr.repo, 'repo')

    def test_pr(self):
        pr = pulls.PullRequest('repo', 'pr')

        self.assertEqual(pr.pr, 'pr')
