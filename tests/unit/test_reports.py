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

import datetime
import sys
import unittest

import mock
import six
from six.moves import builtins

from tugboat import reports


class PullSummaryTest(unittest.TestCase):
    def test_init(self):
        result = reports.PullSummary()

        self.assertEqual(result.oldest, None)
        self.assertEqual(result.youngest, None)
        self.assertEqual(result.least_recent, None)
        self.assertEqual(result.most_recent, None)

    def test_add_unset(self):
        pull = mock.Mock(created_at=5, updated_at=5)
        summary = reports.PullSummary()

        summary.add_pull(pull)

        self.assertEqual(summary.oldest, pull)
        self.assertEqual(summary.youngest, pull)
        self.assertEqual(summary.least_recent, pull)
        self.assertEqual(summary.most_recent, pull)

    def test_add_older(self):
        pull = mock.Mock(created_at=5, updated_at=5)
        other = mock.Mock(created_at=4, updated_at=5)
        summary = reports.PullSummary()
        summary.oldest = pull
        summary.youngest = pull
        summary.least_recent = pull
        summary.most_recent = pull

        summary.add_pull(other)

        self.assertEqual(summary.oldest, other)
        self.assertEqual(summary.youngest, pull)
        self.assertEqual(summary.least_recent, pull)
        self.assertEqual(summary.most_recent, pull)

    def test_add_younger(self):
        pull = mock.Mock(created_at=5, updated_at=5)
        other = mock.Mock(created_at=6, updated_at=5)
        summary = reports.PullSummary()
        summary.oldest = pull
        summary.youngest = pull
        summary.least_recent = pull
        summary.most_recent = pull

        summary.add_pull(other)

        self.assertEqual(summary.oldest, pull)
        self.assertEqual(summary.youngest, other)
        self.assertEqual(summary.least_recent, pull)
        self.assertEqual(summary.most_recent, pull)

    def test_add_less_recent(self):
        pull = mock.Mock(created_at=5, updated_at=5)
        other = mock.Mock(created_at=5, updated_at=4)
        summary = reports.PullSummary()
        summary.oldest = pull
        summary.youngest = pull
        summary.least_recent = pull
        summary.most_recent = pull

        summary.add_pull(other)

        self.assertEqual(summary.oldest, pull)
        self.assertEqual(summary.youngest, pull)
        self.assertEqual(summary.least_recent, other)
        self.assertEqual(summary.most_recent, pull)

    def test_add_more_recent(self):
        pull = mock.Mock(created_at=5, updated_at=5)
        other = mock.Mock(created_at=5, updated_at=6)
        summary = reports.PullSummary()
        summary.oldest = pull
        summary.youngest = pull
        summary.least_recent = pull
        summary.most_recent = pull

        summary.add_pull(other)

        self.assertEqual(summary.oldest, pull)
        self.assertEqual(summary.youngest, pull)
        self.assertEqual(summary.least_recent, pull)
        self.assertEqual(summary.most_recent, other)

    @mock.patch.object(reports.PullSummary, 'add_pull')
    def test_add_pulls(self, mock_add_pull):
        summary = reports.PullSummary()

        result = summary.add_pulls(['pr1', 'pr2', 'pr3'])

        self.assertEqual(result, ['pr1', 'pr2', 'pr3'])
        mock_add_pull.assert_has_calls([
            mock.call('pr1'),
            mock.call('pr2'),
            mock.call('pr3'),
        ])
        self.assertEqual(mock_add_pull.call_count, 3)


class RepoSummaryTest(unittest.TestCase):
    def test_init(self):
        result = reports.RepoSummary('repo')

        self.assertEqual(result.name, 'repo')
        self.assertEqual(result.pulls, 0)
        self.assertEqual(result.mergeable, 0)

    def test_iadd_unmergeable(self):
        summary = reports.RepoSummary('repo')
        pull = mock.Mock(mergeable=False)

        summary += pull

        self.assertEqual(summary.pulls, 1)
        self.assertEqual(summary.mergeable, 0)

    def test_iadd_mergeable(self):
        summary = reports.RepoSummary('repo')
        pull = mock.Mock(mergeable=True)

        summary += pull

        self.assertEqual(summary.pulls, 1)
        self.assertEqual(summary.mergeable, 1)


