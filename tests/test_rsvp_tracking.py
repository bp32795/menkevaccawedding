"""Tests for names-only guest imports and conservative household matching."""

import io
import unittest
from unittest.mock import Mock

from rsvp_tracking import (
    build_household_tracking, normalize_name, query_household_documents, read_guest_households
)


class GuestImportTestCase(unittest.TestCase):
    """Keep contact information out of imported household documents."""

    def test_only_guest_names_are_imported(self):
        """Partner and child names are retained without any source contact information."""
        source = io.StringIO(
            '\ufeffFirst Name,Last Name,Partner First Name,Partner Last Name,'
            'Child 1 First Name,Child 1 Last Name,Email Address,Street Address\n'
            'Taylor,Smith,Jordan,Smith,Sam,Smith,private@example.com,123 Private St\n'
        )
        source.read(1)
        records = read_guest_households(source)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['names'], ['Taylor Smith', 'Jordan Smith', 'Sam Smith'])
        self.assertEqual(set(records[0]), {'id', 'document_type', 'names'})
        self.assertEqual(records[0]['document_type'], 'guest_household')
        self.assertNotIn('private@example.com', str(records))
        self.assertNotIn('123 Private St', str(records))

    def test_household_ids_are_stable_across_order_and_case_changes(self):
        """Reimporting the same household does not create duplicate database records."""
        header = 'First Name,Last Name,Partner First Name,Partner Last Name\n'
        first = read_guest_households(io.StringIO(header + 'Taylor,Smith,Jordan,Smith\n'))
        second = read_guest_households(io.StringIO(header + 'JORDAN,SMITH,TAYLOR,SMITH\n'))
        self.assertEqual(first[0]['id'], second[0]['id'])

    def test_invalid_or_duplicate_csv_is_rejected(self):
        """Invalid guest lists fail before any records can be imported."""
        header = 'First Name,Last Name,Partner First Name,Partner Last Name\n'
        for contents in (
                'Name,Email\nTaylor,private@example.com\n', header,
                header + ',Smith,Jordan,Smith\n',
                header + 'Taylor,Smith,,\nTaylor,Smith,,\n'):
            with self.subTest(contents=contents):
                with self.assertRaises(ValueError):
                    read_guest_households(io.StringIO(contents))

    def test_database_queries_only_select_names_and_matching_metadata(self):
        """Household tracking never fetches contact or other private fields."""
        container = Mock()
        container.query_items.side_effect = [[{'id': 'household', 'names': ['Taylor Smith']}], []]
        households, overrides = query_household_documents(container)
        self.assertEqual(households[0]['names'], ['Taylor Smith'])
        self.assertEqual(overrides, [])
        for call in container.query_items.call_args_list:
            query = call.kwargs['query']
            self.assertNotIn('*', query)
            self.assertNotIn('email', query)
            self.assertNotIn('address', query)
            self.assertTrue(call.kwargs['enable_cross_partition_query'])


