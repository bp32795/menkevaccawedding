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

from app import app, scrape_title_from_url


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
                'priority': 3,
                'image_url': 'https://example.com/vase.jpg',
                'price': 45.99,
                'bought': False,
                'title': 'Beautiful Vase',
                'bought_by': ''
            },
            {
                'id': 'item-2',
                'url': 'https://example.com/item2',
                'priority': 1,
                'image_url': 'https://example.com/coffee.jpg',
                'price': 129.99,
                'bought': True,
                'title': 'Coffee Maker',
                'bought_by': 'John Doe'
            },
            {
                'id': 'item-3',
                'url': 'https://example.com/item3',
                'priority': 2,
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
        self.assertIn(b'Together forever', response.data)
    
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
        self.assertIn(b'RSVP', response.data)
        self.assertIn(b'Coming Soon', response.data)
    
    def test_rsvp_placeholder_content(self):
        """Test that placeholder content is displayed"""
        response = self.client.get('/rsvp')
        self.assertIn(b'RSVP Form Coming Soon', response.data)
        self.assertIn(b'bp32795@gmail.com', response.data)


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
    
    @patch('app.get_cosmos_container')
    def test_registry_page_handles_no_container(self, mock_get_container):
        """Test that registry page handles Cosmos DB connection failure"""
        mock_get_container.return_value = None
        
        response = self.client.get('/registry')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registry items will appear here', response.data)
    
    @patch('app.get_cosmos_container')
    def test_registry_sorting_by_priority(self, mock_get_container):
        """Test that registry items are sorted by priority"""
        mock_container = Mock()
        mock_container.query_items.return_value = iter(self.mock_registry_data)
        mock_get_container.return_value = mock_container
        
        response = self.client.get('/registry')
        self.assertEqual(response.status_code, 200)
        
        content = response.data.decode('utf-8')
        vase_pos = content.find('Beautiful Vase')
        coffee_pos = content.find('Coffee Maker')
        
        # Beautiful Vase (priority 3) should come before Coffee Maker (priority 1)
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
