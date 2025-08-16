# api_client/alireza_api_client.py

import requests
import logging
import json

# غیرفعال کردن هشدارهای مربوط به SSL
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)

class AlirezaAPIClient:
    def __init__(self, panel_url = 'https://pay.alamornetwork.ir:2053/C2v8tOan9RYt5E9', username = 'sirius', password = '22331144'):
        self.base_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
        self.is_logged_in = False
        self.api_base_path = "/xui/API/inbounds" # مسیر استاندارد علیرضا
        logger.info(f"AlirezaAPIClient initialized for {self.base_url}")
    def _request(self, method, path, **kwargs):
        """یک متد مرکزی برای ارسال تمام درخواست‌ها."""
        if not path.startswith('/'):
            path = '/' + path
        
        if not self.is_logged_in and path != '/login':
            if not self.login():
                return None

        url = self.base_url + path
        try:
            response = self.session.request(method, url, verify=False, timeout=20, **kwargs)
            if response.status_code in [401, 403]:
                logger.warning("Authentication error. Re-logging in...")
                if not self.login(): return None
                response = self.session.request(method, url, verify=False, timeout=20, **kwargs)

            response.raise_for_status()
            if not response.text:
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Request failed for {path}: {e}")
            return None

    def login(self):
        """ --- FINAL VERSION: Smart cookie detection --- """
        self.is_logged_in = False
        payload = {'username': self.username, 'password': self.password}
        response_data = self._request('post', '/login', data=payload)
        
        if response_data and response_data.get('success'):
            # --- THE FIX IS HERE ---
            # We use the same robust check here.
            if self.session.cookies:
                self.is_logged_in = True
                cookie_names = '; '.join([f'{c.name}' for c in self.session.cookies])
                logger.info(f"Successfully logged in. Found session cookie(s): {cookie_names}")
                return True
            else:
                logger.error("Login API call was successful, but the panel did not return any session cookie.")
                return False
        else:
            logger.error(f"Login failed for {self.base_url}.")
            return False

    def check_login(self):
        """بررسی اعتبار لاگین."""
        if self.is_logged_in:
            return True
        return self.login()

    def add_client(self, data):
        """Adds a new client."""
        full_path = self.api_base_path + "/addClient/"
        response_data = self._request('post', full_path, json=data)
        if response_data and response_data.get('success'):
            return True
        
        # --- بخش جدید برای لاگ کردن خطای پنل ---
        error_msg = response_data.get('msg', 'Unknown error from panel') if response_data else "No response from panel"
        logger.error(f"AlirezaPanel: Failed to add client. Panel response: '{error_msg}'")
        return False

    def get_inbound(self, inbound_id):
        """اطلاعات یک اینباند خاص را دریافت می‌کند."""
        full_path = f"{self.api_base_path}/get/{inbound_id}"
        response_data = self._request('get', full_path)
        if response_data and response_data.get('success'):
            return response_data.get('obj')
        return None

    def list_inbounds(self):
        """
        --- CORRECTED VERSION ---
        Gets the list of all inbounds for Alireza panels.
        """
        full_path = self.api_base_path + "/"
        # Alireza panel uses GET for listing inbounds
        response_data = self._request('get', full_path)
        if response_data and response_data.get('success'):
            return response_data.get('obj', [])
        logger.error(f"Failed to get inbound list from Alireza panel. Response: {response_data}")
        return []

    def get_client_traffic_by_id(self, client_id):
        """Gets traffic statistics for a specific client by ID."""
        if not self.check_login():
            logger.error("Not logged in to Alireza panel. Cannot get client traffic.")
            return None
        
        endpoint = f"{self.api_base_path}/getClientTrafficsById/{client_id}"
        response = self._request("GET", endpoint)
        
        if response and response.get('success'):
            return response.get('obj', {})
        else:
            logger.warning(f"Failed to get traffic for client ID {client_id}")
            return None

    def get_client_info(self, client_id):
        """Gets detailed information for a specific client by ID."""
        if not self.check_login():
            logger.error("Not logged in to Alireza panel. Cannot get client info.")
            return None
        
        # ابتدا تمام inbounds را دریافت می‌کنیم
        inbounds = self.list_inbounds()
        if not inbounds:
            return None
        
        # در تمام inbounds دنبال کلاینت می‌گردیم
        for inbound in inbounds:
            if 'settings' in inbound and 'clients' in inbound['settings']:
                for client in inbound['settings']['clients']:
                    if client.get('id') == client_id or client.get('email') == client_id:
                        # اطلاعات ترافیک را هم اضافه می‌کنیم
                        traffic_info = self.get_client_traffic_by_id(client_id)
                        if traffic_info:
                            client.update(traffic_info)
                        return client
        
        logger.warning(f"Client with ID {client_id} not found")
        return None
    
    
    