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
    ساخت کانفیگ VMess با پشتیبانی کامل از تمام تنظیمات
    """
    try:
        # استخراج اطلاعات کلاینت
        client_id = client_info.get('id')
        client_email = client_info.get('email', '')
        client_name = client_info.get('name', f"{brand_name}-{client_email}")
        
        # استخراج اطلاعات inbound
        stream_settings_str = inbound_info.get('streamSettings', '{}')
        try:
            stream_settings = json.loads(stream_settings_str) if isinstance(stream_settings_str, str) else stream_settings_str
        except:
            stream_settings = {}
        
        # آدرس سرور - استفاده از IP سرور
        server_ip = server_info.get('ip', '')
        if not server_ip:
            # Fallback به subscription_base_url
            server_ip = server_info.get('subscription_base_url', '').split('//')[-1].split(':')[0].split('/')[0]
        
        # ساخت VMess config
        vmess_config = {
            "v": "2",
            "ps": client_name,  # نام کانفیگ
            "add": server_ip,  # آدرس سرور
            "port": inbound_info.get('port', 443),
            "id": client_id,  # UUID کلاینت
            "aid": "0",
            "net": stream_settings.get('network', 'tcp'),
            "type": "none",
            "host": "",
            "path": "",
            "tls": stream_settings.get('security', 'none')
        }
        
        # تنظیمات WebSocket
        if vmess_config['net'] == 'ws':
            ws_settings = stream_settings.get('wsSettings', {})
            vmess_config['host'] = ws_settings.get('host', '')
            vmess_config['path'] = ws_settings.get('path', '')
            
            # تنظیمات headers
            headers = ws_settings.get('headers', {})
            if headers:
                vmess_config['host'] = headers.get('Host', vmess_config['host'])
        
        # تنظیمات HTTP/2
        elif vmess_config['net'] == 'h2':
            h2_settings = stream_settings.get('httpSettings', {})
            vmess_config['host'] = h2_settings.get('host', '')
            vmess_config['path'] = h2_settings.get('path', '')
        
        # تنظیمات gRPC
        elif vmess_config['net'] == 'grpc':
            grpc_settings = stream_settings.get('grpcSettings', {})
            vmess_config['path'] = grpc_settings.get('serviceName', '')
        
        # تنظیمات TLS
        if vmess_config['tls'] == 'tls':
            tls_settings = stream_settings.get('tlsSettings', {})
            vmess_config['sni'] = tls_settings.get('serverName', server_ip)
            vmess_config['fp'] = tls_settings.get('fingerprint', '')
        
        # تنظیمات Reality
        elif vmess_config['tls'] == 'reality':
            reality_settings = stream_settings.get('realitySettings', {})
            vmess_config['sni'] = reality_settings.get('dest', '').split(':')[0] if ':' in reality_settings.get('dest', '') else reality_settings.get('dest', '')
            vmess_config['fp'] = reality_settings.get('settings', {}).get('fingerprint', '')
            vmess_config['pbk'] = reality_settings.get('settings', {}).get('publicKey', '')
            vmess_config['sid'] = reality_settings.get('shortIds', [''])[0] if reality_settings.get('shortIds') else ''
        
        # حذف فیلدهای خالی
        vmess_config = {k: v for k, v in vmess_config.items() if v != "" and v is not None}
        
        # تبدیل به Base64
        config_json = json.dumps(vmess_config, separators=(',', ':'))
        encoded_config = base64.b64encode(config_json.encode()).decode()
        
        final_url = f"vmess://{encoded_config}"
        logger.info(f"Built VMess config for {client_email}")
        logger.info(f"Config length: {len(final_url)} characters")
        logger.info(f"Full config URL: {final_url}")
        return final_url
        
    except Exception as e:
        logger.error(f"Error building VMess config: {e}")
        return None

def build_vless_config(client_info, inbound_info, server_info, brand_name="Alamor"):
    """
    ساخت کانفیگ VLESS با پشتیبانی کامل از Reality و سایر تنظیمات
    """
    try:
        # استخراج اطلاعات کلاینت
        client_id = client_info.get('id')
        client_email = client_info.get('email', '')
        client_name = client_info.get('name', f"{brand_name}-{client_email}")
        
        # استخراج اطلاعات inbound
        stream_settings_str = inbound_info.get('streamSettings', '{}')
        try:
            stream_settings = json.loads(stream_settings_str) if isinstance(stream_settings_str, str) else stream_settings_str
        except:
            stream_settings = {}
        
        logger.info(f"=== VLESS Config Debug ===")
        logger.info(f"Client ID: {client_id}")
        logger.info(f"Client ID type: {type(client_id)}")
        logger.info(f"Client Email: {client_email}")
        logger.info(f"Stream Settings: {json.dumps(stream_settings, indent=2)}")
        
        # آدرس سرور - استفاده از IP سرور
        server_ip = server_info.get('ip', '')
        if not server_ip:
            # Fallback به subscription_base_url
            server_ip = server_info.get('subscription_base_url', '').split('//')[-1].split(':')[0].split('/')[0]
        
        port = inbound_info.get('port', 443)
        
        logger.info(f"Server IP: {server_ip}")
        logger.info(f"Port: {port}")
        
        # ساخت VLESS URL با پارامترهای صحیح
        base_url = f"vless://{client_id}@{server_ip}:{port}"
        
        logger.info(f"=== URL Construction Debug ===")
        logger.info(f"Client ID for URL: {client_id}")
        logger.info(f"Client ID type for URL: {type(client_id)}")
        logger.info(f"Server IP: {server_ip}")
        logger.info(f"Port: {port}")
        logger.info(f"Base URL: {base_url}")
        
        # پارامترهای query
        params = []
        params.append("encryption=none")
        
        # اضافه کردن security
        security = stream_settings.get('security', 'none')
        params.append(f"security={security}")
        
        # اضافه کردن network type
        network = stream_settings.get('network', 'tcp')
        params.append(f"type={network}")
        
        logger.info(f"Security: {security}")
        logger.info(f"Network: {network}")
        
        # تنظیمات TLS
        if security == 'tls':
            tls_settings = stream_settings.get('tlsSettings', {})
            sni = tls_settings.get('serverName', '')
            if sni:
                params.append(f"sni={sni}")
            fp = tls_settings.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
            logger.info(f"TLS Settings: {json.dumps(tls_settings, indent=2)}")
        
        # تنظیمات Reality
        if security == 'reality':
            reality_settings = stream_settings.get('realitySettings', {})
            logger.info(f"Reality Settings: {json.dumps(reality_settings, indent=2)}")
            
            dest = reality_settings.get('dest', '')
            if dest and ':' in dest:
                sni = dest.split(':')[0]
                params.append(f"sni={sni}")
                logger.info(f"Added SNI from dest: {sni}")
            
            settings = reality_settings.get('settings', {})
            fp = settings.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
                logger.info(f"Added fingerprint: {fp}")
            
            pbk = settings.get('publicKey', '')
            if pbk:
                params.append(f"pbk={pbk}")
                logger.info(f"Added public key: {pbk}")
            
            short_ids = reality_settings.get('shortIds', [])
            if short_ids:
                params.append(f"sid={short_ids[0]}")
                logger.info(f"Added short ID: {short_ids[0]}")
        
        # تنظیمات WebSocket
        if network == 'ws':
            ws_settings = stream_settings.get('wsSettings', {})
            path = ws_settings.get('path', '')
            if path:
                params.append(f"path={path}")
            
            headers = ws_settings.get('headers', {})
            host = headers.get('Host', '')
            if host:
                params.append(f"host={host}")
        
        # تنظیمات gRPC
        elif network == 'grpc':
            grpc_settings = stream_settings.get('grpcSettings', {})
            service_name = grpc_settings.get('serviceName', '')
            if service_name:
                params.append(f"serviceName={service_name}")
        
        # اضافه کردن flow برای XTLS
        flow = client_info.get('flow', '')
        if flow:
            params.append(f"flow={flow}")
        
        logger.info(f"Final params: {params}")
        
        # ساخت URL نهایی
        if params:
            base_url += "?" + "&".join(params)
        
        # اضافه کردن fragment (نام کلاینت)
        final_url = f"{base_url}#{quote(client_name)}"
        
        logger.info(f"Final VLESS URL: {final_url}")
        logger.info(f"Built VLESS config for {client_email}")
        logger.info(f"Config length: {len(final_url)} characters")
        logger.info(f"Full config URL: {final_url}")
        return final_url
        
    except Exception as e:
        logger.error(f"Error building VLESS config: {e}")
        return None

def build_trojan_config(client_info, inbound_info, server_info, brand_name="Alamor"):
    """
    ساخت کانفیگ Trojan با پشتیبانی کامل از تمام تنظیمات
    """
    try:
        # استخراج اطلاعات کلاینت
        client_password = client_info.get('password', '')
        client_email = client_info.get('email', '')
        client_name = client_info.get('name', f"{brand_name}-{client_email}")
        
        # استخراج اطلاعات inbound
        stream_settings_str = inbound_info.get('streamSettings', '{}')
        try:
            stream_settings = json.loads(stream_settings_str) if isinstance(stream_settings_str, str) else stream_settings_str
        except:
            stream_settings = {}
        
        # آدرس سرور - استفاده از IP سرور
        server_ip = server_info.get('ip', '')
        if not server_ip:
            # Fallback به subscription_base_url
            server_ip = server_info.get('subscription_base_url', '').split('//')[-1].split(':')[0].split('/')[0]
        
        port = inbound_info.get('port', 443)
        
        # ساخت Trojan URL با پارامترهای صحیح
        base_url = f"trojan://{client_password}@{server_ip}:{port}"
        
        # پارامترهای query
        params = []
        
        # اضافه کردن security
        security = stream_settings.get('security', 'tls')
        params.append(f"security={security}")
        
        # اضافه کردن network type
        network = stream_settings.get('network', 'tcp')
        params.append(f"type={network}")
        
        # تنظیمات TLS
        if security == 'tls':
            tls_settings = stream_settings.get('tlsSettings', {})
            sni = tls_settings.get('serverName', '')
            if sni:
                params.append(f"sni={sni}")
            fp = tls_settings.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
        
        # تنظیمات Reality
        if security == 'reality':
            reality_settings = stream_settings.get('realitySettings', {})
            dest = reality_settings.get('dest', '')
            if dest and ':' in dest:
                sni = dest.split(':')[0]
                params.append(f"sni={sni}")
            
            settings = reality_settings.get('settings', {})
            fp = settings.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
            
            pbk = settings.get('publicKey', '')
            if pbk:
                params.append(f"pbk={pbk}")
            
            short_ids = reality_settings.get('shortIds', [])
            if short_ids:
                params.append(f"sid={short_ids[0]}")
        
        # تنظیمات WebSocket
        if network == 'ws':
            ws_settings = stream_settings.get('wsSettings', {})
            path = ws_settings.get('path', '')
            if path:
                params.append(f"path={path}")
            
            headers = ws_settings.get('headers', {})
            host = headers.get('Host', '')
            if host:
                params.append(f"host={host}")
        
        # تنظیمات gRPC
        elif network == 'grpc':
            grpc_settings = stream_settings.get('grpcSettings', {})
            service_name = grpc_settings.get('serviceName', '')
            if service_name:
                params.append(f"serviceName={service_name}")
        
        # اضافه کردن flow برای XTLS
        flow = client_info.get('flow', '')
        if flow:
            params.append(f"flow={flow}")
        
        # ساخت URL نهایی
        if params:
            base_url += "?" + "&".join(params)
        
        # اضافه کردن fragment (نام کلاینت)
        final_url = f"{base_url}#{quote(client_name)}"
        
        logger.info(f"Built Trojan config for {client_email}")
        logger.info(f"Config length: {len(final_url)} characters")
        logger.info(f"Full config URL: {final_url}")
        return final_url
        
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
            logger.error(f"Client ID type: {type(client_id)}")
            logger.error(f"Client ID value: {client_id}")
            return None
        
        logger.info(f"Retrieved client info: {client_info.get('email', 'N/A')}")
        logger.info(f"Client info keys: {list(client_info.keys())}")
        logger.info(f"Client ID from panel: {client_info.get('id', 'N/A')}")
        logger.info(f"Client ID type from panel: {type(client_info.get('id', 'N/A'))}")
        logger.info(f"Full client info: {json.dumps(client_info, indent=2)}")
        
        # تشخیص نوع پروتکل - همیشه VLESS
        protocol = 'vless'
        logger.info(f"Protocol set to: {protocol}")
        logger.info(f"Inbound info keys: {list(inbound_info.keys())}")
        logger.info(f"Full inbound info: {inbound_info}")
        
        # ساخت کانفیگ بر اساس پروتکل
        protocol_lower = protocol.lower() if protocol else 'vless'
        logger.info(f"Processing protocol: {protocol_lower}")
        
        config = None
        
        # فقط VLESS بساز
        if protocol_lower in ['vless', 'vless+ws', 'vless+tls', 'vless+reality']:
            logger.info("Building VLESS config...")
            config = build_vless_config(client_info, inbound_info, server_info, brand_name)
            if config:
                logger.info("✅ VLESS config built successfully!")
                protocol = 'vless'
            else:
                logger.error("❌ Failed to build VLESS config")
        else:
            logger.error(f"Unsupported protocol: {protocol}. Only VLESS is supported.")
            return None
        
        if not config:
            logger.error(f"Failed to build VLESS config for protocol: {protocol}")
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
            logger.info(f"Config length: {len(result['config'])} characters")
            logger.info(f"Full config: {result['config']}")
            return result
        else:
            logger.error("❌ Failed to build config")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error in test_config_builder: {e}")
        return None
