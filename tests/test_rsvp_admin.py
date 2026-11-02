"""Tests for the private, read-only RSVP overview."""

import unittest
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup

from app import app


class RSVPAdminTestCase(unittest.TestCase):
    """Verify access control and the exact information exposed by the overview."""

    def setUp(self):
        """Create an isolated client and configure an overview password."""
        self.config_patch = patch.dict(app.config, {
            'TESTING': True,
            'RSVP_ADMIN_PASSWORD': 'test-overview-password'
        })
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.client = app.test_client()
        self.auth = ('admin', 'test-overview-password')
        self.tracking_patch = patch('app.query_household_documents', return_value=([], []))
        self.mock_tracking = self.tracking_patch.start()
        self.addCleanup(self.tracking_patch.stop)

    def assert_private_headers(self, response):
        """Check that the overview cannot be cached or indexed."""
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertIn('private', response.headers['Cache-Control'])
        self.assertEqual(response.headers['X-Robots-Tag'], 'noindex, nofollow')
        self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')

    @patch('app.get_response_container')
    def test_password_required_before_database_access(self, mock_get_container):
        """Missing or incorrect credentials never fetch RSVP information."""
        for auth in (None, ('admin', 'wrong'), ('guest', self.auth[1])):
            with self.subTest(auth=auth):
                response = self.client.get('/rsvp/admin', auth=auth)
                self.assertEqual(response.status_code, 401)
                self.assertIn('Basic', response.headers['WWW-Authenticate'])
                self.assert_private_headers(response)
        mock_get_container.assert_not_called()

    @patch('app.get_response_container')
    def test_unconfigured_password_disables_page(self, mock_get_container):
        """An unset password fails closed rather than making the overview public."""
        with patch.dict(app.config, {'RSVP_ADMIN_PASSWORD': ''}):
            response = self.client.get('/rsvp/admin', auth=self.auth)
        self.assertEqual(response.status_code, 503)
        self.assert_private_headers(response)
        mock_get_container.assert_not_called()

    @patch('app.get_response_container')
    def test_overview_shows_only_requested_fields(self, mock_get_container):
        """Both accepted and declined responses display only the four requested columns."""
        container = mock_get_container.return_value
        container.query_items.return_value = [
            {
                'id': 'rsvp-1',
                'party_names': 'Taylor Smith\nJordan Smith',
                'attending': 'yes',
                'party_size': 2,
                'welcome_party': 'yes',
                'email': 'private@example.com',
                'couple_note': 'Private couple note',
                'dietary_restrictions': 'Private dietary information'
            },
            {
                'id': 'rsvp-2',
                'party_names': 'Alex <script>alert(1)</script>',
                'attending': 'no',
                'party_size': 0,
                'welcome_party': '',
                'email': 'another-private@example.com',
                'decline_note': 'Private decline note'
            },
            {
                'id': 'rsvp-3',
                'party_names': 'Sam Jones',
                'attending': 'yes',
                'party_size': 1,
                'welcome_party': 'no'
            }
        ]

        response = self.client.get('/rsvp/admin', auth=self.auth)

        self.assertEqual(response.status_code, 200)
        self.assert_private_headers(response)
        table = BeautifulSoup(response.data, 'html.parser').find('table')
        self.assertEqual(
            [cell.get_text(strip=True) for cell in table.select('thead th')],
            ['Attending', 'Number attending', 'Welcome party', 'Names']
        )
        self.assertEqual(
            [[cell.get_text(strip=True) for cell in row.find_all('td')]
             for row in table.select('tbody tr')],
            [
                ['Yes', '2', 'Yes', 'Taylor Smith\nJordan Smith'],
                ['No', '0', 'No', 'Alex <script>alert(1)</script>'],
                ['Yes', '1', 'No', 'Sam Jones']
            ]
        )
        for private_value in (
                b'private@example.com', b'another-private@example.com',
                b'Private couple note', b'Private dietary information',
                b'Private decline note', b'<script>alert(1)</script>'):
            self.assertNotIn(private_value, response.data)
        query_arguments = container.query_items.call_args.kwargs
        self.assertEqual(
            query_arguments['query'],
            'SELECT c.id, c.attending, c.party_size, c.welcome_party, c.party_names '
            'FROM c WHERE c.document_type = @document_type ORDER BY c.party_names'
        )
        self.assertEqual(
            query_arguments['parameters'],
            [{'name': '@document_type', 'value': 'rsvp'}]
        )
        self.assertTrue(query_arguments['enable_cross_partition_query'])

    @patch('app.get_response_container')
    def test_guest_totals_count_people_and_shared_responses_once(self, mock_get_container):
        """Include unresolved households, but exclude declines and duplicate assignments."""
        self.mock_tracking.return_value = (
            [
                {'id': 'shared-one', 'names': ['Taylor Smith']},
                {'id': 'shared-two', 'names': ['Jordan Smith']},
                {'id': 'declined', 'names': ['Alex Jones', 'Casey Jones']},
                {'id': 'waiting', 'names': ['Morgan Lee', 'Riley Lee']},
                {'id': 'review', 'names': ['Jamie Stone', 'Jesse Stone']},
                {'id': 'missing', 'names': ['Quinn Brown']}
            ],
            [
                {'household_id': 'shared-one', 'rsvp_ids': ['shared']},
                {'household_id': 'shared-two', 'rsvp_ids': ['shared']},
                {'household_id': 'missing', 'rsvp_ids': ['deleted']}
            ]
        )
        mock_get_container.return_value.query_items.return_value = [
            {'id': 'shared', 'party_names': 'Taylor Smith and Jordan Smith',
             'attending': 'yes', 'party_size': 3, 'welcome_party': 'yes'},
            {'id': 'decline', 'party_names': 'Alex Jones',
             'attending': 'no', 'party_size': 99, 'welcome_party': ''},
            {'id': 'suggestion', 'party_names': 'Jamey Stone',
             'attending': 'yes', 'party_size': 1, 'welcome_party': 'no'},
            {'id': 'unmatched', 'party_names': 'Unrelated Guest',
             'attending': 'yes', 'party_size': 1, 'welcome_party': 'no'}
        ]

        response = self.client.get('/rsvp/admin', auth=self.auth)

        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.data, 'html.parser')
        summary = soup.select_one('[aria-label="Guest count totals"]')
        self.assertEqual(summary.select_one('[data-invited-guests]').get_text(strip=True), '9')
        for key, expected in (('attending', '5'), ('outstanding', '5'), ('potential', '10')):
            self.assertEqual(
                summary.select_one(f'[data-guest-total="{key}"]').get_text(strip=True),
                expected
            )
        self.assertIn('Needs review', summary.get_text())
        self.assertIn('overlap', summary.get_text())
        self.assertIsNone(summary.find_parent(attrs={'data-filter-scope': True}))

    @patch('app.get_response_container')
    def test_guest_totals_with_all_households_responded(self, mock_get_container):
        """A fully answered guest list has zero outstanding, including declined households."""
        self.mock_tracking.return_value = (
            [{'id': 'one', 'names': ['Taylor Smith', 'Jordan Smith']}], []
        )
        for attending, party_size in (('yes', 2), ('no', 0)):
            with self.subTest(attending=attending):
                mock_get_container.return_value.query_items.return_value = [{
                    'id': 'response', 'party_names': 'Taylor Smith',
                    'attending': attending, 'party_size': party_size, 'welcome_party': ''
                }]
                response = self.client.get('/rsvp/admin', auth=self.auth)
                soup = BeautifulSoup(response.data, 'html.parser')
                self.assertEqual(soup.select_one('[data-invited-guests]').get_text(strip=True), '2')
                for key, expected in (
                        ('attending', str(party_size)), ('outstanding', '0'),
                        ('potential', str(party_size))):
                    self.assertEqual(
                        soup.select_one(f'[data-guest-total="{key}"]').get_text(strip=True),
                        expected
                    )

    @patch('app.get_response_container')
    def test_guest_totals_without_imported_guest_list(self, mock_get_container):
        """Missing invitation data cannot be presented as zero outstanding guests."""
        mock_get_container.return_value.query_items.return_value = []
        response = self.client.get('/rsvp/admin', auth=self.auth)
        soup = BeautifulSoup(response.data, 'html.parser')
        self.assertEqual(soup.select_one('[data-guest-total="attending"]').get_text(strip=True), '0')
        for key in ('outstanding', 'potential'):
            self.assertEqual(
                soup.select_one(f'[data-guest-total="{key}"]').get_text(strip=True),
                'Unavailable'
            )
        self.assertIn('Import the guest list', soup.get_text())
        self.assertIsNone(soup.select_one('[data-invited-guests]'))

    @patch('app.get_response_container')
    def test_empty_overview(self, mock_get_container):
        """A genuinely empty response set is distinguished from a database failure."""
        mock_get_container.return_value.query_items.return_value = []
        response = self.client.get('/rsvp/admin', auth=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No RSVPs have been submitted yet.', response.data)

    @patch('app.get_response_container', return_value=None)
    def test_unavailable_database(self, mock_get_container):
        """Database connection failures are visibly reported as unavailable."""
        response = self.client.get('/rsvp/admin', auth=self.auth)
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'RSVP information is currently unavailable.', response.data)
        self.assertNotIn(b'No RSVPs have been submitted yet.', response.data)
        self.assert_private_headers(response)

    @patch('app.get_response_container')
    def test_query_failure_is_not_an_empty_success(self, mock_get_container):
        """Unexpected query failures use Flask's logged server-error handling."""
        mock_get_container.return_value.query_items.side_effect = RuntimeError('query failed')
        with patch.dict(app.config, {'PROPAGATE_EXCEPTIONS': False}):
            with self.assertLogs(app.logger, level='ERROR'):
                response = self.client.get('/rsvp/admin', auth=self.auth)
        self.assertEqual(response.status_code, 500)
        self.assert_private_headers(response)
        self.assertNotIn(b'No RSVPs have been submitted yet.', response.data)

    def test_overview_is_not_linked_from_public_pages(self):
        """Public navigation and the RSVP page do not advertise the private overview."""
        for path in ('/', '/rsvp'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertNotIn(b'/rsvp/admin', response.data)

    def prepare_manual_match(self, container):
        """Set up household records and acquire a real form CSRF token."""
        self.mock_tracking.return_value = (
            [{'id': 'household-1', 'names': ['Taylor Smith', 'Jordan Smith']}], []
        )
        container.query_items.return_value = [{
            'id': 'rsvp-1', 'party_names': 'Taylor Smith', 'attending': 'no',
            'party_size': 0, 'welcome_party': ''
        }]
        response = self.client.get('/rsvp/admin', auth=self.auth)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.data, 'html.parser')
        return soup.find('input', {'name': 'csrf_token'})['value']

    @patch('app.get_response_container')
    def test_filters_keep_household_responses_together(self, mock_get_container):
        """Filter metadata preserves shared cells and never searches unrelated dropdown options."""
        self.mock_tracking.return_value = (
            [
                {'id': 'household-1', 'names': ['Taylor Smith', 'Jordan Smith']},
                {'id': 'household-2', 'names': ['Casey Brown']}
            ],
            []
        )
        mock_get_container.return_value.query_items.return_value = [
            {
                'id': 'rsvp-1', 'party_names': 'Taylor Smith',
                'attending': 'yes', 'party_size': 1, 'welcome_party': 'no'
            },
            {
                'id': 'rsvp-2', 'party_names': 'Jordan Smith',
                'attending': 'no', 'party_size': 0, 'welcome_party': ''
            }
        ]
        response = self.client.get('/rsvp/admin', auth=self.auth)
        soup = BeautifulSoup(response.data, 'html.parser')
        scopes = soup.select('[data-filter-scope]')
        self.assertEqual(len(scopes), 2)
        for scope in scopes:
            self.assertIsNotNone(scope.select_one('[data-filter-controls]'))
            for field in ('search', 'attending', 'welcome_party'):
                self.assertIsNotNone(scope.select_one(f'[data-filter-field="{field}"]'))
            self.assertIsNotNone(scope.select_one('[data-filter-clear]'))
            self.assertIsNotNone(scope.select_one('[data-filter-count][aria-live="polite"]'))
            self.assertIsNotNone(scope.select_one('[data-filter-empty][hidden]'))
        self.assertIsNone(scopes[0].select_one('[data-filter-field="status"]'))
        self.assertIsNotNone(scopes[1].select_one('[data-filter-field="status"]'))
        households = scopes[1].select('tbody[data-filter-group]')
        self.assertEqual(len(households), 2)
        grouped = next(group for group in households if group.select_one('#household-1'))
        self.assertEqual(grouped['data-status'], 'Responded')
        self.assertEqual(len(grouped.select('[data-response-row]')), 2)
        self.assertIn('Taylor Smith', grouped['data-search-names'])
        self.assertIn('Jordan Smith', grouped['data-search-names'])
        self.assertNotIn('Casey Brown', grouped['data-search-names'])
        awaiting = next(group for group in households if group.select_one('#household-2'))
        self.assertEqual(awaiting['data-status'], 'Not responded')
        self.assertEqual(awaiting.select_one('[data-response-row]')['data-attending'], '')
        self.assertEqual(awaiting.select_one('[data-response-row]')['data-welcome-party'], '')
        self.assertNotIn('Taylor Smith', awaiting['data-search-names'])
        script = soup.find('script', src='/static/js/rsvp_admin_filters.js')
        self.assertIsNotNone(script)

    @patch('app.get_response_container')
    @patch('app.send_and_record_rsvp_notifications')
    def test_admin_can_mark_no_and_undo_without_guest_emails(
            self, mock_send_emails, mock_get_container):
        """Admin declines persist across sessions, update totals, and can be undone."""
        container = mock_get_container.return_value
        token = self.prepare_manual_match(container)
        container.query_items.return_value = []
        response = self.client.post('/rsvp/admin', auth=self.auth, data={
            'csrf_token': token, 'household_id': 'household-1', 'action': 'mark_no'
        })
        self.assertEqual(response.status_code, 303)
        self.assert_private_headers(response)
        saved = container.upsert_item.call_args.kwargs['body']
        self.assertEqual(saved['id'], 'match-household-1')
        self.assertTrue(saved['admin_declined'])
        self.assertEqual(saved['rsvp_ids'], [])
        self.mock_tracking.return_value[1].append(saved)

        other_client = app.test_client()
        response = other_client.get('/rsvp/admin', auth=self.auth)
        soup = BeautifulSoup(response.data, 'html.parser')
        row = soup.select_one('#household-1')
        self.assertEqual(row['data-attending'], 'no')
        self.assertEqual(row['data-welcome-party'], 'no')
        self.assertEqual(row.find_parent('tbody')['data-status'], 'Responded')
        self.assertIn('Admin-marked No', row.get_text())
        self.assertIn('Undo Mark No', row.get_text())
        self.assertEqual([cell.get_text(strip=True) for cell in row.find_all('td')][1:4],
                         ['No', '0', 'No'])
        self.assertIsNone(row.select_one('button[value="mark_no"]'))
        self.assertEqual(soup.select_one('[data-invited-guests]').get_text(strip=True), '2')
        for key in ('attending', 'outstanding', 'potential'):
            self.assertEqual(soup.select_one(f'[data-guest-total="{key}"]').get_text(strip=True), '0')
        container.query_items.return_value = [{
            'id': 'later-response', 'party_names': 'Taylor Smith',
            'attending': 'yes', 'party_size': 2, 'welcome_party': 'yes'
        }]
        later = other_client.get('/rsvp/admin', auth=self.auth)
        later_soup = BeautifulSoup(later.data, 'html.parser')
        self.assertEqual(
            later_soup.select_one('[data-guest-total="attending"]').get_text(strip=True), '2')
        self.assertEqual(later_soup.select_one('#household-1')['data-attending'], 'yes')
        self.assertNotIn('Admin-marked No', later_soup.select_one('#household-1').get_text())
        self.assertIsNone(later_soup.select_one('#household-1 button[value="mark_no"]'))
        container.query_items.return_value = []
        token = soup.select_one('input[name="csrf_token"]')['value']
        response = other_client.post('/rsvp/admin', auth=self.auth, data={
            'csrf_token': token, 'household_id': 'household-1', 'action': 'reset_match'
        })
        self.assertEqual(response.status_code, 303)
        container.delete_item.assert_called_once_with(
            item='match-household-1', partition_key='match-household-1')
        self.mock_tracking.return_value[1].clear()
        response = other_client.get('/rsvp/admin', auth=self.auth)
        soup = BeautifulSoup(response.data, 'html.parser')
        self.assertEqual(soup.select_one('[data-guest-total="outstanding"]').get_text(strip=True), '2')
        self.assertIsNotNone(soup.select_one('#household-1 button[value="mark_no"]'))
        mock_send_emails.assert_not_called()

    @patch('app.get_response_container')
    def test_mark_no_does_not_override_a_submitted_rsvp(self, mock_get_container):
        """A stale admin form cannot replace a guest's actual response."""
        container = mock_get_container.return_value
        token = self.prepare_manual_match(container)
        for attending in ('yes', 'no'):
            with self.subTest(attending=attending):
                container.query_items.return_value[0]['attending'] = attending
                response = self.client.post('/rsvp/admin', auth=self.auth, data={
                    'csrf_token': token, 'household_id': 'household-1', 'action': 'mark_no'
                })
                self.assertEqual(response.status_code, 409)
                self.assertIn(b'already has a submitted RSVP', response.data)
        container.upsert_item.assert_not_called()

    @patch('app.get_response_container')
    def test_mark_no_requires_valid_household_authentication_and_csrf(self, mock_get_container):
        """Decline controls use the same authorization and validation as manual matching."""
        data = {'household_id': 'household-1', 'action': 'mark_no'}
        self.assertEqual(self.client.post('/rsvp/admin', data=data).status_code, 401)
        self.assertEqual(
            self.client.post('/rsvp/admin', auth=self.auth, data=data).status_code, 400)
        mock_get_container.assert_not_called()
        container = mock_get_container.return_value
        token = self.prepare_manual_match(container)
        for household_id, ids in (('unknown', []), ('household-1', ['rsvp-1'])):
            response = self.client.post('/rsvp/admin', auth=self.auth, data={
                'csrf_token': token, 'household_id': household_id,
                'rsvp_ids': ids, 'action': 'mark_no'
            })
            self.assertEqual(response.status_code, 400)
        container.upsert_item.assert_not_called()

    @patch('app.get_response_container')
    def test_mark_no_write_failure_is_reported(self, mock_get_container):
        """Failed decline writes cannot look like successful updates."""
        container = mock_get_container.return_value
        token = self.prepare_manual_match(container)
        container.query_items.return_value = []
        container.upsert_item.side_effect = RuntimeError('write failed')
        with patch.dict(app.config, {'PROPAGATE_EXCEPTIONS': False}):
            with self.assertLogs(app.logger, level='ERROR'):
                response = self.client.post('/rsvp/admin', auth=self.auth, data={
                    'csrf_token': token, 'household_id': 'household-1', 'action': 'mark_no'
                })
        self.assertEqual(response.status_code, 500)

    @patch('app.get_response_container')
    def test_manual_match_is_saved_and_visible_to_another_session(self, mock_get_container):
        """Manual matches persist in the database, not just the current browser session."""
        container = mock_get_container.return_value
        token = self.prepare_manual_match(container)
        response = self.client.post('/rsvp/admin', auth=self.auth, data={
            'csrf_token': token, 'household_id': 'household-1',
            'rsvp_ids': ['rsvp-1'], 'action': 'save_match'
        })
        self.assertEqual(response.status_code, 303)
        self.assert_private_headers(response)
        saved = container.upsert_item.call_args.kwargs['body']
        self.assertEqual(saved['document_type'], 'rsvp_household_match')
        self.assertEqual(saved['household_id'], 'household-1')
        self.assertEqual(saved['rsvp_ids'], ['rsvp-1'])
        self.mock_tracking.return_value[1].append(saved)
        other_client = app.test_client()
        response = other_client.get('/rsvp/admin', auth=self.auth)
        self.assertIn(b'Manual', response.data)
        self.assertIn(b'1 responded', response.data)

    @patch('app.get_response_container')
    def test_manual_match_requires_authentication_and_csrf(self, mock_get_container):
        """Basic credentials alone do not authorize a forged matching request."""
        response = self.client.post('/rsvp/admin', data={})
        self.assertEqual(response.status_code, 401)
        response = self.client.post('/rsvp/admin', auth=self.auth, data={})
        self.assertEqual(response.status_code, 400)
        self.assert_private_headers(response)
        mock_get_container.assert_not_called()

    @patch('app.get_response_container')
    def test_manual_match_rejects_unknown_records(self, mock_get_container):
        """Only imported households and real RSVP responses may be linked."""
        container = mock_get_container.return_value
        token = self.prepare_manual_match(container)
        for household_id, response_ids, action in (
                ('unknown', ['rsvp-1'], 'save_match'),
                ('household-1', ['unknown'], 'save_match'),
                ('household-1', ['rsvp-1'], 'unknown')):
            with self.subTest(household=household_id, responses=response_ids, action=action):
                response = self.client.post('/rsvp/admin', auth=self.auth, data={
                    'csrf_token': token, 'household_id': household_id,
                    'rsvp_ids': response_ids, 'action': action
                })
                self.assertEqual(response.status_code, 400)
        container.upsert_item.assert_not_called()
        container.delete_item.assert_not_called()

    @patch('app.get_response_container')
    def test_can_clear_matches_and_restore_automatic_matching(self, mock_get_container):
        """An empty override and removing an override have distinct meanings."""
        container = mock_get_container.return_value
        token = self.prepare_manual_match(container)
        response = self.client.post('/rsvp/admin', auth=self.auth, data={
            'csrf_token': token, 'household_id': 'household-1', 'action': 'save_match'
        })
        self.assertEqual(response.status_code, 303)
        saved = container.upsert_item.call_args.kwargs['body']
        self.assertEqual(saved['rsvp_ids'], [])
        self.mock_tracking.return_value[1].append(saved)
        response = self.client.post('/rsvp/admin', auth=self.auth, data={
            'csrf_token': token, 'household_id': 'household-1', 'action': 'reset_match'
        })
        self.assertEqual(response.status_code, 303)
        container.delete_item.assert_called_once_with(
            item='match-household-1', partition_key='match-household-1')

    @patch('app.get_response_container')
    def test_manual_save_failure_is_reported(self, mock_get_container):
        """A database write failure never redirects as if the match were saved."""
        container = mock_get_container.return_value
        token = self.prepare_manual_match(container)
        container.upsert_item.side_effect = RuntimeError('write failed')
        with patch.dict(app.config, {'PROPAGATE_EXCEPTIONS': False}):
            with self.assertLogs(app.logger, level='ERROR'):
                response = self.client.post('/rsvp/admin', auth=self.auth, data={
                    'csrf_token': token, 'household_id': 'household-1',
                    'rsvp_ids': ['rsvp-1'], 'action': 'save_match'
                })
        self.assertEqual(response.status_code, 500)
        self.assert_private_headers(response)
