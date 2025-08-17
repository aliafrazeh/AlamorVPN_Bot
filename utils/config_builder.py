#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Config Builder - ساخت کانفیگ‌ها مستقیماً از دیتای پنل
پشتیبانی کامل از تمام پروتکل‌ها و پارامترها
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

def detect_protocol(inbound_info):
    """
    تشخیص پروتکل از اطلاعات inbound
    """
    try:
        # بررسی فیلدهای مختلف برای تشخیص پروتکل
        protocol = inbound_info.get('protocol', '').lower()
        proxy_type = inbound_info.get('proxy_type', '').lower()
        proxyType = inbound_info.get('proxyType', '').lower()
        
        # لیست پروتکل‌های پشتیبانی شده
        supported_protocols = [
            'vless', 'vmess', 'trojan', 'shadowsocks', 'dokodemo-door',
            'tcp', 'httpupgrade', 'ws', 'grpc', 'mkcp', 'quic', 'http', 'h2'
        ]
        
        # تشخیص پروتکل اصلی
        detected_protocol = None
        
        # اولویت 1: فیلد protocol
        if protocol in supported_protocols:
            detected_protocol = protocol
        # اولویت 2: فیلد proxy_type
        elif proxy_type in supported_protocols:
            detected_protocol = proxy_type
        # اولویت 3: فیلد proxyType
        elif proxyType in supported_protocols:
            detected_protocol = proxyType
        
        # اگر پروتکل تشخیص داده نشد، پیش‌فرض VLESS
        if not detected_protocol:
            detected_protocol = 'vless'
            logger.warning(f"Protocol not detected, defaulting to VLESS")
        
        logger.info(f"Detected protocol: {detected_protocol}")
        return detected_protocol
        
    except Exception as e:
        logger.error(f"Error detecting protocol: {e}")
        return 'vless'  # پیش‌فرض

def extract_stream_parameters(stream_settings):
    """
    استخراج تمام پارامترهای stream settings
    """
    try:
        if isinstance(stream_settings, str):
            stream_settings = json.loads(stream_settings)
        
        params = {}
        
        # Network type
        params['network'] = stream_settings.get('network', 'tcp')
        
        # Security type
        params['security'] = stream_settings.get('security', 'none')
        
        # TLS Settings
        if params['security'] == 'tls':
            tls_settings = stream_settings.get('tlsSettings', {})
            params['tls'] = {
                'serverName': tls_settings.get('serverName', ''),
                'alpn': tls_settings.get('alpn', []),
                'fingerprint': tls_settings.get('settings', {}).get('fingerprint', ''),
                'echConfigList': tls_settings.get('settings', {}).get('echConfigList', ''),
                'allowInsecure': tls_settings.get('settings', {}).get('allowInsecure', False),
                'utls': tls_settings.get('settings', {}).get('utls', False),
                'externalProxy': tls_settings.get('externalProxy', False)
            }
        
        # Reality Settings
        elif params['security'] == 'reality':
            reality_settings = stream_settings.get('realitySettings', {})
            params['reality'] = {
                'dest': reality_settings.get('dest', ''),
                'fingerprint': reality_settings.get('settings', {}).get('fingerprint', ''),
                'publicKey': reality_settings.get('settings', {}).get('publicKey', ''),
                'shortIds': reality_settings.get('shortIds', []),
                'spiderX': reality_settings.get('spiderX', ''),
                'serverNames': reality_settings.get('serverNames', [])
            }
        
        # WebSocket Settings
        if params['network'] == 'ws':
            ws_settings = stream_settings.get('wsSettings', {})
            params['ws'] = {
                'path': ws_settings.get('path', ''),
                'host': ws_settings.get('headers', {}).get('Host', ''),
                'headers': ws_settings.get('headers', {})
            }
        
        # HTTP/HTTPUpgrade Settings
        elif params['network'] in ['http', 'httpupgrade', 'h2']:
            http_settings = stream_settings.get('httpSettings', {})
            params['http'] = {
                'path': http_settings.get('path', ''),
                'host': http_settings.get('host', ''),
                'method': http_settings.get('method', 'GET')
            }
        
        # gRPC Settings
        elif params['network'] == 'grpc':
            grpc_settings = stream_settings.get('grpcSettings', {})
            params['grpc'] = {
                'serviceName': grpc_settings.get('serviceName', ''),
                'multiMode': grpc_settings.get('multiMode', False)
            }
        
        # mKCP Settings
        elif params['network'] == 'mkcp':
            mkcp_settings = stream_settings.get('kcpSettings', {})
            params['mkcp'] = {
                'mtu': mkcp_settings.get('mtu', 1350),
                'tti': mkcp_settings.get('tti', 50),
                'uplinkCapacity': mkcp_settings.get('uplinkCapacity', 5),
                'downlinkCapacity': mkcp_settings.get('downlinkCapacity', 20),
                'congestion': mkcp_settings.get('congestion', False),
                'readBufferSize': mkcp_settings.get('readBufferSize', 2),
                'writeBufferSize': mkcp_settings.get('writeBufferSize', 2),
                'header': mkcp_settings.get('header', {})
            }
        
        # QUIC Settings
        elif params['network'] == 'quic':
            quic_settings = stream_settings.get('quicSettings', {})
            params['quic'] = {
                'security': quic_settings.get('security', 'none'),
                'key': quic_settings.get('key', ''),
                'header': quic_settings.get('header', {})
            }
        
        # TCP Settings
        elif params['network'] == 'tcp':
            tcp_settings = stream_settings.get('tcpSettings', {})
            params['tcp'] = {
                'header': tcp_settings.get('header', {})
            }
        
        logger.info(f"Extracted stream parameters: {json.dumps(params, indent=2)}")
        return params
        
    except Exception as e:
        logger.error(f"Error extracting stream parameters: {e}")
        return {}

