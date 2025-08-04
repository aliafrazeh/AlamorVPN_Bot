# api_client/alireza_api_client.py

import requests
import logging
import json

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)

class AlirezaAPIClient:
    """
    Corrected API client for Alireza-x-ui panels, using the exact HTTP methods
    from the official documentation.
    """
    def __init__(self, panel_url, username, password):
        self.base_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
        self.is_logged_in = False
        self.api_base_path = "/xui/API/inbounds"
        logger.info(f"AlirezaAPIClient initialized for {self.base_url}")

    def _request(self, method, path, **kwargs):
        if not path.startswith('/'):
            path = '/' + path
        
        if not self.is_logged_in and path != '/login':
            if not self.login():
                return None

        url = self.base_url + path
        try:
            response = self.session.request(method, url, verify=False, timeout=20, **kwargs)
            if response.status_code in [401, 403]:
                if not self.login(): return None
                response = self.session.request(method, url, verify=False, timeout=20, **kwargs)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Request failed for {path}: {e}")
            return None

    def login(self):
        self.is_logged_in = False
        # --- CORRECTED: Using 'data' for a POST request as per documentation ---
        payload = {'username': self.username, 'password': self.password}
        response_data = self._request('post', '/login', data=payload)
        
        if response_data and response_data.get('success'):
            if self.session.cookies:
                self.is_logged_in = True
                logger.info(f"Login successful to {self.base_url}.")
                return True
        
        logger.error(f"Login failed for {self.base_url}.")
        return False

    def check_login(self):
        if self.is_logged_in:
            return True
        return self.login()

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
        
    def add_client(self, data):
        """ --- CORRECTED: Uses POST method as per documentation --- """
        full_path = self.api_base_path + "/addClient/"
        response_data = self._request('post', full_path, json=data)
        
        if response_data and response_data.get('success'):
            return True
        
        error_msg = response_data.get('msg', 'Unknown error') if response_data else "No response"
        logger.error(f"Failed to add client. Reason: {error_msg}")
        return False