"""
Menke Vacca Wedding Website
A Flask web application for wedding RSVP and registry management
"""

from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from flask_mail import Mail, Message
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from markupsafe import escape
import os
from datetime import datetime, timezone
import random
import re
import requests
from bs4 import BeautifulSoup
import json
import logging
import uuid
from dotenv import load_dotenv

# Try to import Azure Communication Services (optional)
try:
    from azure.communication.email import EmailClient
    AZURE_EMAIL_AVAILABLE = True
except ImportError:
    AZURE_EMAIL_AVAILABLE = False
    print("Azure Communication Services not available. Using SMTP fallback.")

# Try to import Azure Cosmos DB
try:
    from azure.cosmos import CosmosClient, PartitionKey, exceptions as cosmos_exceptions
    COSMOS_AVAILABLE = True
except ImportError:
    COSMOS_AVAILABLE = False
    print("Azure Cosmos DB not available. Registry will not work.")

# Try to import Azure Blob Storage
try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
    BLOB_AVAILABLE = True
except ImportError:
    BLOB_AVAILABLE = False
    print("Azure Blob Storage not available. Image caching disabled.")

# Try to import OpenAI for AI-powered autofill
try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI not available. AI autofill disabled.")

# Try to import Azure Identity for managed identity auth
try:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    IDENTITY_AVAILABLE = True
except ImportError:
    IDENTITY_AVAILABLE = False

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Determine if we should use local SMTP server
use_local_smtp = (
    os.environ.get('FLASK_ENV') == 'development' and 
    not os.environ.get('MAIL_USERNAME')
)

# Configuration
if use_local_smtp:
    # Development configuration with local SMTP server
    app.config.update(
        MAIL_SERVER='localhost',
        MAIL_PORT=1025,
        MAIL_USE_TLS=False,
        MAIL_USE_SSL=False,
        MAIL_USERNAME=None,
        MAIL_PASSWORD=None,
        MAIL_DEFAULT_SENDER='dev@menkevaccawedding.com',
        MAIL_SUPPRESS_SEND=False
    )
    print("📧 Using local SMTP server for development")
else:
    # Production configuration - supports multiple email providers
    mail_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    mail_port = int(os.environ.get('MAIL_PORT', 587))
    mail_use_tls = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    
    app.config.update(
        MAIL_SERVER=mail_server,
        MAIL_PORT=mail_port,
        MAIL_USE_TLS=mail_use_tls,
        MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
        MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME')),
        MAIL_SUPPRESS_SEND=False if os.environ.get('MAIL_USERNAME') else True
    )
    
    # Log which email provider is being used
    if 'sendgrid' in mail_server:
        print(f"📧 Using SendGrid SMTP")
    elif 'gmail' in mail_server:
        print(f"📧 Using Gmail SMTP with {os.environ.get('MAIL_USERNAME')}")
    else:
        print(f"📧 Using custom SMTP server: {mail_server}:{mail_port}")
    
    if not os.environ.get('MAIL_USERNAME'):
        print("⚠️  Email not configured - emails will not be sent")

# Initialize Flask-Mail
mail = Mail(app)

# Cosmos DB configuration
COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT', '')
COSMOS_KEY = os.environ.get('COSMOS_KEY', '')
COSMOS_DATABASE = os.environ.get('COSMOS_DATABASE', 'wedding')
COSMOS_CONTAINER = os.environ.get('COSMOS_CONTAINER', 'registry')
COSMOS_RESPONSE_CONTAINER = os.environ.get(
    'COSMOS_RESPONSE_CONTAINER', 'wedding-responses')
RSVP_EDIT_LINK_MAX_AGE = 60 * 60 * 24 * 180
RSVP_EDIT_LINK_SALT = 'rsvp-edit-link'

# Blob Storage configuration
BLOB_CONNECTION_STRING = os.environ.get('BLOB_CONNECTION_STRING', '')
BLOB_CONTAINER_NAME = os.environ.get('BLOB_CONTAINER_NAME', 'registry-images')


def get_cosmos_container():
    """Initialize and return the Cosmos DB container client"""
    if not COSMOS_AVAILABLE:
        app.logger.error("❌ Azure Cosmos DB library not available")
        return None

    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        app.logger.error("❌ COSMOS_ENDPOINT or COSMOS_KEY not configured")
        return None

    try:
        client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        database = client.create_database_if_not_exists(id=COSMOS_DATABASE)
        container = database.create_container_if_not_exists(
            id=COSMOS_CONTAINER,
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400
        )
        return container
    except Exception as e:
        app.logger.error(f"❌ Error connecting to Cosmos DB: {e}")
        return None