def build_vmess_config(client_info, inbound_info, server_info, brand_name="Alamor"):
    """
    ساخت کانفیگ VMess با پشتیبانی کامل از تمام تنظیمات
    """
    try:
        # استخراج اطلاعات کلاینت
        client_id = client_info.get('id')
        client_email = client_info.get('email', '')
        client_name = client_info.get('name', f"{brand_name}-{client_email}")
        
        # تشخیص پروتکل
        protocol = detect_protocol(inbound_info)
        if protocol != 'vmess':
            logger.warning(f"Protocol {protocol} detected but building VMess config")
        
        # استخراج stream parameters
        stream_settings_str = inbound_info.get('streamSettings', '{}')
        stream_params = extract_stream_parameters(stream_settings_str)
        
        # آدرس سرور
        server_ip = server_info.get('ip', '')
        if not server_ip:
            server_ip = server_info.get('subscription_base_url', '').split('//')[-1].split(':')[0].split('/')[0]
        
        # ساخت VMess config
        vmess_config = {
            "v": "2",
            "ps": client_name,
            "add": server_ip,
            "port": inbound_info.get('port', 443),
            "id": client_id,
            "aid": "0",
            "net": stream_params.get('network', 'tcp'),
            "type": "none",
            "host": "",
            "path": "",
            "tls": stream_params.get('security', 'none')
        }
        
        # تنظیمات WebSocket
        if vmess_config['net'] == 'ws':
            ws_params = stream_params.get('ws', {})
            vmess_config['host'] = ws_params.get('host', '')
            vmess_config['path'] = ws_params.get('path', '')
        
        # تنظیمات HTTP/HTTPUpgrade
        elif vmess_config['net'] in ['http', 'httpupgrade', 'h2']:
            http_params = stream_params.get('http', {})
            vmess_config['host'] = http_params.get('host', '')
            vmess_config['path'] = http_params.get('path', '')
        
        # تنظیمات gRPC
        elif vmess_config['net'] == 'grpc':
            grpc_params = stream_params.get('grpc', {})
            vmess_config['path'] = grpc_params.get('serviceName', '')
        
        # تنظیمات mKCP
        elif vmess_config['net'] == 'mkcp':
            mkcp_params = stream_params.get('mkcp', {})
            vmess_config['type'] = mkcp_params.get('header', {}).get('type', 'none')
        
        # تنظیمات QUIC
        elif vmess_config['net'] == 'quic':
            quic_params = stream_params.get('quic', {})
            vmess_config['type'] = quic_params.get('header', {}).get('type', 'none')
        
        # تنظیمات TLS
        if vmess_config['tls'] == 'tls':
            tls_params = stream_params.get('tls', {})
            vmess_config['sni'] = tls_params.get('serverName', server_ip)
            
            if tls_params.get('alpn'):
                vmess_config['alpn'] = ','.join(tls_params['alpn'])
            
            if tls_params.get('fingerprint'):
                vmess_config['fp'] = tls_params['fingerprint']
            
            if tls_params.get('echConfigList'):
                vmess_config['ech'] = tls_params['echConfigList']
        
        # تنظیمات Reality
        elif vmess_config['tls'] == 'reality':
            reality_params = stream_params.get('reality', {})
            vmess_config['sni'] = reality_params.get('dest', '').split(':')[0] if ':' in reality_params.get('dest', '') else reality_params.get('dest', '')
            vmess_config['fp'] = reality_params.get('fingerprint', '')
            vmess_config['pbk'] = reality_params.get('publicKey', '')
            vmess_config['sid'] = reality_params.get('shortIds', [''])[0] if reality_params.get('shortIds') else ''
            vmess_config['spx'] = reality_params.get('spiderX', '')
        
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
    ساخت کانفیگ VLESS با پشتیبانی کامل از تمام تنظیمات
    """
    try:
        # استخراج اطلاعات کلاینت
        client_id = client_info.get('id')
        client_email = client_info.get('email', '')
        client_name = client_info.get('name', f"{brand_name}-{client_email}")
        
        # تشخیص پروتکل
        protocol = detect_protocol(inbound_info)
        if protocol != 'vless':
            logger.warning(f"Protocol {protocol} detected but building VLESS config")
        
        # استخراج stream parameters
        stream_settings_str = inbound_info.get('streamSettings', '{}')
        stream_params = extract_stream_parameters(stream_settings_str)
        
        logger.info(f"=== VLESS Config Debug ===")
        logger.info(f"Client ID: {client_id}")
        logger.info(f"Client ID type: {type(client_id)}")
        logger.info(f"Client Email: {client_email}")
        logger.info(f"Stream Parameters: {json.dumps(stream_params, indent=2)}")
        
        # آدرس سرور
        server_ip = server_info.get('ip', '')
        if not server_ip:
            server_ip = server_info.get('subscription_base_url', '').split('//')[-1].split(':')[0].split('/')[0]
        
        port = inbound_info.get('port', 443)
        
        logger.info(f"Server IP: {server_ip}")
        logger.info(f"Port: {port}")
        
        # ساخت VLESS URL
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
        security = stream_params.get('security', 'none')
        params.append(f"security={security}")
        
        # اضافه کردن network type
        network = stream_params.get('network', 'tcp')
        params.append(f"type={network}")
        
        logger.info(f"Security: {security}")
        logger.info(f"Network: {network}")
        
        # تنظیمات TLS
        if security == 'tls':
            tls_params = stream_params.get('tls', {})
            logger.info(f"TLS Parameters: {json.dumps(tls_params, indent=2)}")
            
            # SNI
            sni = tls_params.get('serverName', '')
            if sni:
                params.append(f"sni={sni}")
                logger.info(f"Added SNI: {sni}")
            
            # ALPN
            alpn = tls_params.get('alpn', [])
            if alpn:
                alpn_str = ','.join(alpn)
                params.append(f"alpn={alpn_str}")
                logger.info(f"Added ALPN: {alpn_str}")
            
            # Fingerprint
            fp = tls_params.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
                logger.info(f"Added fingerprint: {fp}")
            
            # ECH
            ech_config_list = tls_params.get('echConfigList', '')
            if ech_config_list:
                params.append(f"ech={ech_config_list}")
                logger.info(f"Added ECH config list")
            
            # Allow Insecure
            allow_insecure = tls_params.get('allowInsecure', False)
            if allow_insecure:
                params.append("allowInsecure=true")
                logger.info(f"Added allowInsecure: true")
            
            # uTLS
            utls = tls_params.get('utls', False)
            if utls:
                params.append("utls=true")
                logger.info(f"Added uTLS: true")
        
        # تنظیمات Reality
        elif security == 'reality':
            reality_params = stream_params.get('reality', {})
            logger.info(f"Reality Parameters: {json.dumps(reality_params, indent=2)}")
            
            # Dest (target)
            dest = reality_params.get('dest', '')
            if dest and ':' in dest:
                sni = dest.split(':')[0]
                params.append(f"sni={sni}")
                logger.info(f"Added SNI from dest: {sni}")
            
            # Fingerprint
            fp = reality_params.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
                logger.info(f"Added fingerprint: {fp}")
            
            # Public Key
            pbk = reality_params.get('publicKey', '')
            if pbk:
                params.append(f"pbk={pbk}")
                logger.info(f"Added public key: {pbk}")
            
            # Short ID
            short_ids = reality_params.get('shortIds', [])
            if short_ids:
                params.append(f"sid={short_ids[0]}")
                logger.info(f"Added short ID: {short_ids[0]}")
            
            # SpiderX
            spx = reality_params.get('spiderX', '')
            if spx:
                params.append(f"spx={spx}")
                logger.info(f"Added SpiderX: {spx}")
        
        # تنظیمات WebSocket
        if network == 'ws':
            ws_params = stream_params.get('ws', {})
            path = ws_params.get('path', '')
            if path:
                params.append(f"path={path}")
            
            host = ws_params.get('host', '')
            if host:
                params.append(f"host={host}")
        
        # تنظیمات HTTP/HTTPUpgrade
        elif network in ['http', 'httpupgrade', 'h2']:
            http_params = stream_params.get('http', {})
            path = http_params.get('path', '')
            if path:
                params.append(f"path={path}")
            
            host = http_params.get('host', '')
            if host:
                params.append(f"host={host}")
        
        # تنظیمات gRPC
        elif network == 'grpc':
            grpc_params = stream_params.get('grpc', {})
            service_name = grpc_params.get('serviceName', '')
            if service_name:
                params.append(f"serviceName={service_name}")
        
        # تنظیمات mKCP
        elif network == 'mkcp':
            mkcp_params = stream_params.get('mkcp', {})
            # اضافه کردن پارامترهای mKCP اگر نیاز باشه
            pass
        
        # تنظیمات QUIC
        elif network == 'quic':
            quic_params = stream_params.get('quic', {})
            # اضافه کردن پارامترهای QUIC اگر نیاز باشه
            pass
        
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
        
        # تشخیص پروتکل
        protocol = detect_protocol(inbound_info)
        if protocol != 'trojan':
            logger.warning(f"Protocol {protocol} detected but building Trojan config")
        
        # استخراج stream parameters
        stream_settings_str = inbound_info.get('streamSettings', '{}')
        stream_params = extract_stream_parameters(stream_settings_str)
        
        # آدرس سرور
        server_ip = server_info.get('ip', '')
        if not server_ip:
            server_ip = server_info.get('subscription_base_url', '').split('//')[-1].split(':')[0].split('/')[0]
        
        port = inbound_info.get('port', 443)
        
        # ساخت Trojan URL
        base_url = f"trojan://{client_password}@{server_ip}:{port}"
        
        # پارامترهای query
        params = []
        
        # اضافه کردن security
        security = stream_params.get('security', 'tls')
        params.append(f"security={security}")
        
        # اضافه کردن network type
        network = stream_params.get('network', 'tcp')
        params.append(f"type={network}")
        
        # تنظیمات TLS
        if security == 'tls':
            tls_params = stream_params.get('tls', {})
            
            # SNI
            sni = tls_params.get('serverName', '')
            if sni:
                params.append(f"sni={sni}")
            
            # ALPN
            alpn = tls_params.get('alpn', [])
            if alpn:
                alpn_str = ','.join(alpn)
                params.append(f"alpn={alpn_str}")
            
            # Fingerprint
            fp = tls_params.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
            
            # ECH
            ech_config_list = tls_params.get('echConfigList', '')
            if ech_config_list:
                params.append(f"ech={ech_config_list}")
            
            # Allow Insecure
            allow_insecure = tls_params.get('allowInsecure', False)
            if allow_insecure:
                params.append("allowInsecure=true")
            
            # uTLS
            utls = tls_params.get('utls', False)
            if utls:
                params.append("utls=true")
        
        # تنظیمات Reality
        elif security == 'reality':
            reality_params = stream_params.get('reality', {})
            
            # Dest (target)
            dest = reality_params.get('dest', '')
            if dest and ':' in dest:
                sni = dest.split(':')[0]
                params.append(f"sni={sni}")
            
            # Fingerprint
            fp = reality_params.get('fingerprint', '')
            if fp:
                params.append(f"fp={fp}")
            
            # Public Key
            pbk = reality_params.get('publicKey', '')
            if pbk:
                params.append(f"pbk={pbk}")
            
            # Short ID
            short_ids = reality_params.get('shortIds', [])
            if short_ids:
                params.append(f"sid={short_ids[0]}")
            
            # SpiderX
            spx = reality_params.get('spiderX', '')
            if spx:
                params.append(f"spx={spx}")
        
        # تنظیمات WebSocket
        if network == 'ws':
            ws_params = stream_params.get('ws', {})
            path = ws_params.get('path', '')
            if path:
                params.append(f"path={path}")
            
            host = ws_params.get('host', '')
            if host:
                params.append(f"host={host}")
        
        # تنظیمات HTTP/HTTPUpgrade
        elif network in ['http', 'httpupgrade', 'h2']:
            http_params = stream_params.get('http', {})
            path = http_params.get('path', '')
            if path:
                params.append(f"path={path}")
            
            host = http_params.get('host', '')
            if host:
                params.append(f"host={host}")
        
        # تنظیمات gRPC
        elif network == 'grpc':
            grpc_params = stream_params.get('grpc', {})
            service_name = grpc_params.get('serviceName', '')
            if service_name:
                params.append(f"serviceName={service_name}")
        
        # تنظیمات mKCP
        elif network == 'mkcp':
            mkcp_params = stream_params.get('mkcp', {})
            # اضافه کردن پارامترهای mKCP اگر نیاز باشه
            pass
        
        # تنظیمات QUIC
        elif network == 'quic':
            quic_params = stream_params.get('quic', {})
            # اضافه کردن پارامترهای QUIC اگر نیاز باشه
            pass
        
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
    ساخت کانفیگ از دیتای پنل با تشخیص خودکار پروتکل
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
        
        # تشخیص نوع پروتکل
        protocol = detect_protocol(inbound_info)
        logger.info(f"Detected protocol: {protocol}")
        logger.info(f"Inbound info keys: {list(inbound_info.keys())}")
        logger.info(f"Full inbound info: {inbound_info}")
        
        # ساخت کانفیگ بر اساس پروتکل
        config = None
        
        if protocol == 'vless':
            logger.info("Building VLESS config...")
            config = build_vless_config(client_info, inbound_info, server_info, brand_name)
            if config:
                logger.info("✅ VLESS config built successfully!")
            else:
                logger.error("❌ Failed to build VLESS config")
        
        elif protocol == 'vmess':
            logger.info("Building VMess config...")
            config = build_vmess_config(client_info, inbound_info, server_info, brand_name)
            if config:
                logger.info("✅ VMess config built successfully!")
            else:
                logger.error("❌ Failed to build VMess config")
        
        elif protocol == 'trojan':
            logger.info("Building Trojan config...")
            config = build_trojan_config(client_info, inbound_info, server_info, brand_name)
            if config:
                logger.info("✅ Trojan config built successfully!")
            else:
                logger.error("❌ Failed to build Trojan config")
        
        else:
            logger.error(f"Unsupported protocol: {protocol}")
            return None
        
        if not config:
            logger.error(f"Failed to build {protocol} config")
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
