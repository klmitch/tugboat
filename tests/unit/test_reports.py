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

import sys
import unittest

import mock
import six
from six.moves import builtins

from tugboat import reports


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


class ReportTest(unittest.TestCase):
    @mock.patch('datetime.datetime', mock.Mock(now=mock.Mock(side_effect=[
        1234567,
        1234569,
    ])))
    @mock.patch.dict(reports.targets, clear=True)
    @mock.patch.object(sys, 'stderr', six.StringIO())
    def test_basic(self):
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

        reports.report('gh', repos, stream, None)

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
            'Open PRs: 9 (7 mergeable); oldest last updated 10\n'
            '\n'
            'Pull request repo8#1:\n'
            '    URL: https://github/repo8/pull/1\n'
            '    Merge me:branch -> repo8:master\n'
            '    Proposed 90 by spam (me)\n'
            '    Last updated: 10\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo7#1:\n'
            '    URL: https://github/repo7/pull/1\n'
            '    Merge me:branch -> repo7:master\n'
            '    Proposed 80 by spam (me)\n'
            '    Last updated: 20\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo6#1:\n'
            '    URL: https://github/repo6/pull/1\n'
            '    Merge me:branch -> repo6:master\n'
            '    Proposed 70 by spam (me)\n'
            '    Last updated: 30\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo5#1:\n'
            '    URL: https://github/repo5/pull/1\n'
            '    Merge me:branch -> repo5:master\n'
            '    Proposed 60 by <unknown> (me)\n'
            '    Last updated: 40\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo4#1:\n'
            '    URL: https://github/repo4/pull/1\n'
            '    Merge me:branch -> repo4:master\n'
            '    Proposed 50 by <unknown> (me)\n'
            '    Last updated: 50\n'
            '    Mergeable: no\n'
            '\n'
            'Pull request repo3#1:\n'
            '    URL: https://github/repo3/pull/1\n'
            '    Merge me:branch -> repo3:master\n'
            '    Proposed 40 by <unknown> (me)\n'
            '    Last updated: 60\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo2#1:\n'
            '    URL: https://github/repo2/pull/1\n'
            '    Merge me:branch -> repo2:master\n'
            '    Proposed 30 by spam (me)\n'
            '    Last updated: 70\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo1#2:\n'
            '    URL: https://github/repo1/pull/2\n'
            '    Merge me:branch -> repo1:master\n'
            '    Proposed 20 by <unknown> (me)\n'
            '    Last updated: 80\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo1#1:\n'
            '    URL: https://github/repo1/pull/1\n'
            '    Merge me:branch -> repo1:master\n'
            '    Proposed 10 by <unknown> (me)\n'
            '    Last updated: 90\n'
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
            'Report generated in 2 at 1234567\n'
        )
        self.assertEqual(sys.stderr.getvalue(), '')

    @mock.patch('datetime.datetime', mock.Mock(now=mock.Mock(side_effect=[
        1234567,
        1234569,
    ])))
    @mock.patch.dict(reports.targets, clear=True)
    @mock.patch.object(sys, 'stderr', six.StringIO())
    def test_callback(self):
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

        reports.report('gh', repos, stream, 'callback')

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
            'Open PRs: 9 (7 mergeable); oldest last updated 10\n'
            '\n'
            'Pull request repo8#1:\n'
            '    URL: https://github/repo8/pull/1\n'
            '    Merge me:branch -> repo8:master\n'
            '    Proposed 90 by spam (me)\n'
            '    Last updated: 10\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo7#1:\n'
            '    URL: https://github/repo7/pull/1\n'
            '    Merge me:branch -> repo7:master\n'
            '    Proposed 80 by spam (me)\n'
            '    Last updated: 20\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo6#1:\n'
            '    URL: https://github/repo6/pull/1\n'
            '    Merge me:branch -> repo6:master\n'
            '    Proposed 70 by spam (me)\n'
            '    Last updated: 30\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo5#1:\n'
            '    URL: https://github/repo5/pull/1\n'
            '    Merge me:branch -> repo5:master\n'
            '    Proposed 60 by <unknown> (me)\n'
            '    Last updated: 40\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo4#1:\n'
            '    URL: https://github/repo4/pull/1\n'
            '    Merge me:branch -> repo4:master\n'
            '    Proposed 50 by <unknown> (me)\n'
            '    Last updated: 50\n'
            '    Mergeable: no\n'
            '\n'
            'Pull request repo3#1:\n'
            '    URL: https://github/repo3/pull/1\n'
            '    Merge me:branch -> repo3:master\n'
            '    Proposed 40 by <unknown> (me)\n'
            '    Last updated: 60\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo2#1:\n'
            '    URL: https://github/repo2/pull/1\n'
            '    Merge me:branch -> repo2:master\n'
            '    Proposed 30 by spam (me)\n'
            '    Last updated: 70\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo1#2:\n'
            '    URL: https://github/repo1/pull/2\n'
            '    Merge me:branch -> repo1:master\n'
            '    Proposed 20 by <unknown> (me)\n'
            '    Last updated: 80\n'
            '    Mergeable: yes\n'
            '\n'
            'Pull request repo1#1:\n'
            '    URL: https://github/repo1/pull/1\n'
            '    Merge me:branch -> repo1:master\n'
            '    Proposed 10 by <unknown> (me)\n'
            '    Last updated: 90\n'
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
            'Report generated in 2 at 1234567\n'
        )
        self.assertEqual(sys.stderr.getvalue(),
                         'Looking up repo "repo1"...\n'
                         'Looking up user "user1"...\n'
                         'Looking up organization "org1"...\n'
                         'Looking up repo "repo2"...\n'
                         'Looking up user "user2"...\n'
                         'Looking up organization "org2"...\n'
                         'Generating report...\n')

    @mock.patch('datetime.datetime', mock.Mock(now=mock.Mock(side_effect=[
        1234567,
        1234569,
    ])))
    @mock.patch.dict(reports.targets, clear=True)
    @mock.patch.object(sys, 'stderr', six.StringIO())
    def test_empty(self):
        stream = six.StringIO()

        reports.report('gh', [], stream, 'callback')

        self.assertEqual(stream.getvalue(), 'No open pull requests\n')
        self.assertEqual(sys.stderr.getvalue(), 'Generating report...\n')


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
    @mock.patch.object(builtins, 'open')
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
    @mock.patch.object(builtins, 'open')
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
    @mock.patch.object(builtins, 'open')
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
        mock_open.assert_called_once_with('output', 'w')
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
    @mock.patch.object(builtins, 'open')
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
    @mock.patch.object(builtins, 'open')
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