def get_response_container():
    """Initialize the Cosmos DB container for RSVPs and contact messages."""
    if not COSMOS_AVAILABLE or not COSMOS_ENDPOINT or not COSMOS_KEY:
        app.logger.error("Cosmos DB is not configured for wedding responses")
        return None

    try:
        client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        database = client.create_database_if_not_exists(id=COSMOS_DATABASE)
        return database.create_container_if_not_exists(
            id=COSMOS_RESPONSE_CONTAINER,
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400
        )
    except Exception as error:
        app.logger.error(f"Error connecting to response database: {error}")
        return None


def create_captcha(purpose):
    """Create a small arithmetic challenge stored in the visitor's session."""
    first_number = random.randint(1, 9)
    second_number = random.randint(1, 9)
    session[f'captcha_{purpose}'] = first_number + second_number
    return f"What is {first_number} + {second_number}?"


def validate_captcha(purpose, answer, honeypot=''):
    """Validate and consume a bot challenge and reject honeypot submissions."""
    expected_answer = session.pop(f'captcha_{purpose}', None)
    if honeypot or expected_answer is None:
        return False
    try:
        return int(answer) == expected_answer
    except (TypeError, ValueError):
        return False


def normalize_email(email):
    """Return a normalized email address, or an empty string when invalid."""
    normalized_email = str(email or '').strip().lower()
    if len(normalized_email) > 254:
        return ''
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', normalized_email):
        return ''
    return normalized_email


def find_rsvp_by_email(container, email):
    """Find the first RSVP associated with a normalized email address."""
    results = list(container.query_items(
        query=(
            'SELECT * FROM c WHERE c.document_type = @document_type '
            'AND c.email = @email'
        ),
        parameters=[
            {'name': '@document_type', 'value': 'rsvp'},
            {'name': '@email', 'value': email}
        ],
        enable_cross_partition_query=True
    ))
    return results[0] if results else None


def generate_rsvp_edit_token(rsvp_record):
    """Create a signed token that identifies one RSVP and email address."""
    serializer = URLSafeTimedSerializer(app.secret_key)
    return serializer.dumps(
        {'id': rsvp_record['id'], 'email': rsvp_record['email']},
        salt=RSVP_EDIT_LINK_SALT
    )


def get_rsvp_from_edit_token(token):
    """Validate an edit token and return its RSVP, or None when invalid."""
    serializer = URLSafeTimedSerializer(app.secret_key)
    try:
        token_data = serializer.loads(
            token,
            salt=RSVP_EDIT_LINK_SALT,
            max_age=RSVP_EDIT_LINK_MAX_AGE
        )
    except (BadSignature, SignatureExpired):
        return None

    rsvp_id = token_data.get('id')
    email = normalize_email(token_data.get('email'))
    if not rsvp_id or not email:
        return None

    container = get_response_container()
    if not container:
        return None
    try:
        rsvp_record = container.read_item(item=rsvp_id, partition_key=rsvp_id)
    except Exception:
        return None
    if (rsvp_record.get('document_type') != 'rsvp' or
            rsvp_record.get('email') != email):
        return None
    return rsvp_record


def get_blob_container_client():
    """Initialize and return the Blob Storage container client"""
    if not BLOB_AVAILABLE:
        app.logger.error("❌ Azure Blob Storage library not available")
        return None

    if not BLOB_CONNECTION_STRING:
        app.logger.error("❌ BLOB_CONNECTION_STRING not configured")
        return None

    try:
        blob_service = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
        container_client = blob_service.get_container_client(BLOB_CONTAINER_NAME)
        # Create container if it doesn't exist
        try:
            container_client.get_container_properties()
        except Exception:
            container_client.create_container()
        return container_client
    except Exception as e:
        app.logger.error(f"❌ Error connecting to Blob Storage: {e}")
        return None


def cache_image_to_blob(image_url, item_id):
    """Download an image from a URL and upload it to Azure Blob Storage.
    Returns the blob name on success, or None on failure.
    """
    container_client = get_blob_container_client()
    if not container_client or not image_url:
        return None

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }
        resp = requests.get(image_url, headers=headers, timeout=15, stream=True)
        resp.raise_for_status()

        # Determine content type and extension
        content_type = resp.headers.get('Content-Type', 'image/jpeg')
        ext_map = {
            'image/jpeg': '.jpg', 'image/png': '.png',
            'image/webp': '.webp', 'image/gif': '.gif',
        }
        ext = ext_map.get(content_type.split(';')[0].strip(), '.jpg')
        blob_name = f"{item_id}{ext}"

        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(
            resp.content,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type.split(';')[0].strip()),
        )
        app.logger.info(f"✅ Cached image for item {item_id} as {blob_name}")
        return blob_name
    except Exception as e:
        app.logger.warning(f"⚠️ Could not cache image for item {item_id}: {e}")
        return None


def scrape_title_from_url(url):
    """Scrape title from product URL if title is missing"""
    result = scrape_product_metadata(url)
    return result.get('title') or 'Product'