class FormatAgeTest(unittest.TestCase):
    def test_normal(self):
        now = datetime.datetime(2000, 1, 1, 0, 0, 0)
        time = datetime.datetime(1999, 12, 31, 0, 0, 0)

        result = reports.format_age(now, time, "<%s>")

        self.assertEqual(result, '<1 day, 0:00:00>')

    def test_equal(self):
        now = datetime.datetime(2000, 1, 1, 0, 0, 0)
        time = datetime.datetime(2000, 1, 1, 0, 0, 0)

        result = reports.format_age(now, time, "<%s>")

        self.assertEqual(result, '')

    def test_negative(self):
        now = datetime.datetime(2000, 1, 1, 0, 0, 0)
        time = datetime.datetime(2000, 1, 2, 0, 0, 0)

        result = reports.format_age(now, time, "<%s>")

        self.assertEqual(result, '')


class RepoActionTest(unittest.TestCase):
    @mock.patch('argparse.Action.__init__', return_value=None)
    def test_init_no_target(self, mock_init):
        result = reports.RepoAction('strings', 'dest', a=1, b=2, c=3)

        self.assertEqual(result.target, 'repo')
        mock_init.assert_called_once_with('strings', 'dest', a=1, b=2, c=3)

    @mock.patch('argparse.Action.__init__', return_value=None)
    def test_init_with_target(self, mock_init):
        result = reports.RepoAction('strings', 'dest', a=1, b=2, c=3,
                                    target='organization')

        self.assertEqual(result.target, 'organization')
        mock_init.assert_called_once_with('strings', 'dest', a=1, b=2, c=3)

    @mock.patch('argparse.Action.__init__', return_value=None)
    def test_call(self, mock_init):
        action = reports.RepoAction('strings', 'dest', target='user')
        action.dest = 'dest'
        namespace = mock.Mock(spec=[])

        action('parser', namespace, 'spam')
        action('parser', namespace, 'foo')

        self.assertEqual(namespace.dest, [('user', 'spam'), ('user', 'foo')])


class SortKeysTest(unittest.TestCase):
    def test_created(self):
        pull = mock.Mock(created_at=5)

        result = reports.sort_keys['created'](pull)

        self.assertEqual(result, 5)

    def test_updated(self):
        pull = mock.Mock(updated_at=5)

        result = reports.sort_keys['updated'](pull)

        self.assertEqual(result, 5)

    def test_repo(self):
        pull = mock.Mock(**{'repo.full_name': 'some/repo', 'number': 5})

        result = reports.sort_keys['repo'](pull)

        self.assertEqual(result, ('some/repo', 5))


