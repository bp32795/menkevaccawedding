"""
Test cases for the Menke Vacca Wedding Website
Comprehensive test suite following TDD principles
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module
from app import app, get_notification_recipients, scrape_title_from_url


class WeddingWebsiteTestCase(unittest.TestCase):
    """Base test case with common setup"""
    
    def setUp(self):
        """Set up test client and configuration"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        # Mock data for testing (Cosmos DB format)
        self.mock_registry_data = [
            {
                'id': 'item-1',
                'url': 'https://example.com/item1',
                'image_url': 'https://example.com/vase.jpg',
                'price': 45.99,
                'bought': False,
                'title': 'Beautiful Vase',
                'bought_by': ''
            },
            {
                'id': 'item-2',
                'url': 'https://example.com/item2',
                'image_url': 'https://example.com/coffee.jpg',
                'price': 129.99,
                'bought': True,
                'title': 'Coffee Maker',
                'bought_by': 'John Doe'
            },
            {
                'id': 'item-3',
                'url': 'https://example.com/item3',
                'image_url': '',
                'price': 75.50,
                'bought': False,
                'title': '',
                'bought_by': ''
            }
        ]


class HomePageTestCase(WeddingWebsiteTestCase):
    """Test cases for the home page"""
    
    def test_home_page_loads(self):
        """Test that home page loads successfully"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Menke & Vacca', response.data)
        self.assertIn(b'Sofia Vacca', response.data)
    
    def test_home_page_navigation_links(self):
        """Test that navigation links are present"""
        response = self.client.get('/')
        self.assertIn(b'RSVP', response.data)
        self.assertIn(b'Registry', response.data)
        self.assertIn(b'Home', response.data)
    
    def test_home_page_cta_buttons(self):
        """Test that call-to-action buttons are present"""
        response = self.client.get('/')
        self.assertIn(b'See Our Venue', response.data)
        self.assertIn(b'View Registry', response.data)


class RSVPPageTestCase(WeddingWebsiteTestCase):
    """Test cases for the RSVP page"""

    def test_rsvp_page_loads(self):
        """Test that RSVP page loads successfully"""
        response = self.client.get('/rsvp')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Click Here to RSVP', response.data)
        self.assertIn(b'Change RSVP', response.data)
        self.assertIn(b'Will you be attending the Welcome Party', response.data)
        self.assertIn(b'href="https://share.google/7ZxWuUYoSVfMIMUnj"', response.data)
        self.assertIn(b'We will be serving salmon', response.data)
        self.assertIn(b'Dietary restrictions', response.data)
        self.assertIn(b'Feel free to leave a note for the couple', response.data)
        self.assertGreaterEqual(response.data.count(b'visually-hidden">Required'), 7)

    @patch('app.get_response_container')
    def test_submit_rsvp_requires_every_guest_field(self, mock_get_container):
        """Each guest-facing RSVP field is required by the API."""
        valid_data = {
            'party_names': 'Taylor Smith',
            'attending': 'yes',
            'welcome_party': 'yes',
            'party_size': 1,
            'email': 'taylor@example.com',
            'captcha': '7',
            'website': ''
        }

        for missing_field in (
                'party_names', 'attending', 'welcome_party', 'party_size', 'email'):
            with self.subTest(missing_field=missing_field):
                request_data = dict(valid_data)
                request_data.pop(missing_field)
                with self.client.session_transaction() as session_data:
                    session_data['captcha_rsvp'] = 7

                response = self.client.post('/api/rsvp', json=request_data)

                self.assertEqual(response.status_code, 400)
        mock_get_container.assert_not_called()

    @patch('app.send_guest_rsvp_confirmation')
    @patch('app.send_rsvp_notification_email')
    @patch('app.get_response_container')
    def test_submit_rsvp_stores_response_and_sends_email(
            self, mock_get_container, mock_send_email, mock_guest_email):
        """A valid RSVP is stored and emailed to the couple and guest."""
        mock_container = Mock()
        mock_container.query_items.return_value = []
        mock_get_container.return_value = mock_container

        with self.client.session_transaction() as session_data:
            session_data['captcha_rsvp'] = 7

        response = self.client.post('/api/rsvp', json={
            'party_names': 'Taylor Smith, Jordan Smith',
            'attending': 'yes',
            'welcome_party': 'yes',
            'party_size': 2,
            'dietary_restrictions': 'One vegetarian meal, please.',
            'email': 'Taylor@example.com',
            'captcha': '7',
            'website': ''
        })

        self.assertEqual(response.status_code, 201)
        stored_rsvp = mock_container.create_item.call_args.kwargs['body']
        self.assertEqual(stored_rsvp['document_type'], 'rsvp')
        self.assertEqual(stored_rsvp['email'], 'taylor@example.com')
        self.assertEqual(stored_rsvp['welcome_party'], 'yes')
        self.assertEqual(
            stored_rsvp['dietary_restrictions'], 'One vegetarian meal, please.')
        self.assertEqual(stored_rsvp['decline_note'], '')
        self.assertEqual(stored_rsvp['party_size'], 2)
        mock_send_email.assert_called_once_with(stored_rsvp, is_update=False)
        mock_guest_email.assert_called_once()
        self.assertEqual(mock_guest_email.call_args.args[0], stored_rsvp)
        self.assertIn('/rsvp/edit/', mock_guest_email.call_args.args[1])

    @patch('app.send_guest_rsvp_confirmation')
    @patch('app.send_rsvp_notification_email')
    @patch('app.get_response_container')
    def test_declining_rsvp_stores_optional_note_without_attendee_fields(
            self, mock_get_container, mock_send_email, mock_guest_email):
        """A declining party can leave a note without attendee-only details."""
        mock_container = Mock()
        mock_container.query_items.return_value = []
        mock_get_container.return_value = mock_container

        with self.client.session_transaction() as session_data:
            session_data['captcha_rsvp'] = 7

        response = self.client.post('/api/rsvp', json={
            'party_names': 'Taylor Smith',
            'attending': 'no',
            'decline_note': 'We are sorry to miss it. Congratulations!',
            'email': 'taylor@example.com',
            'captcha': '7',
            'website': ''
        })

        self.assertEqual(response.status_code, 201)
        stored_rsvp = mock_container.create_item.call_args.kwargs['body']
        self.assertEqual(stored_rsvp['welcome_party'], '')
        self.assertEqual(stored_rsvp['party_size'], 0)
        self.assertEqual(stored_rsvp['dietary_restrictions'], '')
        self.assertEqual(
            stored_rsvp['decline_note'],
            'We are sorry to miss it. Congratulations!'
        )
        mock_send_email.assert_called_once_with(stored_rsvp, is_update=False)
        mock_guest_email.assert_called_once()

    @patch('app.get_response_container')
    def test_submit_rsvp_rejects_duplicate_email(self, mock_get_container):
        """A second new RSVP cannot overwrite an existing email."""
        mock_container = Mock()
        mock_container.query_items.return_value = [{'id': 'existing'}]
        mock_get_container.return_value = mock_container

        with self.client.session_transaction() as session_data:
            session_data['captcha_rsvp'] = 4

        response = self.client.post('/api/rsvp', json={
            'party_names': 'Taylor Smith',
            'attending': 'no',
            'welcome_party': 'no',
            'party_size': 1,
            'email': 'taylor@example.com',
            'captcha': '4',
            'website': ''
        })

        self.assertEqual(response.status_code, 409)
        mock_container.create_item.assert_not_called()

    @patch('app.get_response_container')
    def test_lookup_rsvp_returns_previous_information(self, mock_get_container):
        """Email lookup returns the saved RSVP and authorizes one edit."""
        saved_rsvp = {
            'id': 'rsvp-1',
            'document_type': 'rsvp',
            'party_names': 'Taylor Smith',
            'attending': 'yes',
            'welcome_party': 'no',
            'party_size': 1,
            'email': 'taylor@example.com'
        }
        mock_container = Mock()
        mock_container.query_items.return_value = [saved_rsvp]
        mock_get_container.return_value = mock_container

        with self.client.session_transaction() as session_data:
            session_data['captcha_lookup'] = 9

        response = self.client.post('/api/rsvp/lookup', json={
            'email': 'Taylor@example.com',
            'captcha': '9',
            'website': ''
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['rsvp']['party_names'], 'Taylor Smith')
        self.assertEqual(response.get_json()['rsvp']['welcome_party'], 'no')
        with self.client.session_transaction() as session_data:
            self.assertEqual(session_data['editable_rsvp_id'], 'rsvp-1')

    @patch('app.send_guest_rsvp_confirmation')
    @patch('app.send_rsvp_notification_email')
    @patch('app.get_response_container')
    def test_change_rsvp_updates_authorized_record(
            self, mock_get_container, mock_send_email, mock_guest_email):
        """A lookup-authorized RSVP edit updates only that record."""
        mock_container = Mock()
        mock_container.read_item.return_value = {
            'id': 'rsvp-1',
            'document_type': 'rsvp',
            'email': 'taylor@example.com',
            'created_at': '2026-08-01T00:00:00+00:00'
        }
        mock_get_container.return_value = mock_container

        with self.client.session_transaction() as session_data:
            session_data['editable_rsvp_id'] = 'rsvp-1'
            session_data['editable_rsvp_email'] = 'taylor@example.com'

        response = self.client.post('/api/rsvp', json={
            'party_names': 'Taylor Smith, Jordan Smith',
            'attending': 'yes',
            'welcome_party': 'no',
            'party_size': 2,
            'email': 'taylor@example.com',
            'is_update': True,
            'website': ''
        })

        self.assertEqual(response.status_code, 200)
        updated_rsvp = mock_container.replace_item.call_args.kwargs['body']
        self.assertEqual(updated_rsvp['welcome_party'], 'no')
        self.assertEqual(updated_rsvp['party_size'], 2)
        mock_send_email.assert_called_once_with(updated_rsvp, is_update=True)
        mock_guest_email.assert_called_once()
        self.assertEqual(mock_guest_email.call_args.args[0], updated_rsvp)

    @patch('app.get_response_container')
    def test_signed_edit_link_prefills_saved_rsvp(self, mock_get_container):
        """A valid signed link authorizes and preloads the matching RSVP."""
        saved_rsvp = {
            'id': 'rsvp-1',
            'document_type': 'rsvp',
            'party_names': 'Taylor Smith, Jordan Smith',
            'attending': 'yes',
            'welcome_party': 'yes',
            'party_size': 2,
            'dietary_restrictions': 'One vegetarian meal, please.',
            'decline_note': '',
            'email': 'taylor@example.com'
        }
        mock_container = Mock()
        mock_container.read_item.return_value = saved_rsvp
        mock_get_container.return_value = mock_container
        token = app_module.generate_rsvp_edit_token(saved_rsvp)

        response = self.client.get(f'/rsvp/edit/{token}')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Taylor Smith, Jordan Smith', response.data)
        self.assertIn(b'"welcome_party": "yes"', response.data)
        with self.client.session_transaction() as session_data:
            self.assertEqual(session_data['editable_rsvp_id'], 'rsvp-1')

    @patch('app.send_email_via_azure')
    @patch.dict(os.environ, {'AZURE_COMMUNICATION_CONNECTION_STRING': 'configured'})
    def test_guest_confirmation_contains_details_and_html_edit_link(
            self, mock_send_email):
        """Guest confirmation includes submitted details and a linked edit action."""
        rsvp_record = {
            'id': 'rsvp-1',
            'party_names': 'Taylor Smith, Jordan Smith',
            'attending': 'yes',
            'welcome_party': 'yes',
            'party_size': 2,
            'dietary_restrictions': 'One vegetarian meal, please.',
            'decline_note': '',
            'email': 'taylor@example.com'
        }
        edit_url = 'https://test.menkexvacca.com/rsvp/edit/signed-token'
        mock_send_email.return_value = True

        result = app_module.send_guest_rsvp_confirmation(rsvp_record, edit_url)

        self.assertTrue(result)
        recipients, subject, plain_body = mock_send_email.call_args.args
        html_body = mock_send_email.call_args.kwargs['html_body']
        self.assertEqual(recipients, ['taylor@example.com'])
        self.assertEqual(subject, 'Your Menke & Vacca Wedding RSVP')
        self.assertIn('Thank you for your response!', plain_body)
        self.assertIn('Taylor Smith, Jordan Smith', plain_body)
        self.assertIn('Welcome Party: Yes', plain_body)
        self.assertIn('Dietary restrictions: One vegetarian meal, please.', plain_body)
        self.assertIn(edit_url, plain_body)
        self.assertIn(f'href="{edit_url}"', html_body)
        self.assertIn('Thanks,<br>Brandon and Sofie', html_body)

    def test_submit_rsvp_rejects_invalid_captcha(self):
        """A new RSVP requires the server-generated bot challenge."""
        with self.client.session_transaction() as session_data:
            session_data['captcha_rsvp'] = 6

        response = self.client.post('/api/rsvp', json={
            'party_names': 'Taylor Smith',
            'attending': 'yes',
            'party_size': 1,
            'email': 'taylor@example.com',
            'captcha': '99',
            'website': ''
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('verification', response.get_json()['error'].lower())


class ContactPageTestCase(WeddingWebsiteTestCase):
    """Test cases for the contact form."""

    def test_contact_page_loads(self):
        """The contact page displays all requested fields."""
        response = self.client.get('/contact')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Contact Us', response.data)
        self.assertIn(b'Name', response.data)
        self.assertIn(b'Email', response.data)
        self.assertIn(b'Note', response.data)

    @patch('app.send_contact_notification_email')
    @patch('app.get_response_container')
    def test_contact_submission_is_stored_and_emailed(
            self, mock_get_container, mock_send_email):
        """A valid contact message is persisted and emailed."""
        mock_container = Mock()
        mock_get_container.return_value = mock_container

        with self.client.session_transaction() as session_data:
            session_data['captcha_contact'] = 5

        response = self.client.post('/contact', data={
            'name': 'Taylor Smith',
            'email': 'taylor@example.com',
            'note': 'I forgot which email I used for my RSVP.',
            'captcha': '5',
            'website': ''
        })

        self.assertEqual(response.status_code, 302)
        stored_message = mock_container.create_item.call_args.kwargs['body']
        self.assertEqual(stored_message['document_type'], 'contact')
        mock_send_email.assert_called_once_with(stored_message)

    @patch.dict(os.environ, {'EMAIL_TO_ADDRESS': 'bp32795@gmail.com'})
    def test_form_notifications_include_both_recipients(self):
        """Wedding form notifications always include Brandon and Sofia."""
        recipients = get_notification_recipients()

        self.assertIn('bp32795@gmail.com', recipients)
        self.assertIn('sofiavacca97@gmail.com', recipients)


class VenuePageTestCase(WeddingWebsiteTestCase):
    """Test cases for the venue page"""
    
    def test_venue_page_loads(self):
        """Test that venue page loads successfully"""
        response = self.client.get('/venue')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Different Pointe of View', response.data)
        self.assertIn(b'Tapatio Cliffs Resort', response.data)
    
    def test_venue_content_display(self):
        """Test that venue details are properly displayed"""
        response = self.client.get('/venue')
        self.assertIn(b'North Phoenix', response.data)
        self.assertIn(b'Hilton Phoenix Tapatio Cliffs Resort', response.data)
        self.assertIn(b'Venue Gallery', response.data)
    
    def test_venue_booking_info(self):
        """Test that hotel booking information is displayed"""
        response = self.client.get('/venue')
        self.assertIn(b'Accommodations', response.data)


class TimelinePageTestCase(WeddingWebsiteTestCase):
    """Test cases for the timeline page"""
    
    def test_timeline_page_loads(self):
        """Test that timeline page loads successfully"""
        response = self.client.get('/ourstory')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Our Love Story', response.data)
    
    def test_timeline_story_content(self):
        """Test that story milestones are displayed"""
        response = self.client.get('/ourstory')
        self.assertIn(b'2017', response.data)  # First meeting year
        self.assertIn(b'2025', response.data)  # Proposal year
        self.assertIn(b'Tinder', response.data)  # How they met
        self.assertIn(b'Brandon', response.data)
        self.assertIn(b'Sofie', response.data)
    
    def test_timeline_adventure_gallery(self):
        """Test that adventure gallery is displayed"""
        response = self.client.get('/ourstory')
        self.assertIn(b'Adventures Together', response.data)


class RegistryPageTestCase(WeddingWebsiteTestCase):
    """Test cases for the registry page"""
    
    @patch('app.get_cosmos_container')
    def test_registry_page_loads_with_items(self, mock_get_container):
        """Test that registry page loads with items from Cosmos DB"""
        mock_container = Mock()
        mock_container.query_items.return_value = iter(self.mock_registry_data)
        mock_get_container.return_value = mock_container
        
        response = self.client.get('/registry')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Wedding Registry', response.data)
        self.assertIn(b'Beautiful Vase', response.data)
        self.assertIn(b'Coffee Maker', response.data)
        self.assertIn(b'Shipping Address', response.data)
        self.assertIn(b'class="registry-shipping-address"', response.data)
        self.assertIn(b'Product links lead to the manufacturer', response.data)
        self.assertIn(b'@Bmenk', response.data)
        self.assertIn(b'data-filter="available"', response.data)
        self.assertIn(b'data-filter="bought"', response.data)
        self.assertIn(b'data-bought="true"', response.data)
        self.assertIn(b'data-bought="false"', response.data)
    
    @patch('app.get_cosmos_container')
    def test_registry_page_handles_no_container(self, mock_get_container):
        """Test that registry page handles Cosmos DB connection failure"""
        mock_get_container.return_value = None
        
        response = self.client.get('/registry')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registry items will appear here', response.data)
    
    @patch('app.get_cosmos_container')
    def test_registry_sorting_by_price(self, mock_get_container):
        """Test that registry items are sorted by price"""
        mock_container = Mock()
        mock_container.query_items.return_value = iter(self.mock_registry_data)
        mock_get_container.return_value = mock_container
        
        response = self.client.get('/registry')
        self.assertEqual(response.status_code, 200)
        
        content = response.data.decode('utf-8')
        vase_pos = content.find('Beautiful Vase')     # $45.99
        coffee_pos = content.find('Coffee Maker')      # $129.99
        
        # Beautiful Vase ($45.99) should come before Coffee Maker ($129.99)
        self.assertLess(vase_pos, coffee_pos)
    
    @patch('app.get_cosmos_container')
    def test_registry_bought_items_display(self, mock_get_container):
        """Test that bought items are displayed differently"""
        mock_container = Mock()
        mock_container.query_items.return_value = iter(self.mock_registry_data)
        mock_get_container.return_value = mock_container
        
        response = self.client.get('/registry')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Already Purchased', response.data)
        self.assertIn(b'I Bought This', response.data)


class PurchaseItemTestCase(WeddingWebsiteTestCase):
    """Test cases for item purchase functionality"""
    
    @patch('app.send_registry_notification_email')
    @patch('app.get_cosmos_container')
    def test_purchase_item_success(self, mock_get_container, mock_send_email):
        """Test successful item purchase"""
        mock_container = Mock()
        mock_container.read_item.return_value = dict(self.mock_registry_data[0])
        mock_container.replace_item = Mock()
        mock_get_container.return_value = mock_container
        mock_send_email.return_value = True
        
        purchase_data = {
            'name': 'Jane Smith',
            'purchase_date': '2025-08-30',
            'delivery_date': '2025-09-05',
            'item_title': 'Beautiful Vase',
            'item_id': 'item-1',
            'item_url': 'https://example.com/item1'
        }
        
        response = self.client.post('/purchase_item',
                                   data=json.dumps(purchase_data),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('Thank you', data['message'])
        
        # Verify Cosmos DB was updated
        mock_container.read_item.assert_called_once_with(item='item-1', partition_key='item-1')
        mock_container.replace_item.assert_called_once()
        
        # Verify email was sent
        mock_send_email.assert_called_once()
    
    def test_purchase_item_missing_data(self):
        """Test purchase item with missing required data"""
        incomplete_data = {
            'name': 'Jane Smith',
            # Missing other required fields
        }
        
        response = self.client.post('/purchase_item',
                                   data=json.dumps(incomplete_data),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Missing required field', data['error'])
    
    @patch('app.get_cosmos_container')
    def test_purchase_item_no_container(self, mock_get_container):
        """Test purchase item when Cosmos DB connection fails"""
        mock_get_container.return_value = None
        
        purchase_data = {
            'name': 'Jane Smith',
            'purchase_date': '2025-08-30',
            'item_title': 'Beautiful Vase',
            'item_id': 'item-1'
        }
        
        response = self.client.post('/purchase_item',
                                   data=json.dumps(purchase_data),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Unable to connect', data['error'])


class UtilityFunctionsTestCase(WeddingWebsiteTestCase):
    """Test cases for utility functions"""
    
    @patch('app.requests.get')
    def test_scrape_title_from_url_success(self, mock_get):
        """Test successful title scraping from URL"""
        mock_response = Mock()
        mock_response.content = b'<html><head><title>Amazing Product</title></head><body><h1>Amazing Product Title</h1></body></html>'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        title = scrape_title_from_url('https://example.com/product')
        self.assertEqual(title, 'Amazing Product Title')
    
    @patch('app.requests.get')
    def test_scrape_title_from_url_failure(self, mock_get):
        """Test title scraping failure"""
        mock_get.side_effect = Exception('Network error')
        
        title = scrape_title_from_url('https://example.com/product')
        self.assertEqual(title, 'Product')  # Fallback title
    
    @patch('app.requests.get')
    def test_scrape_title_no_title_found(self, mock_get):
        """Test title scraping when no title is found"""
        mock_response = Mock()
        mock_response.content = b'<html><body><p>No title here</p></body></html>'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        title = scrape_title_from_url('https://example.com/product')
        self.assertEqual(title, 'Product')  # Fallback title
    
    # def test_get_google_sheets_client(self):
    #     """Test Google Sheets client initialization"""
    #     with patch('app.Credentials.from_service_account_info') as mock_creds, \
    #          patch('app.gspread.authorize') as mock_authorize:
            
    #         mock_credentials = Mock()
    #         mock_creds.return_value = mock_credentials
    #         mock_client = Mock()
    #         mock_authorize.return_value = mock_client
            
    #         client = get_google_sheets_client()
            
    #         self.assertIsNotNone(client)
    #         mock_creds.assert_called_once()
    #         mock_authorize.assert_called_once_with(mock_credentials)


class ErrorHandlingTestCase(WeddingWebsiteTestCase):
    """Test cases for error handling"""
    
    def test_404_error_page(self):
        """Test 404 error page"""
        response = self.client.get('/nonexistent-page')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'Page Not Found', response.data)
        self.assertIn(b'404', response.data)
    
    @patch('app.get_cosmos_container')
    def test_registry_handles_db_exception(self, mock_get_container):
        """Test that registry page handles Cosmos DB exceptions gracefully"""
        mock_container = Mock()
        mock_container.query_items.side_effect = Exception('Cosmos DB error')
        mock_get_container.return_value = mock_container
        
        response = self.client.get('/registry')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registry items will appear here', response.data)


class SecurityTestCase(WeddingWebsiteTestCase):
    """Test cases for security features"""
    
    def test_csrf_protection_disabled_in_testing(self):
        """Test that CSRF protection is properly configured for testing"""
        self.assertFalse(self.app.config['WTF_CSRF_ENABLED'])
    
    def test_secret_key_configured(self):
        """Test that secret key is configured"""
        self.assertIsNotNone(self.app.secret_key)
        self.assertNotEqual(self.app.secret_key, '')
    
    def test_purchase_item_requires_json(self):
        """Test that purchase endpoint requires JSON content type"""
        response = self.client.post('/purchase_item', data='not json')
        # Should fail gracefully, not crash
        self.assertIn(response.status_code, [400, 500])


class IntegrationTestCase(WeddingWebsiteTestCase):
    """Integration test cases"""
    
    @patch('app.send_registry_notification_email')
    @patch('app.get_cosmos_container')
    def test_full_purchase_workflow(self, mock_get_container, mock_send_email):
        """Test the complete purchase workflow"""
        mock_container = Mock()
        mock_container.query_items.return_value = iter(self.mock_registry_data)
        mock_container.read_item.return_value = dict(self.mock_registry_data[0])
        mock_container.replace_item = Mock()
        mock_get_container.return_value = mock_container
        mock_send_email.return_value = True
        
        # 1. Load registry page
        response = self.client.get('/registry')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Beautiful Vase', response.data)
        
        # 2. Purchase an item
        purchase_data = {
            'name': 'Integration Test User',
            'purchase_date': '2025-08-30',
            'item_title': 'Beautiful Vase',
            'item_id': 'item-1',
            'item_url': 'https://example.com/item1'
        }
        
        response = self.client.post('/purchase_item',
                                   data=json.dumps(purchase_data),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # 3. Verify side effects
        mock_container.replace_item.assert_called()
        mock_send_email.assert_called_once()


if __name__ == '__main__':
    # Create a test suite
    test_classes = [
        HomePageTestCase,
        RSVPPageTestCase,
        VenuePageTestCase,
        TimelinePageTestCase,
        RegistryPageTestCase,
        PurchaseItemTestCase,
        UtilityFunctionsTestCase,
        ErrorHandlingTestCase,
        SecurityTestCase,
        IntegrationTestCase
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    if not result.wasSuccessful():
        sys.exit(1)
