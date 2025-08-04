# api_client/alireza_api_client.py

import requests
import logging
import json

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)

class AlirezaAPIClient:
    """
    کلاینت API نهایی و اصلاح شده برای پنل‌های Alireza-x-ui.
    این نسخه مشکل دریافت لیست اینباندها را به صورت قطعی حل می‌کند.
    """
    def __init__(self, panel_url, username, password):
        self.base_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
        self.is_logged_in = False
        # مسیر پایه API برای این پنل
        self.api_base_path = "/xui/API/inbounds" # مسیر صحیح بر اساس داکیومنت
        logger.info(f"AlirezaAPIClient initialized for {self.base_url}")

    def _request(self, method, path, **kwargs):
        # این تابع مرکزی بدون تغییر باقی می‌ماند
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
        # تابع لاگین هوشمند بدون تغییر باقی می‌ماند
        self.is_logged_in = False
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
        --- FIX FINAL ---
        لیست تمام اینباندها را با متد و مسیر صحیح دریافت می‌کند.
        """
        # مسیر کامل شبیه به پنل سنایی است
        full_path = self.api_base_path + "/list"
        
        # --- THE FIX IS HERE ---
        # این پنل نیز مانند سنایی از متد POST برای لیست کردن استفاده می‌کند
        response_data = self._request('post', full_path)
        
        if response_data and response_data.get('success'):
            return response_data.get('obj', [])
        
        logger.error(f"Failed to get inbound list from Alireza panel. Response: {response_data}")
        return []
        
    def add_client(self, data):
        # این تابع صحیح است و بدون تغییر باقی می‌ماند
        full_path = self.api_base_path + "/addClient/"
        response_data = self._request('post', full_path, json=data)
        
        if response_data and response_data.get('success'):
            return True
        
        error_msg = response_data.get('msg', 'Unknown error') if response_data else "No response"
        logger.error(f"Failed to add client. Reason: {error_msg}")
        return False