class ReportTest(unittest.TestCase):
    maxDiff = None

    @mock.patch('datetime.datetime', mock.Mock(utcnow=mock.Mock(side_effect=[
        80,
        82,
    ])))
    @mock.patch.dict(reports.targets, clear=True)
    @mock.patch.object(sys, 'stderr', six.StringIO())
    @mock.patch.object(reports, 'format_age',
                       side_effect=lambda x, y, z: z % (x - y))
    def test_basic(self, mock_format_age):
        prs = {
            'repo1#1': mock.Mock(**{
                'user.name': None,
                'mergeable': False,
                'created_at': 10,
                'updated_at': 90,
            }),
            'repo1#2': mock.Mock(**{
                'user.name': None,
                'mergeable': True,
                'created_at': 20,
                'updated_at': 80,
            }),
            'repo2#1': mock.Mock(**{
                'user.name': 'spam',
                'mergeable': True,
                'created_at': 30,
                'updated_at': 70,
            }),
            'user1:repo3#1': mock.Mock(**{
                'user.name': None,
                'mergeable': True,
                'created_at': 40,
                'updated_at': 60,
            }),
            'user1:repo4#1': mock.Mock(**{
                'user.name': None,
                'mergeable': False,
                'created_at': 50,
                'updated_at': 50,
            }),
            'user2:repo5#1': mock.Mock(**{
                'user.name': None,
                'mergeable': True,
                'created_at': 60,
                'updated_at': 40,
            }),
            'org1:repo6#1': mock.Mock(**{
                'user.name': 'spam',
                'mergeable': True,
                'created_at': 70,
                'updated_at': 30,
            }),
            'org1:repo7#1': mock.Mock(**{
                'user.name': 'spam',
                'mergeable': True,
                'created_at': 80,
                'updated_at': 20,
            }),
            'org2:repo8#1': mock.Mock(**{
                'user.name': 'spam',
                'mergeable': True,
                'created_at': 90,
                'updated_at': 10,
            }),
        }
        for key, pr in prs.items():
            repo, number = key.split(':')[-1].split('#')
            pr.repo.full_name = repo
            pr.number = int(number)
            pr.html_url = 'https://github/%s/pull/%s' % (repo, number)
            pr.head.label = 'me:branch'
            pr.base.label = '%s:master' % repo
            pr.user.login = 'me'
        reports.targets = {
            'repo': mock.Mock(side_effect=lambda x, y, z: [
                pr for n, pr in prs.items() if n.startswith('%s#' % y)]),
            'user': mock.Mock(side_effect=lambda x, y, z: [
                pr for n, pr in prs.items() if n.startswith('%s:' % y)]),
            'organization': mock.Mock(side_effect=lambda x, y, z: [
                pr for n, pr in prs.items() if n.startswith('%s:' % y)]),
        }
        repos = [
            ('repo', 'repo1'),
            ('user', 'user1'),
            ('organization', 'org1'),
            ('repo', 'repo2'),
            ('user', 'user2'),
            ('organization', 'org2'),
        ]
        stream = six.StringIO()

        reports.report('gh', repos, stream, None, 'updated')

        reports.targets['repo'].assert_has_calls([
            mock.call('gh', 'repo1', None),
            mock.call('gh', 'repo2', None),
        ])
        self.assertEqual(reports.targets['repo'].call_count, 2)
        reports.targets['user'].assert_has_calls([
            mock.call('gh', 'user1', None),
            mock.call('gh', 'user2', None),
        ])
        self.assertEqual(reports.targets['user'].call_count, 2)
        reports.targets['organization'].assert_has_calls([
            mock.call('gh', 'org1', None),
            mock.call('gh', 'org2', None),
        ])
        self.assertEqual(reports.targets['organization'].call_count, 2)
        self.assertEqual(
            stream.getvalue(),
            'Open PRs: 9 (7 mergeable)\n'
            '    Oldest PR, from 10: repo1#1\n'
            '    Youngest PR, from 90: repo8#1\n'
            '    Least recently updated PR, at 10: repo8#1\n'
            '    Most recently updated PR, at 90: repo1#1\n'
            '\n'
            'Pull request repo8#1:\n'
            '    URL: https://github/repo8/pull/1\n'
            '    Merge me:branch -> repo8:master\n'
            '    Proposed 90 (age: -10)\n'
            '    Proposed by spam (me)\n'
            '    Last updated: 10 (70 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo7#1:\n'
            '    URL: https://github/repo7/pull/1\n'
            '    Merge me:branch -> repo7:master\n'
            '    Proposed 80 (age: 0)\n'
            '    Proposed by spam (me)\n'
            '    Last updated: 20 (60 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo6#1:\n'
            '    URL: https://github/repo6/pull/1\n'
            '    Merge me:branch -> repo6:master\n'
            '    Proposed 70 (age: 10)\n'
            '    Proposed by spam (me)\n'
            '    Last updated: 30 (50 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo5#1:\n'
            '    URL: https://github/repo5/pull/1\n'
            '    Merge me:branch -> repo5:master\n'
            '    Proposed 60 (age: 20)\n'
            '    Proposed by <unknown> (me)\n'
            '    Last updated: 40 (40 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo4#1:\n'
            '    URL: https://github/repo4/pull/1\n'
            '    Merge me:branch -> repo4:master\n'
            '    Proposed 50 (age: 30)\n'
            '    Proposed by <unknown> (me)\n'
            '    Last updated: 50 (30 ago)\n'
            '    Mergeable: no\n'
            '\n'
            'Pull request repo3#1:\n'
            '    URL: https://github/repo3/pull/1\n'
            '    Merge me:branch -> repo3:master\n'
            '    Proposed 40 (age: 40)\n'
            '    Proposed by <unknown> (me)\n'
            '    Last updated: 60 (20 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo2#1:\n'
            '    URL: https://github/repo2/pull/1\n'
            '    Merge me:branch -> repo2:master\n'
            '    Proposed 30 (age: 50)\n'
            '    Proposed by spam (me)\n'
            '    Last updated: 70 (10 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo1#2:\n'
            '    URL: https://github/repo1/pull/2\n'
            '    Merge me:branch -> repo1:master\n'
            '    Proposed 20 (age: 60)\n'
            '    Proposed by <unknown> (me)\n'
            '    Last updated: 80 (0 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo1#1:\n'
            '    URL: https://github/repo1/pull/1\n'
            '    Merge me:branch -> repo1:master\n'
            '    Proposed 10 (age: 70)\n'
            '    Proposed by <unknown> (me)\n'
            '    Last updated: 90 (-10 ago)\n'
            '    Mergeable: no\n'
            '\n'
            'Repositories with open pull requests: 8\n'
            'Breakdown by repository:\n'
            '    Open PRs for repo1: 2 (1 mergeable)\n'
            '    Open PRs for repo2: 1 (1 mergeable)\n'
            '    Open PRs for repo3: 1 (1 mergeable)\n'
            '    Open PRs for repo4: 1 (0 mergeable)\n'
            '    Open PRs for repo5: 1 (1 mergeable)\n'
            '    Open PRs for repo6: 1 (1 mergeable)\n'
            '    Open PRs for repo7: 1 (1 mergeable)\n'
            '    Open PRs for repo8: 1 (1 mergeable)\n'
            '\n'
            'Report generated in 2 at 80\n'
        )
        self.assertEqual(sys.stderr.getvalue(), '')
        mock_format_age.assert_has_calls([
            mock.call(80, 90, ' (age: %s)'),
            mock.call(80, 10, ' (%s ago)'),
            mock.call(80, 80, ' (age: %s)'),
            mock.call(80, 20, ' (%s ago)'),
            mock.call(80, 70, ' (age: %s)'),
            mock.call(80, 30, ' (%s ago)'),
            mock.call(80, 60, ' (age: %s)'),
            mock.call(80, 40, ' (%s ago)'),
            mock.call(80, 50, ' (age: %s)'),
            mock.call(80, 50, ' (%s ago)'),
            mock.call(80, 40, ' (age: %s)'),
            mock.call(80, 60, ' (%s ago)'),
            mock.call(80, 30, ' (age: %s)'),
            mock.call(80, 70, ' (%s ago)'),
            mock.call(80, 20, ' (age: %s)'),
            mock.call(80, 80, ' (%s ago)'),
            mock.call(80, 10, ' (age: %s)'),
            mock.call(80, 90, ' (%s ago)'),
        ])
        self.assertEqual(mock_format_age.call_count, 18)

    @mock.patch('datetime.datetime', mock.Mock(utcnow=mock.Mock(side_effect=[
        80,
        82,
    ])))
    @mock.patch.dict(reports.targets, clear=True)
    @mock.patch.object(sys, 'stderr', six.StringIO())
    @mock.patch.object(reports, 'format_age',
                       side_effect=lambda x, y, z: z % (x - y))
    def test_callback(self, mock_format_age):
        prs = {
            'repo1#1': mock.Mock(**{
                'user.name': None,
                'mergeable': False,
                'created_at': 10,
                'updated_at': 90,
            }),
            'repo1#2': mock.Mock(**{
                'user.name': None,
                'mergeable': True,
                'created_at': 20,
                'updated_at': 80,
            }),
            'repo2#1': mock.Mock(**{
                'user.name': 'spam',
                'mergeable': True,
                'created_at': 30,
                'updated_at': 70,
            }),
            'user1:repo3#1': mock.Mock(**{
                'user.name': None,
                'mergeable': True,
                'created_at': 40,
                'updated_at': 60,
            }),
            'user1:repo4#1': mock.Mock(**{
                'user.name': None,
                'mergeable': False,
                'created_at': 50,
                'updated_at': 50,
            }),
            'user2:repo5#1': mock.Mock(**{
                'user.name': None,
                'mergeable': True,
                'created_at': 60,
                'updated_at': 40,
            }),
            'org1:repo6#1': mock.Mock(**{
                'user.name': 'spam',
                'mergeable': True,
                'created_at': 70,
                'updated_at': 30,
            }),
            'org1:repo7#1': mock.Mock(**{
                'user.name': 'spam',
                'mergeable': True,
                'created_at': 80,
                'updated_at': 20,
            }),
            'org2:repo8#1': mock.Mock(**{
                'user.name': 'spam',
                'mergeable': True,
                'created_at': 90,
                'updated_at': 10,
            }),
        }
        for key, pr in prs.items():
            repo, number = key.split(':')[-1].split('#')
            pr.repo.full_name = repo
            pr.number = int(number)
            pr.html_url = 'https://github/%s/pull/%s' % (repo, number)
            pr.head.label = 'me:branch'
            pr.base.label = '%s:master' % repo
            pr.user.login = 'me'
        reports.targets = {
            'repo': mock.Mock(side_effect=lambda x, y, z: [
                pr for n, pr in sorted(prs.items(), key=lambda x: x[0])
                if n.startswith('%s#' % y)]),
            'user': mock.Mock(side_effect=lambda x, y, z: [
                pr for n, pr in sorted(prs.items(), key=lambda x: x[0])
                if n.startswith('%s:' % y)]),
            'organization': mock.Mock(side_effect=lambda x, y, z: [
                pr for n, pr in sorted(prs.items(), key=lambda x: x[0])
                if n.startswith('%s:' % y)]),
        }
        repos = [
            ('repo', 'repo1'),
            ('user', 'user1'),
            ('organization', 'org1'),
            ('repo', 'repo2'),
            ('user', 'user2'),
            ('organization', 'org2'),
        ]
        stream = six.StringIO()

        reports.report('gh', repos, stream, 'callback', 'other')

        reports.targets['repo'].assert_has_calls([
            mock.call('gh', 'repo1', 'callback'),
            mock.call('gh', 'repo2', 'callback'),
        ])
        self.assertEqual(reports.targets['repo'].call_count, 2)
        reports.targets['user'].assert_has_calls([
            mock.call('gh', 'user1', 'callback'),
            mock.call('gh', 'user2', 'callback'),
        ])
        self.assertEqual(reports.targets['user'].call_count, 2)
        reports.targets['organization'].assert_has_calls([
            mock.call('gh', 'org1', 'callback'),
            mock.call('gh', 'org2', 'callback'),
        ])
        self.assertEqual(reports.targets['organization'].call_count, 2)
        self.assertEqual(
            stream.getvalue(),
            'Open PRs: 9 (7 mergeable)\n'
            '    Oldest PR, from 10: repo1#1\n'
            '    Youngest PR, from 90: repo8#1\n'
            '    Least recently updated PR, at 10: repo8#1\n'
            '    Most recently updated PR, at 90: repo1#1\n'
            '\n'
            'Pull request repo1#1:\n'
            '    URL: https://github/repo1/pull/1\n'
            '    Merge me:branch -> repo1:master\n'
            '    Proposed 10 (age: 70)\n'
            '    Proposed by <unknown> (me)\n'
            '    Last updated: 90 (-10 ago)\n'
            '    Mergeable: no\n'
            '\n'
            'Pull request repo1#2:\n'
            '    URL: https://github/repo1/pull/2\n'
            '    Merge me:branch -> repo1:master\n'
            '    Proposed 20 (age: 60)\n'
            '    Proposed by <unknown> (me)\n'
            '    Last updated: 80 (0 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo3#1:\n'
            '    URL: https://github/repo3/pull/1\n'
            '    Merge me:branch -> repo3:master\n'
            '    Proposed 40 (age: 40)\n'
            '    Proposed by <unknown> (me)\n'
            '    Last updated: 60 (20 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo4#1:\n'
            '    URL: https://github/repo4/pull/1\n'
            '    Merge me:branch -> repo4:master\n'
            '    Proposed 50 (age: 30)\n'
            '    Proposed by <unknown> (me)\n'
            '    Last updated: 50 (30 ago)\n'
            '    Mergeable: no\n'
            '\n'
            'Pull request repo6#1:\n'
            '    URL: https://github/repo6/pull/1\n'
            '    Merge me:branch -> repo6:master\n'
            '    Proposed 70 (age: 10)\n'
            '    Proposed by spam (me)\n'
            '    Last updated: 30 (50 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo7#1:\n'
            '    URL: https://github/repo7/pull/1\n'
            '    Merge me:branch -> repo7:master\n'
            '    Proposed 80 (age: 0)\n'
            '    Proposed by spam (me)\n'
            '    Last updated: 20 (60 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo2#1:\n'
            '    URL: https://github/repo2/pull/1\n'
            '    Merge me:branch -> repo2:master\n'
            '    Proposed 30 (age: 50)\n'
            '    Proposed by spam (me)\n'
            '    Last updated: 70 (10 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo5#1:\n'
            '    URL: https://github/repo5/pull/1\n'
            '    Merge me:branch -> repo5:master\n'
            '    Proposed 60 (age: 20)\n'
            '    Proposed by <unknown> (me)\n'
            '    Last updated: 40 (40 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo8#1:\n'
            '    URL: https://github/repo8/pull/1\n'
            '    Merge me:branch -> repo8:master\n'
            '    Proposed 90 (age: -10)\n'
            '    Proposed by spam (me)\n'
            '    Last updated: 10 (70 ago)\n'
            '    Mergeable: yes\n'
            '\n'
            'Repositories with open pull requests: 8\n'
            'Breakdown by repository:\n'
            '    Open PRs for repo1: 2 (1 mergeable)\n'
            '    Open PRs for repo2: 1 (1 mergeable)\n'
            '    Open PRs for repo3: 1 (1 mergeable)\n'
            '    Open PRs for repo4: 1 (0 mergeable)\n'
            '    Open PRs for repo5: 1 (1 mergeable)\n'
            '    Open PRs for repo6: 1 (1 mergeable)\n'
            '    Open PRs for repo7: 1 (1 mergeable)\n'
            '    Open PRs for repo8: 1 (1 mergeable)\n'
            '\n'
            'Report generated in 2 at 80\n'
        )
        self.assertEqual(sys.stderr.getvalue(),
                         'Looking up repo "repo1"...\n'
                         'Looking up user "user1"...\n'
                         'Looking up organization "org1"...\n'
                         'Looking up repo "repo2"...\n'
                         'Looking up user "user2"...\n'
                         'Looking up organization "org2"...\n'
                         'Generating report...\n'
                         'Emitting summary: Open PRs: 9 (7 mergeable)\n'
                         'Emitting pull request repo1#1\n'
                         'Emitting pull request repo1#2\n'
                         'Emitting pull request repo3#1\n'
                         'Emitting pull request repo4#1\n'
                         'Emitting pull request repo6#1\n'
                         'Emitting pull request repo7#1\n'
                         'Emitting pull request repo2#1\n'
                         'Emitting pull request repo5#1\n'
                         'Emitting pull request repo8#1\n'
                         'Emitting repositories with open pull requests: 8\n'
                         'Report generated in 2 at 80\n')
        mock_format_age.assert_has_calls([
            mock.call(80, 10, ' (age: %s)'),
            mock.call(80, 90, ' (%s ago)'),
            mock.call(80, 20, ' (age: %s)'),
            mock.call(80, 80, ' (%s ago)'),
            mock.call(80, 40, ' (age: %s)'),
            mock.call(80, 60, ' (%s ago)'),
            mock.call(80, 50, ' (age: %s)'),
            mock.call(80, 50, ' (%s ago)'),
            mock.call(80, 70, ' (age: %s)'),
            mock.call(80, 30, ' (%s ago)'),
            mock.call(80, 80, ' (age: %s)'),
            mock.call(80, 20, ' (%s ago)'),
            mock.call(80, 30, ' (age: %s)'),
            mock.call(80, 70, ' (%s ago)'),
            mock.call(80, 60, ' (age: %s)'),
            mock.call(80, 40, ' (%s ago)'),
            mock.call(80, 90, ' (age: %s)'),
            mock.call(80, 10, ' (%s ago)'),
        ])
        self.assertEqual(mock_format_age.call_count, 18)

    @mock.patch('datetime.datetime', mock.Mock(utcnow=mock.Mock(side_effect=[
        80,
        82,
    ])))
    @mock.patch.dict(reports.targets, clear=True)
    @mock.patch.object(sys, 'stderr', six.StringIO())
    @mock.patch.object(reports, 'format_age',
                       side_effect=lambda x, y, z: z % (x - y))
    def test_empty(self, mock_format_age):
        stream = six.StringIO()

        reports.report('gh', [], stream, 'callback')

        self.assertEqual(stream.getvalue(), 'No open pull requests\n')
        self.assertEqual(sys.stderr.getvalue(), 'Generating report...\n')
        self.assertFalse(mock_format_age.called)


