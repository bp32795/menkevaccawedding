"""Names-only household imports and conservative RSVP matching."""

import csv
from difflib import SequenceMatcher
import hashlib
import re
import unicodedata


def normalize_name(value):
    """Normalize capitalization, accents, punctuation, and whitespace for comparison."""
    decomposed = unicodedata.normalize('NFKD', value.casefold())
    return ' '.join(re.findall(
        r'[^\W_]+', ''.join(char for char in decomposed if not unicodedata.combining(char))
    ))


def read_guest_households(source):
    """Read household names from an invitation CSV without retaining contact details."""
    reader = csv.DictReader(source)
    required_headers = {'First Name', 'Last Name', 'Partner First Name', 'Partner Last Name'}
    if not required_headers.issubset(reader.fieldnames or []):
        raise ValueError('The guest CSV is missing required name columns.')

    households = []
    seen_ids = set()
    for row_number, row in enumerate(reader, start=2):
        if not any(value for value in row.values()):
            continue
        if not (row.get('First Name') or '').strip():
            raise ValueError(f'The guest CSV is missing a first name on row {row_number}.')
        names = []
        for prefix in ('', 'Partner ', *(f'Child {number} ' for number in range(1, 6))):
            first_name = (row.get(f'{prefix}First Name') or '').strip()
            last_name = (row.get(f'{prefix}Last Name') or '').strip()
            if first_name:
                names.append(' '.join(f'{first_name} {last_name}'.split()))
        identity = '\n'.join(sorted(normalize_name(name) for name in names))
        household_id = 'guest-party-' + hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]
        if household_id in seen_ids:
            raise ValueError(f'The guest CSV repeats a household on row {row_number}.')
        seen_ids.add(household_id)
        households.append({
            'id': household_id,
            'document_type': 'guest_household',
            'names': names
        })
    if not households:
        raise ValueError('The guest CSV contains no households.')
    return households


def query_household_documents(container):
    """Fetch only household names and manual matching metadata."""
    households = list(container.query_items(
        query='SELECT c.id, c.names FROM c WHERE c.document_type = @document_type',
        parameters=[{'name': '@document_type', 'value': 'guest_household'}],
        enable_cross_partition_query=True
    ))
    overrides = list(container.query_items(
        query=(
            'SELECT c.id, c.household_id, c.rsvp_ids FROM c '
            'WHERE c.document_type = @document_type'
        ),
        parameters=[{'name': '@document_type', 'value': 'rsvp_household_match'}],
        enable_cross_partition_query=True
    ))
    return households, overrides


def build_household_tracking(households, responses, overrides):
    """Match unique full names automatically and leave ambiguous names for human review."""
    rows = {
        household['id']: {
            'id': household['id'],
            'names': household['names'],
            'responses': [],
            'suggestions': [],
            'manual': False,
            'missing_response': False
        }
        for household in households
    }
    name_index = {}
    for household in households:
        for name in household['names']:
            normalized = normalize_name(name)
            if len(normalized.split()) >= 2:
                name_index.setdefault(normalized, set()).add(household['id'])

    override_index = {override['household_id']: override for override in overrides}
    response_index = {response['id']: response for response in responses}
    manually_assigned = {
        response_id
        for household_id, override in override_index.items() if household_id in rows
        for response_id in override['rsvp_ids']
    }
    for household_id, row in rows.items():
        if household_id in override_index:
            row['manual'] = True
            for response_id in override_index[household_id]['rsvp_ids']:
                if response_id in response_index:
                    row['responses'].append(response_index[response_id])
                else:
                    row['missing_response'] = True

    for response in responses:
        if response['id'] in manually_assigned:
            continue
        party_names = normalize_name(response['party_names'])
        exact_names = {
            name for name in name_index if f' {name} ' in f' {party_names} '
        }
        unique_households = set().union(*(
            name_index[name] for name in exact_names if len(name_index[name]) == 1
        ))
        candidates = set().union(*(name_index[name] for name in exact_names))
        if len(unique_households) == 1:
            household_id = next(iter(unique_households))
            if not rows[household_id]['manual']:
                rows[household_id]['responses'].append(response)
            continue
        if not candidates:
            words = party_names.split()
            for name, household_ids in name_index.items():
                name_words = name.split()
                for start in range(len(words)):
                    candidate = ' '.join(words[start:start + len(name_words)])
                    if SequenceMatcher(None, name, candidate).ratio() >= 0.84:
                        candidates.update(household_ids)
                        break
        for household_id in candidates:
            if not rows[household_id]['manual']:
                rows[household_id]['suggestions'].append(response)

    for row in rows.values():
        if row['missing_response'] or row['suggestions']:
            row['status'] = 'Needs review'
        elif row['responses']:
            row['status'] = 'Responded'
        else:
            row['status'] = 'Not responded'
        row['selected_ids'] = [response['id'] for response in row['responses']]

    matched_ids = {
        response['id'] for row in rows.values() for response in row['responses']
    }
    sorted_rows = sorted(rows.values(), key=lambda row: normalize_name(' '.join(row['names'])))
    return {
        'households': sorted_rows,
        'responded_count': sum(row['status'] == 'Responded' for row in sorted_rows),
        'awaiting_count': sum(row['status'] == 'Not responded' for row in sorted_rows),
        'review_count': sum(row['status'] == 'Needs review' for row in sorted_rows),
        'unmatched_responses': [
            response for response in responses if response['id'] not in matched_ids
        ]
    }