def scrape_product_metadata(url):
    """Scrape product metadata from URL using OG tags and HTML selectors.
    Returns dict with title, image_url, price (best-effort).
    """
    result = {'title': '', 'image_url': '', 'price': 0}
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 403:
            result['warning'] = f'Site blocked automated access (HTTP 403). You may need to fill in details manually.'
            return result
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')

        # --- Title ---
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content', '').strip():
            result['title'] = og_title['content'].strip()
        else:
            for sel in ['h1', '.product-title', '[data-testid="product-title"]', 'title']:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    result['title'] = el.get_text(strip=True)
                    break

        # --- Image ---
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content', '').strip():
            result['image_url'] = og_image['content'].strip()

        # --- Price ---
        # Try OG price
        og_price = soup.find('meta', property='og:price:amount') or soup.find('meta', property='product:price:amount')
        if og_price and og_price.get('content', '').strip():
            try:
                result['price'] = float(og_price['content'].strip().replace(',', ''))
            except ValueError:
                pass
        # Fallback: JSON-LD
        if not result['price']:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    ld = json.loads(script.string)
                    items = ld if isinstance(ld, list) else [ld]
                    for item in items:
                        offers = item.get('offers', item.get('Offers', {}))
                        if isinstance(offers, list):
                            offers = offers[0] if offers else {}
                        price_val = offers.get('price') or offers.get('lowPrice')
                        if price_val:
                            result['price'] = float(str(price_val).replace(',', ''))
                            break
                except Exception:
                    continue

        return result
    except Exception as e:
        app.logger.warning(f"Could not scrape metadata from {url}: {e}")
        return result


def ai_extract_product_info(url, html_snippet):
    """Use Azure OpenAI to extract product info from HTML when OG tags are sparse."""
    if not OPENAI_AVAILABLE:
        return {}

    endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
    key = os.environ.get('AZURE_OPENAI_KEY')
    deployment = os.environ.get('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o-mini')

    if not endpoint:
        app.logger.info("Azure OpenAI not configured, skipping AI autofill")
        return {}

    try:
        # Prefer managed identity; fall back to API key for local dev
        if IDENTITY_AVAILABLE and not key:
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
                api_version="2024-10-21"
            )
        elif key:
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=key,
                api_version="2024-10-21"
            )
        else:
            app.logger.info("No Azure OpenAI credentials available")
            return {}

        # Trim HTML to a reasonable size
        trimmed = html_snippet[:8000]

        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": (
                    "You extract product information from HTML. "
                    "Return ONLY valid JSON with keys: title, image_url, price. "
                    "price should be a number (no $ sign). "
                    "If you cannot determine a field, use an empty string for text or 0 for price."
                )},
                {"role": "user", "content": f"URL: {url}\n\nHTML:\n{trimmed}"}
            ],
            temperature=0,
            max_tokens=200
        )

        text = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if text.startswith('```'):
            text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
        return json.loads(text)
    except Exception as e:
        app.logger.warning(f"AI extraction failed: {e}")
        return {}

@app.route('/')
def home():
    """Home page with wedding information"""
    return render_template('home.html')

@app.route('/rsvp')
def rsvp():
    """Display RSVP creation and change controls."""
    return render_template(
        'rsvp.html',
        rsvp_captcha=create_captcha('rsvp'),
        lookup_captcha=create_captcha('lookup'),
        initial_rsvp=None
    )


@app.route('/rsvp/edit/<token>')
def edit_rsvp_from_link(token):
    """Authorize an RSVP edit from a signed confirmation-email link."""
    rsvp_record = get_rsvp_from_edit_token(token)
    if not rsvp_record:
        flash('That RSVP edit link is invalid or has expired.', 'error')
        return redirect(url_for('rsvp'))

    session['editable_rsvp_id'] = rsvp_record['id']
    session['editable_rsvp_email'] = rsvp_record['email']
    return render_template(
        'rsvp.html',
        rsvp_captcha=create_captcha('rsvp'),
        lookup_captcha=create_captcha('lookup'),
        initial_rsvp={
            'party_names': rsvp_record.get('party_names', ''),
            'attending': rsvp_record.get('attending', ''),
            'party_size': rsvp_record.get('party_size', 1),
            'email': rsvp_record.get('email', '')
        }
    )