class NormalCallbackTest(unittest.TestCase):
    @mock.patch.object(sys, 'stderr', six.StringIO())
    def test_no_pulls(self):
        repo = mock.Mock(full_name='repo')

        reports._normal_callback(1, 3, repo)

        self.assertEqual(sys.stderr.getvalue(),
                         'Processing repository "repo" (2/3)...\n')

    @mock.patch.object(sys, 'stderr', six.StringIO())
    def test_with_pulls(self):
        repo = mock.Mock(full_name='repo')
        pulls = [
            mock.Mock(mergeable=True),
            mock.Mock(mergeable=False),
            mock.Mock(mergeable=True),
        ]

        reports._normal_callback(1, 3, repo, pulls)

        self.assertEqual(sys.stderr.getvalue(), '')


class VerboseCallbackTest(unittest.TestCase):
    @mock.patch.object(sys, 'stderr', six.StringIO())
    def test_no_pulls(self):
        repo = mock.Mock(full_name='repo')

        reports._verbose_callback(1, 3, repo)

        self.assertEqual(sys.stderr.getvalue(),
                         'Processing repository "repo" (2/3)... ')

    @mock.patch.object(sys, 'stderr', six.StringIO())
    def test_with_pulls(self):
        repo = mock.Mock(full_name='repo')
        pulls = [
            mock.Mock(mergeable=True),
            mock.Mock(mergeable=False),
            mock.Mock(mergeable=True),
        ]

        reports._verbose_callback(1, 3, repo, pulls)

        self.assertEqual(sys.stderr.getvalue(), '3 pulls (2 mergeable)\n')


