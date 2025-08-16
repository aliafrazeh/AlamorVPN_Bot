# api_client/xui_api_client.py

import requests
import logging
import json

# Disable SSL warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)

class XuiAPIClient:
    def __init__(self, panel_url, username, password):
        self.base_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
        self.is_logged_in = False
        self.api_base_path = "/panel/api/inbounds" # مسیر استاندارد سنایی
        logger.info(f"XuiAPIClient initialized for {self.base_url}")

    def _request(self, method, path, **kwargs):
        """A central and robust method for sending all requests."""
        if not path.startswith('/'):
            path = '/' + path
        
        # Auto-login if not already logged in
        if not self.is_logged_in and path != '/login':
            if not self.login():
                return None # Stop if login fails

        url = self.base_url + path
        try:
            response = self.session.request(method, url, verify=False, timeout=20, **kwargs)

            # Re-login attempt on authentication failure
            if response.status_code in [401, 403]:
                logger.warning("Authentication error. Re-logging in...")
                if not self.login(): return None
                response = self.session.request(method, url, verify=False, timeout=20, **kwargs)

            response.raise_for_status() # Check for other HTTP errors (like 500)
            if not response.text:
                return None
            
            return response.json()

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from {path}. Response: {response.text[:200]}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {path}: {e}")
            return None

    def login(self):
        """ --- FINAL VERSION: Smart cookie detection --- """
        self.is_logged_in = False
        payload = {'username': self.username, 'password': self.password}
        response_data = self._request('post', '/login', data=payload)
        
        if response_data and response_data.get('success'):
            # --- THE FIX IS HERE ---
            # We no longer care about the cookie's name. If any cookie is set, it's a success.
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
        """Checks if the session is still valid."""
        if self.is_logged_in:
            return True
        return self.login()

    def add_client(self, data):
        """Adds a new client to an inbound."""
        response_data = self._request('post', '/panel/api/inbounds/addClient', json=data)
        if response_data and response_data.get('success'):
            logger.info(f"Client added successfully to inbound {data.get('id', 'N/A')}.")
            return True
        else:
            error_msg = response_data.get('msg', 'Unknown') if response_data else "No response"
            logger.warning(f"Failed to add client to inbound {data.get('id', 'N/A')}: {error_msg}")
            return False
    def list_inbounds(self):
        if not self.check_login(): 
            logger.error("Not logged in to X-UI. Cannot list inbounds.")
            return []
        
        endpoint = "/panel/api/inbounds/list"
        response = self._request("GET", endpoint) 
        
        if response and response.get('success'):
            logger.info("Successfully retrieved inbound list.")
            return response.get('obj', [])
        else:
            logger.error(f"Failed to get inbound list. Response: {response}")
            return []

    def get_inbound(self, inbound_id):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot get inbound details.")
            return None
        
        endpoint = f"/panel/api/inbounds/get/{inbound_id}"
        response = self._request("GET", endpoint) 
        
        if response and response.get('success'):
            logger.info(f"Successfully retrieved inbound details for ID {inbound_id}.")
            return response.get('obj')
        else:
            logger.error(f"Failed to get inbound details for ID {inbound_id}. Response: {response}")
            return None
            
    def add_inbound(self, data):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot add inbound.")
            return None
        
        endpoint = "/panel/api/inbounds/add"
        response = self._request("POST", endpoint, data=data) 
        
        if response and response.get('success'):
            logger.info(f"Inbound added: {response.get('obj')}")
            return response.get("obj")
        else:
            logger.warning(f"Failed to add inbound: {response}")
            return None

    def delete_inbound(self, inbound_id):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot delete inbound.")
            return False
        
        endpoint = f"/panel/api/inbounds/del/{inbound_id}"
        response = self._request("POST", endpoint) 
        
        if response and response.get('success'):
            logger.info(f"Inbound {inbound_id} deleted successfully.")
            return True
        else:
            logger.warning(f"Failed to delete inbound {inbound_id}: {response}")
            return False

    def update_inbound(self, inbound_id, data):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot update inbound.")
            return False
        
        endpoint = f"/panel/api/inbounds/update/{inbound_id}"
        response = self._request("POST", endpoint, data=data) 
        
        if response and response.get('success'):
            logger.info(f"Inbound {inbound_id} updated successfully.")
            return True
        else:
            logger.warning(f"Failed to update inbound {inbound_id}: {response}")
            return False

    

    def delete_client(self, inbound_id, client_id):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot delete client.")
            return False
        
        endpoint = f"/panel/api/inbounds/{inbound_id}/delClient/{client_id}"
        response = self._request("POST", endpoint) 
        
        if response and response.get('success'):
            logger.info(f"Client {client_id} deleted from inbound ID {inbound_id}.")
            return True
        else:
            logger.warning(f"Failed to delete client {client_id} from inbound ID {inbound_id}: {response}")
            return False

    def update_client(self, client_id, data):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot update client.")
            return False
        
        endpoint = f"/panel/api/inbounds/updateClient/{client_id}"
        response = self._request("POST", endpoint, data=data) 
        
        if response and response.get('success'):
            logger.info(f"Client {client_id} updated successfully.")
            return True
        else:
            logger.warning(f"Failed to update client {client_id}: {response}")
            return False

    def reset_client_traffic(self, id, email):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot reset client traffic.")
            return False
        url = f"{self.panel_url}/panel/api/inbounds/{id}/resetClientTraffic/{email}"
        try:
            res = self.session.post(url, verify=False, timeout=10)
            res.raise_for_status()
            response_json = res.json()
            if response_json.get('success'):
                logger.info(f"Client traffic reset for {email} in inbound {id}.")
                return True
            else:
                logger.warning(f"Failed to reset client traffic for {email} in inbound {id}: {response_json.get('msg', res.text)}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error resetting client traffic for {email} from {url}: {e}")
            return False

    def reset_all_traffics(self):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot reset all traffics.")
            return False
        url = f"{self.panel_url}/panel/api/inbounds/resetAllTraffics"
        try:
            res = self.session.post(url, verify=False, timeout=10)
            res.raise_for_status()
            response_json = res.json()
            if response_json.get('success'):
                logger.info("All traffics reset successfully.")
                return True
            else:
                logger.warning(f"Failed to reset all traffics: {response_json.get('msg', res.text)}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error resetting all traffics from {url}: {e}")
            return False

    def reset_all_client_traffics(self, id):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot reset all client traffics.")
            return False
        url = f"{self.panel_url}/panel/api/inbounds/resetAllClientTraffics/{id}"
        try:
            res = self.session.post(url, verify=False, timeout=10)
            res.raise_for_status()
            response_json = res.json()
            if response_json.get('success'):
                logger.info(f"All client traffics reset for inbound {id}.")
                return True
            else:
                logger.warning(f"Failed to reset all client traffics for inbound {id}: {response_json.get('msg', res.text)}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error resetting all client traffics for {id} from {url}: {e}")
            return False

    def del_depleted_clients(self, id):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot delete depleted clients.")
            return False
        url = f"{self.panel_url}/panel/api/inbounds/delDepletedClients/{id}"
        try:
            res = self.session.post(url, verify=False, timeout=10)
            res.raise_for_status()
            response_json = res.json()
            if response_json.get('success'):
                logger.info(f"Depleted clients deleted for inbound {id}.")
                return True
            else:
                logger.warning(f"Failed to delete depleted clients for inbound {id}: {response_json.get('msg', res.text)}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting depleted clients for {id} from {url}: {e}")
            return False

    def client_ips(self, email):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot get client IPs.")
            return None
        url = f"{self.panel_url}/panel/api/inbounds/clientIps/{email}"
        try:
            res = self.session.post(url, verify=False, timeout=10)
            res.raise_for_status()
            response_json = res.json()
            if response_json.get('success'):
                logger.info(f"Client IPs retrieved for {email}.")
                return response_json.get("obj")
            else:
                logger.warning(f"Failed to get client IPs for {email}: {response_json.get('msg', res.text)}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting client IPs for {email} from {url}: {e}")
            return None

    def clear_client_ips(self, email):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot clear client IPs.")
            return False
        url = f"{self.panel_url}/panel/api/inbounds/clearClientIps/{email}"
        try:
            res = self.session.post(url, verify=False, timeout=10)
            res.raise_for_status()
            response_json = res.json()
            if response_json.get('success'):
                logger.info(f"Client IPs cleared for {email}.")
                return True
            else:
                logger.warning(f"Failed to clear client IPs for {email}: {response_json.get('msg', res.text)}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error clearing client IPs for {email} from {url}: {e}")
            return False

    def get_online_users(self):
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot get online users.")
            return None
        url = f"{self.panel_url}/panel/api/inbounds/onlines"
        try:
            res = self.session.post(url, verify=False, timeout=10)
            res.raise_for_status()
            response_json = res.json()
            if response_json.get('success'):
                logger.info("Successfully retrieved online users.")
                return response_json.get("obj")
            else:
                logger.warning(f"Failed to get online users: {response_json.get('msg', res.text)}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting online users from {url}: {e}")
            return None

    def get_client_traffic_by_id(self, client_id):
        """Gets traffic statistics for a specific client by ID."""
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot get client traffic.")
            return None
        
        endpoint = f"/panel/api/inbounds/getClientTrafficsById/{client_id}"
        response = self._request("GET", endpoint)
        
        if response and response.get('success'):
            return response.get('obj', {})
        else:
            logger.warning(f"Failed to get traffic for client ID {client_id}")
            return None

    def get_client_info(self, client_id):
        """Gets detailed information for a specific client by ID."""
        if not self.check_login():
            logger.error("Not logged in to X-UI. Cannot get client info.")
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
        
        
        
        
        
        
# api_client/xui_api_client.py
# ... (کل کد کلاس XuiAPIClient و بقیه توابع) ...

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from config import XUI_PANEL_URL, XUI_USERNAME, XUI_PASSWORD

    print("\n--- Testing XuiAPIClient Login ---")
    test_client = XuiAPIClient(
        panel_url=XUI_PANEL_URL,
        username=XUI_USERNAME,
        password=XUI_PASSWORD
    )

    try:
        # ارسال درخواست لاگین به صورت دستی و چاپ جزئیات پاسخ
        login_url = f"{test_client.panel_url}/login"
        login_data = {"username": test_client.username, "password": test_client.password}
        print(f"Attempting POST request to: {login_url}")
        print(f"Payload: {login_data}")

        response = test_client.session.post(login_url, json=login_data, verify=False, timeout=10)
        response.raise_for_status() # برای برانگیختن خطا در صورت کد وضعیت 4xx/5xx

        print("\n--- Raw Response Details ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response URL: {response.url}")
        print(f"Response Headers:")
        for k, v in response.headers.items():
            print(f"  {k}: {v}")
        print(f"Response Cookies:")
        for k, v in response.cookies.items():
            print(f"  {k}: {v}")
        print(f"Response Body (JSON):")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
        except json.JSONDecodeError:
            print("  (Not a valid JSON response)")
            print(response.text)

        print("\n--- Login Attempt Result ---")
        if response.status_code == 200 and response_json.get("success"):
            session_cookie_found = 'session' in test_client.session.cookies
            obj_token_found = response_json.get('obj') is not None

            print(f"API success field: {response_json.get('success')}")
            print(f"Is 'session' cookie found in session.cookies? {session_cookie_found}")
            print(f"Is 'obj' token found in response JSON? {obj_token_found}")

            if session_cookie_found or obj_token_found:
                print("Login successful! Session cookie or obj token detected.")
            else:
                print("Login successful (API returned success) but no expected 'session' cookie or 'obj' token found.")
                print("Please inspect the 'Response Headers' and 'Response Body (JSON)' above for the actual session/token key.")
        else:
            print(f"Login failed. API returned unsuccessful. Message: {response_json.get('msg', response.text)}")

    except requests.exceptions.RequestException as e:
        print(f"\n--- Login Request Error ---")
        print(f"An error occurred during login request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error Response Status: {e.response.status_code}")
            print(f"Error Response Text: {e.response.text}")
    except Exception as e:
        print(f"\n--- Unexpected Error ---")
        print(f"An unexpected error occurred: {e}")