class HouseholdMatchingTestCase(unittest.TestCase):
    """Separate confirmed responses from ambiguous or missing matches."""

    def setUp(self):
        """Use a guest list containing unique and duplicate names."""
        self.households = [
            {'id': 'one', 'names': ['Taylor Smith', 'Jordan Smith']},
            {'id': 'two', 'names': ['Alex Jones', 'John Smith']},
            {'id': 'three', 'names': ['Casey Brown', 'John Smith']},
            {'id': 'four', 'names': ['Katie']}
        ]

    def track(self, names, overrides=None, **extra):
        """Build a single-response tracking result."""
        return build_household_tracking(
            self.households,
            [{'id': 'response', 'party_names': names, 'attending': 'yes', **extra}],
            overrides or []
        )

    def household(self, result, household_id):
        """Select one household from a tracking result."""
        return next(row for row in result['households'] if row['id'] == household_id)

    def test_unique_full_name_confirms_even_a_declined_response(self):
        """A decline still means the household has responded."""
        result = self.track('Taylor Smith', attending='no')
        self.assertEqual(self.household(result, 'one')['status'], 'Responded')
        self.assertEqual(result['responded_count'], 1)
        self.assertEqual(result['awaiting_count'], 3)
        self.assertEqual(result['unmatched_responses'], [])

    def test_duplicate_names_require_review(self):
        """A shared name must not mark either household as confirmed."""
        result = self.track('John Smith')
        self.assertEqual(self.household(result, 'two')['status'], 'Needs review')
        self.assertEqual(self.household(result, 'three')['status'], 'Needs review')
        self.assertEqual(result['responded_count'], 0)
        self.assertEqual(result['review_count'], 2)
        self.assertEqual(len(result['unmatched_responses']), 1)

    def test_unique_party_member_disambiguates_shared_name(self):
        """Another unique party member resolves a duplicate-name ambiguity."""
        result = self.track('John Smith and Alex Jones')
        self.assertEqual(self.household(result, 'two')['status'], 'Responded')
        self.assertEqual(self.household(result, 'three')['status'], 'Not responded')

    def test_response_spanning_households_is_flagged_for_review(self):
        """A shared RSVP is not silently assigned to multiple invite households."""
        result = self.track('Taylor Smith, Alex Jones')
        self.assertEqual(result['responded_count'], 0)
        self.assertEqual(self.household(result, 'one')['status'], 'Needs review')
        self.assertEqual(self.household(result, 'two')['status'], 'Needs review')

    def test_similar_spellings_are_suggestions_not_confirmations(self):
        """Fuzzy name similarity never becomes an automatic confirmed match."""
        result = self.track('Tayler Smith')
        row = self.household(result, 'one')
        self.assertEqual(row['status'], 'Needs review')
        self.assertEqual(len(row['suggestions']), 1)
        self.assertEqual(row['responses'], [])

    def test_first_name_only_and_unrelated_names_do_not_auto_match(self):
        """Incomplete and unrelated names remain unmatched."""
        for name in ('Katie', 'Completely Unrelated', ''):
            with self.subTest(name=name):
                result = self.track(name)
                self.assertEqual(result['responded_count'], 0)
                self.assertEqual(len(result['unmatched_responses']), 1)

    def test_normalization_handles_accents_case_and_punctuation(self):
        """Formatting differences do not prevent an otherwise exact full-name match."""
        self.assertEqual(normalize_name(" JOS\u00c9 O'Neil "), 'jose o neil')
        result = self.track('TAYLOR SMITH\nJordan Smith')
        self.assertEqual(result['responded_count'], 1)

    def test_manual_assignment_wins_over_automatic_match(self):
        """A response manually assigned elsewhere is not auto-linked again."""
        result = self.track('Taylor Smith', [{
            'household_id': 'two', 'rsvp_ids': ['response']
        }])
        self.assertEqual(self.household(result, 'one')['status'], 'Not responded')
        self.assertEqual(self.household(result, 'two')['status'], 'Responded')
        self.assertTrue(self.household(result, 'two')['manual'])

    def test_empty_manual_override_blocks_automatic_match(self):
        """An explicitly cleared household remains not responded."""
        result = self.track('Taylor Smith', [{'household_id': 'one', 'rsvp_ids': []}])
        self.assertEqual(self.household(result, 'one')['status'], 'Not responded')
        self.assertEqual(len(result['unmatched_responses']), 1)

    def test_shared_response_can_be_manually_assigned_to_multiple_households(self):
        """Human confirmation can associate a shared response with several invitations."""
        result = self.track('Taylor Smith and Alex Jones', [
            {'household_id': 'one', 'rsvp_ids': ['response']},
            {'household_id': 'two', 'rsvp_ids': ['response']}
        ])
        self.assertEqual(result['responded_count'], 2)
        self.assertEqual(result['unmatched_responses'], [])

    def test_multiple_responses_for_one_household_are_preserved(self):
        """Separate replies from party members can belong to the same household."""
        responses = [
            {'id': 'first', 'party_names': 'Taylor Smith'},
            {'id': 'second', 'party_names': 'Jordan Smith'}
        ]
        result = build_household_tracking(self.households, responses, [])
        self.assertEqual(result['responded_count'], 1)
        self.assertEqual(len(self.household(result, 'one')['responses']), 2)

    def test_deleted_manually_matched_response_requires_review(self):
        """Stale saved links are surfaced, not silently shown as a confirmed response."""
        result = self.track('Taylor Smith', [
            {'household_id': 'two', 'rsvp_ids': ['deleted']}
        ])
        self.assertEqual(self.household(result, 'two')['status'], 'Needs review')
        self.assertTrue(self.household(result, 'two')['missing_response'])
