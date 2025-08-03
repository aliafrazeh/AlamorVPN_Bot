# api_client/alireza_api_client.py

import requests
import logging
import json

# غیرفعال کردن هشدارهای مربوط به SSL
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)

class AlirezaAPIClient:
    """
    کلاینت API برای تعامل با پنل‌های Alireza-x-ui.
    این کلاس بر اساس مستندات رسمی گیت‌هاب نوشته شده است.
    """
    def __init__(self, panel_url, username, password):
        self.base_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
        self.is_logged_in = False
        # --- THE FIX IS HERE: Define the correct API base path ---
        self.api_base_path = "/xui/API/inbounds"
        logger.info(f"AlirezaAPIClient initialized for {self.base_url}")

    def _request(self, method, path, **kwargs):
        """یک متد مرکزی و قوی برای ارسال تمام درخواست‌ها."""
        if not path.startswith('/'):
            path = '/' + path
        
        # لاگین خودکار اگر لازم بود
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
        """لاگین به پنل."""
        self.is_logged_in = False
        payload = {'username': self.username, 'password': self.password}
        response_data = self._request('post', '/login', data=payload)
        
        if response_data and response_data.get('success'):
            self.is_logged_in = True
            return True
        else:
            logger.error(f"Login failed for {self.base_url}.")
            return False

    def check_login(self):
        """بررسی اعتبار لاگین."""
        if self.is_logged_in:
            return True
        return self.login()

    def add_client(self, data):
        """
        یک کلاینت جدید به یک اینباند مشخص اضافه می‌کند.
        مسیر API: /xui/API/inbounds/addClient/
        """
        logger.info(f"Adding client to inbound {data.get('id')}...")
        # --- THE FIX IS HERE: Use the correct API path ---
        full_path = self.api_base_path + "/addClient/"
        response_data = self._request('post', full_path, json=data)
        
        if response_data and response_data.get('success'):
            logger.info(f"Client added successfully.")
            return True
        
        error_msg = response_data.get('msg', 'Unknown error') if response_data else "No response"
        logger.error(f"Failed to add client. Reason: {error_msg}")
        return False

    def get_inbound(self, inbound_id):
        """
        اطلاعات یک اینباند خاص را دریافت می‌کند.
        مسیر API: /xui/API/inbounds/get/:id
        """
        full_path = f"{self.api_base_path}/get/{inbound_id}"
        response_data = self._request('get', full_path)
        if response_data and response_data.get('success'):
            return response_data.get('obj')
        return None

    def list_inbounds(self):
        """
        لیست تمام اینباندها را دریافت می‌کند.
        مسیر API: /xui/API/inbounds/
        """
        full_path = self.api_base_path + "/"
        response_data = self._request('get', full_path)
        if response_data and response_data.get('success'):
            return response_data.get('obj', [])
        return []