@app.route('/api/rsvp', methods=['POST'])
def submit_rsvp():
    """Create a new RSVP or update a response authorized by email lookup."""
    data = request.get_json(silent=True) or {}
    is_update = data.get('is_update') is True

    if data.get('website'):
        return jsonify({'error': 'Unable to verify submission.'}), 400
    if not is_update and not validate_captcha(
            'rsvp', data.get('captcha'), data.get('website')):
        return jsonify({'error': 'Bot verification failed. Please try again.'}), 400

    party_names = str(data.get('party_names') or '').strip()
    attending = str(data.get('attending') or '').strip().lower()
    email = normalize_email(data.get('email'))
    try:
        party_size = int(data.get('party_size'))
    except (TypeError, ValueError):
        party_size = 0

    if not party_names or len(party_names) > 1000:
        return jsonify({'error': 'Please provide the names in your party.'}), 400
    if attending not in {'yes', 'no'}:
        return jsonify({'error': 'Please select whether your party will attend.'}), 400
    if not 1 <= party_size <= 20:
        return jsonify({'error': 'Party size must be between 1 and 20.'}), 400
    if not email:
        return jsonify({'error': 'Please provide a valid email address.'}), 400

    container = get_response_container()
    if not container:
        return jsonify({'error': 'The RSVP system is unavailable. Please try again.'}), 503

    now = datetime.now(timezone.utc).isoformat()
    if is_update:
        rsvp_id = session.get('editable_rsvp_id')
        authorized_email = session.get('editable_rsvp_email')
        if not rsvp_id or authorized_email != email:
            return jsonify({'error': 'Please look up your RSVP again before editing.'}), 403
        try:
            rsvp_record = container.read_item(item=rsvp_id, partition_key=rsvp_id)
        except Exception:
            return jsonify({'error': 'RSVP not found.'}), 404
        if (rsvp_record.get('document_type') != 'rsvp' or
                rsvp_record.get('email') != authorized_email):
            return jsonify({'error': 'RSVP not found.'}), 404
        rsvp_record.update({
            'party_names': party_names,
            'attending': attending,
            'party_size': party_size,
            'email': email,
            'updated_at': now
        })
        container.replace_item(item=rsvp_id, body=rsvp_record)
        session.pop('editable_rsvp_id', None)
        session.pop('editable_rsvp_email', None)
        send_rsvp_notification_email(rsvp_record, is_update=True)
        edit_url = url_for(
            'edit_rsvp_from_link',
            token=generate_rsvp_edit_token(rsvp_record),
            _external=True,
            _scheme='https'
        )
        send_guest_rsvp_confirmation(rsvp_record, edit_url)
        return jsonify({'success': True, 'message': 'Your RSVP has been updated.'})

    if find_rsvp_by_email(container, email):
        return jsonify({
            'error': 'An RSVP already exists for this email. Use Change RSVP instead.'
        }), 409

    rsvp_record = {
        'id': str(uuid.uuid4()),
        'document_type': 'rsvp',
        'party_names': party_names,
        'attending': attending,
        'party_size': party_size,
        'email': email,
        'created_at': now,
        'updated_at': now
    }
    container.create_item(body=rsvp_record)
    send_rsvp_notification_email(rsvp_record, is_update=False)
    edit_url = url_for(
        'edit_rsvp_from_link',
        token=generate_rsvp_edit_token(rsvp_record),
        _external=True,
        _scheme='https'
    )
    send_guest_rsvp_confirmation(rsvp_record, edit_url)
    return jsonify({
        'success': True,
        'message': 'Thank you. Your RSVP has been received.'
    }), 201


@app.route('/api/rsvp/lookup', methods=['POST'])
def lookup_rsvp():
    """Look up an RSVP by email and authorize editing it in this session."""
    data = request.get_json(silent=True) or {}
    if not validate_captcha('lookup', data.get('captcha'), data.get('website')):
        return jsonify({'error': 'Bot verification failed. Please try again.'}), 400

    email = normalize_email(data.get('email'))
    if not email:
        return jsonify({'error': 'Please provide a valid email address.'}), 400

    container = get_response_container()
    if not container:
        return jsonify({'error': 'The RSVP system is unavailable. Please try again.'}), 503

    rsvp_record = find_rsvp_by_email(container, email)
    if not rsvp_record:
        return jsonify({
            'error': 'No RSVP was found for that email. Please contact us for help.'
        }), 404

    session['editable_rsvp_id'] = rsvp_record['id']
    session['editable_rsvp_email'] = email
    return jsonify({'success': True, 'rsvp': {
        'party_names': rsvp_record.get('party_names', ''),
        'attending': rsvp_record.get('attending', ''),
        'party_size': rsvp_record.get('party_size', 1),
        'email': rsvp_record.get('email', '')
    }})