class ProcessReportTest(unittest.TestCase):
    @mock.patch('getpass.getpass', return_value='prompted')
    @mock.patch('github.Github', return_value='gh')
    @mock.patch('io.open')
    @mock.patch('sys.stdout', mock.Mock())
    def test_basic(self, mock_open, mock_Github, mock_getpass):
        args = mock.Mock(username='username', password='password',
                         github_url='github_url', output='-',
                         verbose=0)

        gen = reports._process_report(args)
        next(gen)

        self.assertEqual(args.gh, 'gh')
        self.assertEqual(args.stream, sys.stdout)
        self.assertEqual(args.repo_callback, None)
        self.assertFalse(mock_getpass.called)
        mock_Github.assert_called_once_with(
            'username', 'password', 'github_url')
        self.assertFalse(mock_open.called)
        self.assertFalse(sys.stdout.close.called)

        try:
            next(gen)
        except StopIteration:
            pass
        else:
            self.fail('Failed to end iteration')

        self.assertFalse(sys.stdout.close.called)

    @mock.patch('getpass.getpass', return_value='prompted')
    @mock.patch('github.Github', return_value='gh')
    @mock.patch('io.open')
    @mock.patch('sys.stdout', mock.Mock())
    def test_prompt(self, mock_open, mock_Github, mock_getpass):
        args = mock.Mock(username='username', password=None,
                         github_url='github_url', output='-',
                         verbose=0)

        gen = reports._process_report(args)
        next(gen)

        self.assertEqual(args.gh, 'gh')
        self.assertEqual(args.stream, sys.stdout)
        self.assertEqual(args.repo_callback, None)
        mock_getpass.assert_called_once_with('Password for username> ')
        mock_Github.assert_called_once_with(
            'username', 'prompted', 'github_url')
        self.assertFalse(mock_open.called)
        self.assertFalse(sys.stdout.close.called)

        try:
            next(gen)
        except StopIteration:
            pass
        else:
            self.fail('Failed to end iteration')

        self.assertFalse(sys.stdout.close.called)

    @mock.patch('getpass.getpass', return_value='prompted')
    @mock.patch('github.Github', return_value='gh')
    @mock.patch('io.open')
    @mock.patch('sys.stdout', mock.Mock())
    def test_output(self, mock_open, mock_Github, mock_getpass):
        args = mock.Mock(username='username', password='password',
                         github_url='github_url', output='output',
                         verbose=0)

        gen = reports._process_report(args)
        next(gen)

        self.assertEqual(args.gh, 'gh')
        self.assertEqual(args.stream, mock_open.return_value)
        self.assertEqual(args.repo_callback, None)
        self.assertFalse(mock_getpass.called)
        mock_Github.assert_called_once_with(
            'username', 'password', 'github_url')
        mock_open.assert_called_once_with('output', 'w', encoding='utf-8')
        self.assertFalse(mock_open.return_value.close.called)

        try:
            next(gen)
        except StopIteration:
            pass
        else:
            self.fail('Failed to end iteration')

        mock_open.return_value.close.assert_called_once_with()

    @mock.patch('getpass.getpass', return_value='prompted')
    @mock.patch('github.Github', return_value='gh')
    @mock.patch('io.open')
    @mock.patch('sys.stdout', mock.Mock())
    def test_verbosity_normal(self, mock_open, mock_Github, mock_getpass):
        args = mock.Mock(username='username', password='password',
                         github_url='github_url', output='-',
                         verbose=1)

        gen = reports._process_report(args)
        next(gen)

        self.assertEqual(args.gh, 'gh')
        self.assertEqual(args.stream, sys.stdout)
        self.assertEqual(args.repo_callback, reports._normal_callback)
        self.assertFalse(mock_getpass.called)
        mock_Github.assert_called_once_with(
            'username', 'password', 'github_url')
        self.assertFalse(mock_open.called)
        self.assertFalse(sys.stdout.close.called)

        try:
            next(gen)
        except StopIteration:
            pass
        else:
            self.fail('Failed to end iteration')

        self.assertFalse(sys.stdout.close.called)

    @mock.patch('getpass.getpass', return_value='prompted')
    @mock.patch('github.Github', return_value='gh')
    @mock.patch('io.open')
    @mock.patch('sys.stdout', mock.Mock())
    def test_verbosity_verbose(self, mock_open, mock_Github, mock_getpass):
        args = mock.Mock(username='username', password='password',
                         github_url='github_url', output='-',
                         verbose=2)

        gen = reports._process_report(args)
        next(gen)

        self.assertEqual(args.gh, 'gh')
        self.assertEqual(args.stream, sys.stdout)
        self.assertEqual(args.repo_callback, reports._verbose_callback)
        self.assertFalse(mock_getpass.called)
        mock_Github.assert_called_once_with(
            'username', 'password', 'github_url')
        self.assertFalse(mock_open.called)
        self.assertFalse(sys.stdout.close.called)

        try:
            next(gen)
        except StopIteration:
            pass
        else:
            self.fail('Failed to end iteration')

        self.assertFalse(sys.stdout.close.called)
