#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Config Builder - ساخت کانفیگ‌ها مستقیماً از دیتای پنل
"""

import json
import base64
import logging
from urllib.parse import quote
from api_client.xui_api_client import XuiAPIClient
from api_client.alireza_api_client import AlirezaAPIClient

logger = logging.getLogger(__name__)

def get_api_client(server_info):
    """
    ساخت API client بر اساس نوع پنل
    """
    panel_type = server_info.get('panel_type', 'xui')
    
    if panel_type == 'alireza':
        return AlirezaAPIClient(
            panel_url=server_info['panel_url'],
            username=server_info['username'],
            password=server_info['password']
        )
    else:  # xui
        return XuiAPIClient(
            panel_url=server_info['panel_url'],
            username=server_info['username'],
            password=server_info['password']
        )

def build_vmess_config(client_info, inbound_info, server_info, brand_name="Alamor"):
    """
    ساخت کانفیگ VMess
    """
    try:
        # استخراج اطلاعات کلاینت
        client_id = client_info.get('id')
        client_email = client_info.get('email', '')
        client_name = client_info.get('name', f"{brand_name}-{client_email}")
        
        # استخراج اطلاعات inbound
        inbound_settings = json.loads(inbound_info.get('settings', '{}'))
        stream_settings = json.loads(inbound_info.get('streamSettings', '{}'))
        
        # ساخت VMess config
        vmess_config = {
            "v": "2",
            "ps": client_name,  # نام کانفیگ
            "add": server_info.get('subscription_base_url', '').split('//')[-1].split(':')[0].split('/')[0],  # آدرس سرور
            "port": inbound_info.get('port', 443),
            "id": client_id,  # UUID کلاینت
            "aid": "0",
            "net": stream_settings.get('network', 'tcp'),
            "type": stream_settings.get('headerType', 'none'),
            "host": "",
            "path": "",
            "tls": stream_settings.get('security', 'none')
        }
        
        # تنظیمات WebSocket
        if vmess_config['net'] == 'ws':
            ws_settings = stream_settings.get('wsSettings', {})
            vmess_config['host'] = ws_settings.get('host', '')
            vmess_config['path'] = ws_settings.get('path', '')
        
        # تنظیمات TLS
        if vmess_config['tls'] == 'tls':
            tls_settings = stream_settings.get('tlsSettings', {})
            vmess_config['sni'] = tls_settings.get('serverName', vmess_config['add'])
        
        # تبدیل به Base64
        config_json = json.dumps(vmess_config, separators=(',', ':'))
        encoded_config = base64.b64encode(config_json.encode()).decode()
        
        return f"vmess://{encoded_config}"
        
    except Exception as e:
        logger.error(f"Error building VMess config: {e}")
        return None

def build_vless_config(client_info, inbound_info, server_info, brand_name="Alamor"):
    """
    ساخت کانفیگ VLESS
    """
    try:
        # استخراج اطلاعات کلاینت
        client_id = client_info.get('id')
        client_email = client_info.get('email', '')
        client_name = client_info.get('name', f"{brand_name}-{client_email}")
        
        # استخراج اطلاعات inbound
        inbound_settings = json.loads(inbound_info.get('settings', '{}'))
        stream_settings = json.loads(inbound_info.get('streamSettings', '{}'))
        
        # آدرس سرور
        server_address = server_info.get('subscription_base_url', '').split('//')[-1].split(':')[0].split('/')[0]
        port = inbound_info.get('port', 443)
        
        # پارامترهای query
        params = {
            'encryption': 'none',
            'security': stream_settings.get('security', 'none'),
            'type': stream_settings.get('network', 'tcp')
        }
        
        # تنظیمات WebSocket
        if params['type'] == 'ws':
            ws_settings = stream_settings.get('wsSettings', {})
            params['path'] = ws_settings.get('path', '')
            params['host'] = ws_settings.get('host', '')
        
        # تنظیمات TLS
        if params['security'] == 'tls':
            tls_settings = stream_settings.get('tlsSettings', {})
            params['sni'] = tls_settings.get('serverName', server_address)
        
        # ساخت query string
        query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items() if v])
        
        # ساخت VLESS config
        vless_config = f"vless://{client_id}@{server_address}:{port}?{query_string}#{quote(client_name)}"
        
        return vless_config
        
    except Exception as e:
        logger.error(f"Error building VLESS config: {e}")
        return None

def build_trojan_config(client_info, inbound_info, server_info, brand_name="Alamor"):
    """
    ساخت کانفیگ Trojan
    """
    try:
        # استخراج اطلاعات کلاینت
        client_password = client_info.get('password', '')
        client_email = client_info.get('email', '')
        client_name = client_info.get('name', f"{brand_name}-{client_email}")
        
        # استخراج اطلاعات inbound
        stream_settings = json.loads(inbound_info.get('streamSettings', '{}'))
        
        # آدرس سرور
        server_address = server_info.get('subscription_base_url', '').split('//')[-1].split(':')[0].split('/')[0]
        port = inbound_info.get('port', 443)
        
        # پارامترهای query
        params = {
            'security': stream_settings.get('security', 'tls'),
            'type': stream_settings.get('network', 'tcp')
        }
        
        # تنظیمات TLS
        if params['security'] == 'tls':
            tls_settings = stream_settings.get('tlsSettings', {})
            params['sni'] = tls_settings.get('serverName', server_address)
        
        # ساخت query string
        query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items() if v])
        
        # ساخت Trojan config
        trojan_config = f"trojan://{client_password}@{server_address}:{port}?{query_string}#{quote(client_name)}"
        
        return trojan_config
        
    except Exception as e:
        logger.error(f"Error building Trojan config: {e}")
        return None

def build_config_from_panel(server_info, inbound_id, client_id, brand_name="Alamor"):
    """
    ساخت کانفیگ از دیتای پنل
    """
    try:
        logger.info(f"Building config for client {client_id} in inbound {inbound_id}")
        
        # ساخت API client
        api_client = get_api_client(server_info)
        if not api_client.check_login():
            logger.error(f"Failed to login to panel {server_info.get('name', 'Unknown')}")
            return None
        
        # دریافت اطلاعات inbound
        inbound_info = api_client.get_inbound(inbound_id)
        if not inbound_info:
            logger.error(f"Failed to get inbound {inbound_id}")
            return None
        
        # دریافت اطلاعات کلاینت
        client_info = api_client.get_client_info(client_id)
        if not client_info:
            logger.error(f"Failed to get client {client_id}")
            return None
        
        logger.info(f"Retrieved client info: {client_info.get('email', 'N/A')}")
        
        # تشخیص نوع پروتکل
        protocol = inbound_info.get('protocol', 'vmess')
        
        # ساخت کانفیگ بر اساس پروتکل
        if protocol == 'vmess':
            config = build_vmess_config(client_info, inbound_info, server_info, brand_name)
        elif protocol == 'vless':
            config = build_vless_config(client_info, inbound_info, server_info, brand_name)
        elif protocol == 'trojan':
            config = build_trojan_config(client_info, inbound_info, server_info, brand_name)
        else:
            logger.error(f"Unsupported protocol: {protocol}")
            return None
        
        if config:
            logger.info(f"Successfully built {protocol} config for client {client_id}")
            return {
                'protocol': protocol,
                'config': config,
                'client_email': client_info.get('email', ''),
                'client_name': client_info.get('name', ''),
                'inbound_id': inbound_id,
                'server_name': server_info.get('name', 'Unknown')
            }
        else:
            logger.error(f"Failed to build config for client {client_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error building config from panel: {e}")
        return None

def test_config_builder(server_info, inbound_id, client_id):
    """
    تست تابع ساخت کانفیگ
    """
    try:
        logger.info(f"Testing config builder for server: {server_info.get('name', 'Unknown')}")
        
        result = build_config_from_panel(server_info, inbound_id, client_id)
        
        if result:
            logger.info("✅ Config built successfully!")
            logger.info(f"Protocol: {result['protocol']}")
            logger.info(f"Client: {result['client_email']}")
            logger.info(f"Server: {result['server_name']}")
            logger.info(f"Config: {result['config'][:100]}...")
            return result
        else:
            logger.error("❌ Failed to build config")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error in test_config_builder: {e}")
        return None