@app.route('/api/captcha/<purpose>')
def refresh_captcha(purpose):
    """Return a fresh bot challenge for an RSVP modal."""
    if purpose not in {'rsvp', 'lookup'}:
        return jsonify({'error': 'Unknown verification purpose.'}), 404
    return jsonify({'question': create_captcha(purpose)})


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Display and process the contact form."""
    if request.method == 'GET':
        return render_template('contact.html', captcha=create_captcha('contact'))

    if not validate_captcha(
            'contact', request.form.get('captcha'), request.form.get('website')):
        flash('Bot verification failed. Please try again.', 'error')
        return redirect(url_for('contact'))

    name = request.form.get('name', '').strip()
    email = normalize_email(request.form.get('email'))
    note = request.form.get('note', '').strip()
    if not name or len(name) > 200 or not email or not note or len(note) > 5000:
        flash('Please provide a valid name, email address, and note.', 'error')
        return redirect(url_for('contact'))

    container = get_response_container()
    if not container:
        flash('The contact form is unavailable. Please try again later.', 'error')
        return redirect(url_for('contact'))

    message_record = {
        'id': str(uuid.uuid4()),
        'document_type': 'contact',
        'name': name,
        'email': email,
        'note': note,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    container.create_item(body=message_record)
    send_contact_notification_email(message_record)
    flash('Your message has been sent. We will be in touch soon.', 'success')
    return redirect(url_for('contact'))

@app.route('/venue')
def venue():
    """Venue page with location and photo gallery"""
    return render_template('venue.html')

@app.route('/ourstory')
def timeline():
    """Timeline page with relationship story"""
    return render_template('timeline.html')

@app.route('/registry')
def registry():
    """Registry page displaying items from Cosmos DB"""
    try:
        container = get_cosmos_container()
        if not container:
            flash('Unable to load registry at this time. Please try again later.', 'error')
            return render_template('registry.html', items=[])

        query = "SELECT * FROM c"
        raw_items = list(container.query_items(query=query, enable_cross_partition_query=True))

        items = []
        for item in raw_items:
            # Scrape title if missing
            if not item.get('title') and item.get('url'):
                item['title'] = scrape_title_from_url(item['url'])

            # Ensure numeric types
            try:
                item['price'] = float(item.get('price', 0)) if item.get('price') else 0
            except (ValueError, TypeError):
                item['price'] = 0

            # Use cached image URL if available
            if item.get('cached_image'):
                item['display_image_url'] = url_for('registry_image', blob_name=item['cached_image'])
            else:
                item['display_image_url'] = item.get('image_url', '')

            items.append(item)

        # Sort by price
        items.sort(key=lambda x: x['price'])

        return render_template('registry.html', items=items)

    except Exception as e:
        app.logger.error(f"Error loading registry: {e}")
        flash('Unable to load registry at this time. Please try again later.', 'error')
        return render_template('registry.html', items=[])


@app.route('/registry/image/<blob_name>')
def registry_image(blob_name):
    """Serve a cached registry image from Azure Blob Storage"""
    from flask import Response

    # Sanitize blob_name to prevent path traversal
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+\.\w{2,4}$', blob_name):
        return '', 404

    container_client = get_blob_container_client()
    if not container_client:
        return '', 404

    try:
        blob_client = container_client.get_blob_client(blob_name)
        download = blob_client.download_blob()
        content_type = download.properties.content_settings.content_type or 'image/jpeg'

        return Response(
            download.readall(),
            content_type=content_type,
            headers={
                'Cache-Control': 'public, max-age=604800',  # 7 days
            },
        )
    except Exception:
        return '', 404

def send_email_via_azure(
    to_email, subject, body, from_email=None, html_body=None):
    """
    Send email using Azure Communication Services
    """
    app.logger.info("🔄 Attempting Azure Communication Services email...")
    
    if not AZURE_EMAIL_AVAILABLE:
        app.logger.warning("❌ Azure Communication Services library not available")
        return False
        
    try:
        # Get connection string from environment
        connection_string = os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING')
        if not connection_string:
            app.logger.warning("❌ Azure Communication Services not configured - no connection string")
            return False
            
        app.logger.info("🔗 Azure connection string found, initializing client...")
        
        # Initialize the EmailClient
        email_client = EmailClient.from_connection_string(connection_string)
        app.logger.info("✅ EmailClient initialized successfully")
        
        # Set default from email - try Azure managed domain first
        if not from_email:
            from_email = os.environ.get('EMAIL_FROM_ADDRESS')
            if not from_email:
                # Try to use a generic Azure managed domain format as fallback
                app.logger.warning("⚠️ EMAIL_FROM_ADDRESS not set, using fallback domain")
                from_email = 'donotreply@donotreply.azurecomm.net'
                app.logger.info(f"🔄 Using fallback Azure managed domain: {from_email}")
            else:
                app.logger.info(f"📤 Using configured from address: {from_email}")
        
        app.logger.info(f"📤 From: {from_email}")
        recipients = to_email if isinstance(to_email, list) else [to_email]
        app.logger.info(f"📨 To: {', '.join(recipients)}")
        
        # Create the email message
        message = {
            "senderAddress": from_email,
            "recipients": {
                "to": [{"address": recipient} for recipient in recipients]
            },
            "content": {
                "subject": subject,
                "plainText": body
            }
        }
        if html_body:
            message['content']['html'] = html_body
        
        app.logger.info("📧 Sending email via Azure Communication Services...")
        
        # Send the email
        poller = email_client.begin_send(message)
        result = poller.result()
        
        app.logger.info(f"✅ Email sent via Azure Communication Services. Operation ID: {result['id']}")
        return True
        
    except Exception as e:
        error_message = str(e)
        app.logger.error(f"❌ Error sending email via Azure Communication Services: {error_message}")
        app.logger.error(f"🔍 Exception type: {type(e).__name__}")
        
        # Provide specific guidance for common errors
        if "DomainNotLinked" in error_message:
            app.logger.error("💡 SOLUTION: Your email domain is not linked to Azure Communication Services")
            app.logger.error("💡 Quick fix: Use Azure managed domain in Email Communication Services → Provision domains")
            app.logger.error("💡 Or configure custom domain with proper DNS records")
            app.logger.error("💡 See FIX_AZURE_EMAIL.md for detailed instructions")
        elif "Unauthorized" in error_message:
            app.logger.error("💡 Fix: Check your AZURE_COMMUNICATION_CONNECTION_STRING")
        elif "InvalidSender" in error_message:
            app.logger.error("💡 Fix: Verify your EMAIL_FROM_ADDRESS matches your linked domain")
        
        return False


def get_notification_recipients():
    """Return the unique email recipients for wedding form notifications."""
    configured_recipients = os.environ.get(
        'EMAIL_TO_ADDRESS', 'bp32795@gmail.com').split(',')
    recipients = [recipient.strip() for recipient in configured_recipients]
    recipients.append('sofiavacca97@gmail.com')
    return list(dict.fromkeys(recipient for recipient in recipients if recipient))


def send_couple_notification(subject, body):
    """Send a form notification to both members of the couple."""
    recipients = get_notification_recipients()
    if os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING'):
        if send_email_via_azure(recipients, subject, body):
            return True

    try:
        if (app.config.get('MAIL_USERNAME') and
                not app.config.get('MAIL_SUPPRESS_SEND')):
            mail.send(Message(
                subject=subject,
                recipients=recipients,
                sender=app.config['MAIL_DEFAULT_SENDER'],
                body=body
            ))
            return True
    except Exception as error:
        app.logger.error(f"Error sending form notification: {error}")
    return False


def send_guest_rsvp_confirmation(data, edit_url):
    """Send RSVP details and a signed edit link to the submitting guest."""
    attendance = 'Yes' if data['attending'] == 'yes' else 'No'
    subject = 'Your Menke & Vacca Wedding RSVP'
    plain_body = (
        "Thank you for your response! Please find your submission below:\n\n"
        f"Party names: {data['party_names']}\n"
        f"Attending: {attendance}\n"
        f"Party size: {data['party_size']}\n"
        f"Email: {data['email']}\n\n"
        f"Click here to change any details: {edit_url}\n\n"
        "Thanks,\n"
        "Brandon and Sofie"
    )
    safe_party_names = escape(data['party_names'])
    safe_email = escape(data['email'])
    safe_edit_url = escape(edit_url)
    html_body = (
        "<p>Thank you for your response! Please find your submission below:</p>"
        "<p>"
        f"<strong>Party names:</strong> {safe_party_names}<br>"
        f"<strong>Attending:</strong> {attendance}<br>"
        f"<strong>Party size:</strong> {data['party_size']}<br>"
        f"<strong>Email:</strong> {safe_email}"
        "</p>"
        f'<p><a href="{safe_edit_url}">Click here to change any details.</a></p>'
        "<p>Thanks,<br>Brandon and Sofie</p>"
    )
    recipients = [data['email']]

    if os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING'):
        if send_email_via_azure(
                recipients, subject, plain_body, html_body=html_body):
            return True

    try:
        if (app.config.get('MAIL_USERNAME') and
                not app.config.get('MAIL_SUPPRESS_SEND')):
            mail.send(Message(
                subject=subject,
                recipients=recipients,
                sender=app.config['MAIL_DEFAULT_SENDER'],
                body=plain_body,
                html=html_body
            ))
            return True
    except Exception as error:
        app.logger.error(f"Error sending RSVP confirmation: {error}")
    return False


def send_rsvp_notification_email(data, is_update=False):
    """Email the couple when an RSVP is created or changed."""
    action = 'Updated RSVP' if is_update else 'New RSVP'
    attendance = 'Yes' if data['attending'] == 'yes' else 'No'
    body = (
        f"{action} received.\n\n"
        f"Party names: {data['party_names']}\n"
        f"Attending: {attendance}\n"
        f"Party size: {data['party_size']}\n"
        f"Email: {data['email']}\n"
        f"Submitted: {data['updated_at']}"
    )
    return send_couple_notification(
        f"{action}: {data['party_names']}", body)


def send_contact_notification_email(data):
    """Email the couple when a contact form message is submitted."""
    body = (
        "A new contact message was received.\n\n"
        f"Name: {data['name']}\n"
        f"Email: {data['email']}\n"
        f"Note: {data['note']}\n"
        f"Submitted: {data['created_at']}"
    )
    return send_couple_notification(f"Wedding website message from {data['name']}", body)

def send_registry_notification_email(data):
    """
    Send registry purchase notification - tries Azure first, then SMTP fallback
    """
    to_email = os.environ.get('EMAIL_TO_ADDRESS', 'bp32795@gmail.com')
    subject = f"Registry Item Purchased: {data['item_title']}"
    
    app.logger.info(f"📧 Preparing email notification:")
    app.logger.info(f"   To: {to_email}")
    app.logger.info(f"   Subject: {subject}")
    app.logger.info(f"   Item: {data['item_title']}")
    app.logger.info(f"   Buyer: {data['name']}")
    
    body = f"""
Someone has purchased an item from your wedding registry!

Details:
- Item: {data['item_title']}
- Purchased by: {data['name']}
- Purchase date: {data['purchase_date']}
- Item URL: {data['item_url']}"""

    # Add delivery date if provided
    if data.get('delivery_date'):
        body += f"\n- Estimated delivery: {data['delivery_date']}"
    
    # Add note if provided
    if data.get('note'):
        body += f"""

Personal message from {data['name']}:
"{data['note']}"
"""
    
    body += """

Congratulations!

---
Menke & Vacca Wedding Registry
https://menkevaccawedding.azurewebsites.net
"""
    
    # Check Azure Communication Services first
    azure_connection = os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING')
    app.logger.info(f"🔍 Azure Connection String configured: {azure_connection is not None}")
    if azure_connection:
        app.logger.info("🔄 Trying Azure Communication Services...")
        if send_email_via_azure(to_email, subject, body):
            app.logger.info("✅ Email sent via Azure Communication Services")
            return True
        else:
            app.logger.warning("⚠️ Azure Communication Services failed, trying SMTP fallback")
    else:
        app.logger.info("ℹ️ Azure Communication Services not configured, trying SMTP")
    
    # Fall back to SMTP (Gmail/SendGrid)
    mail_username = app.config.get('MAIL_USERNAME')
    mail_suppress = app.config.get('MAIL_SUPPRESS_SEND')
    app.logger.info(f"🔍 SMTP configured: {mail_username is not None}")
    app.logger.info(f"🔍 SMTP suppressed: {mail_suppress}")
    
    try:
        if mail_username and not mail_suppress:
            app.logger.info("🔄 Sending via SMTP...")
            msg = Message(
                subject=subject,
                recipients=[to_email],
                sender=app.config['MAIL_DEFAULT_SENDER'],
                body=body
            )
            mail.send(msg)
            app.logger.info("✅ Email sent via SMTP")
            return True
        else:
            app.logger.warning("⚠️ SMTP email not configured or suppressed - email notification skipped")
            return False
    except Exception as e:
        app.logger.error(f"❌ Error sending email via SMTP: {e}")
        return False

@app.route('/purchase_item', methods=['POST'])
def purchase_item():
    """Handle item purchase form submission"""
    app.logger.info("🛒 Purchase item request received")

    try:
        data = request.get_json()
        app.logger.info(f"📦 Purchase data received: {data}")

        # Validate required fields
        required_fields = ['name', 'purchase_date', 'item_title', 'item_id']
        for field in required_fields:
            if not data.get(field):
                app.logger.error(f"❌ Missing required field: {field}")
                return jsonify({'error': f'Missing required field: {field}'}), 400

        app.logger.info("✅ All required fields present")

        # Update Cosmos DB
        container = get_cosmos_container()
        if not container:
            app.logger.error("❌ Unable to connect to Cosmos DB")
            return jsonify({'error': 'Unable to connect to registry system'}), 500

        try:
            item = container.read_item(item=data['item_id'], partition_key=data['item_id'])
            item['bought'] = True
            item['bought_by'] = data['name']
            container.replace_item(item=item['id'], body=item)
            app.logger.info("✅ Cosmos DB updated successfully")
        except Exception as e:
            app.logger.warning(f"⚠️ Could not update item {data['item_id']}: {e}")

        # Send email notification
        try:
            email_data = {
                'item_title': data['item_title'],
                'name': data['name'],
                'purchase_date': data['purchase_date'],
                'item_url': data.get('item_url', ''),
                'delivery_date': data.get('delivery_date', ''),
                'note': data.get('note', '')
            }
            email_sent = send_registry_notification_email(email_data)
            if email_sent:
                app.logger.info(f"✅ Email notification sent for: {data['item_title']}")
            else:
                app.logger.warning(f"⚠️ Email not sent - purchase recorded: {data['item_title']}")
        except Exception as e:
            app.logger.error(f"❌ Error sending email: {e}")

        return jsonify({'success': True, 'message': 'Thank you for your purchase!'})

    except Exception as e:
        app.logger.error(f"❌ Error processing purchase: {e}")
        return jsonify({'error': 'An error occurred processing your purchase'}), 500


# --- Registry Admin Routes (direct access only, no nav link) ---

@app.route('/registry/admin')
def registry_admin():
    """Admin page for managing registry items"""
    try:
        container = get_cosmos_container()
        items = []
        if container:
            query = "SELECT * FROM c"
            items = list(container.query_items(query=query, enable_cross_partition_query=True))
        return render_template('registry_admin.html', items=items)
    except Exception as e:
        app.logger.error(f"Error loading admin page: {e}")
        return render_template('registry_admin.html', items=[])


@app.route('/registry/admin/add', methods=['POST'])
def registry_admin_add():
    """Add a new registry item"""
    try:
        container = get_cosmos_container()
        if not container:
            return jsonify({'error': 'Unable to connect to database'}), 500

        data = request.get_json()
        item = {
            'id': str(uuid.uuid4()),
            'url': data.get('url', ''),
            'image_url': data.get('image_url', ''),
            'price': float(data.get('price', 0)),
            'bought': False,
            'title': data.get('title', ''),
            'bought_by': '',
            'cached_image': ''
        }

        # Auto-scrape title if not provided
        if not item['title'] and item['url']:
            item['title'] = scrape_title_from_url(item['url'])

        # Cache image to blob storage
        if item['image_url']:
            blob_name = cache_image_to_blob(item['image_url'], item['id'])
            if blob_name:
                item['cached_image'] = blob_name

        container.create_item(body=item)
        return jsonify({'success': True, 'item': item})

    except Exception as e:
        app.logger.error(f"Error adding item: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/registry/admin/delete', methods=['POST'])
def registry_admin_delete():
    """Delete a registry item"""
    try:
        container = get_cosmos_container()
        if not container:
            return jsonify({'error': 'Unable to connect to database'}), 500

        data = request.get_json()
        item_id = data.get('id')
        if not item_id:
            return jsonify({'error': 'Item ID required'}), 400

        container.delete_item(item=item_id, partition_key=item_id)
        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error deleting item: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/registry/admin/edit', methods=['POST'])
def registry_admin_edit():
    """Edit a registry item"""
    try:
        container = get_cosmos_container()
        if not container:
            return jsonify({'error': 'Unable to connect to database'}), 500

        data = request.get_json()
        item_id = data.get('id')
        if not item_id:
            return jsonify({'error': 'Item ID required'}), 400

        item = container.read_item(item=item_id, partition_key=item_id)
        # Update only provided fields
        for field in ['url', 'title', 'image_url']:
            if field in data:
                item[field] = data[field]
        if 'price' in data:
            item['price'] = float(data['price'])
        if 'bought' in data:
            item['bought'] = bool(data['bought'])
        if 'bought_by' in data:
            item['bought_by'] = data['bought_by']

        container.replace_item(item=item_id, body=item)
        return jsonify({'success': True, 'item': item})

    except Exception as e:
        app.logger.error(f"Error editing item: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/registry/admin/autofill', methods=['POST'])
def registry_admin_autofill():
    """Auto-fill product fields from URL using OG tags, then AI fallback."""
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    # Step 1: OG / HTML scraping
    result = scrape_product_metadata(url)
    source = 'scrape'

    # If the site blocked us, return early with the warning
    if result.get('warning'):
        result['source'] = 'blocked'
        return jsonify(result)

    # Step 2: If we're missing key fields, try AI
    missing_title = not result.get('title')
    missing_image = not result.get('image_url')
    missing_price = not result.get('price')

    if missing_title or (missing_image and missing_price):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            html_snippet = resp.text
        except Exception:
            html_snippet = ''

        if html_snippet:
            ai_result = ai_extract_product_info(url, html_snippet)
            if ai_result:
                source = 'ai'
                # Fill in only what's missing
                if missing_title and ai_result.get('title'):
                    result['title'] = ai_result['title']
                if missing_image and ai_result.get('image_url'):
                    result['image_url'] = ai_result['image_url']
                if missing_price and ai_result.get('price'):
                    try:
                        result['price'] = float(ai_result['price'])
                    except (ValueError, TypeError):
                        pass

    result['source'] = source
    return jsonify(result)


@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template('404.html'), 404


@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Start local SMTP server if in development mode
    if use_local_smtp:
        try:
            from dev_smtp_server import start_smtp_server
            smtp_thread = start_smtp_server()
            print("📧 Local SMTP server started for email testing")
        except Exception as e:
            print(f"⚠️  Could not start local SMTP server: {e}")
    
    # Set up logging
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Wedding website startup')
    
    app.run(debug=True, host='0.0.0.0', port=5000)
