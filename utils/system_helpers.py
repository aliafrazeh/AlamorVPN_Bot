# utils/system_helpers.py
import subprocess
import logging
import os

logger = logging.getLogger(__name__)

def run_shell_command(command):
    """یک دستور شل را اجرا کرده و موفقیت یا شکست آن را برمی‌گرداند."""
    try:
        # ما از sudo استفاده می‌کنیم چون nginx و certbot نیاز به دسترسی root دارند
        full_command = ['sudo'] + command
        result = subprocess.run(full_command, check=True, capture_output=True, text=True)
        logger.info(f"Command successful: {' '.join(command)}\nOutput: {result.stdout}")
        return True, ""
    except subprocess.CalledProcessError as e:
        error_message = f"Command failed: {' '.join(command)}\nError: {e.stderr}"
        logger.error(error_message)
        return False, e.stderr

def setup_domain_nginx_and_ssl(domain_name, admin_email):
    """
    یک دامنه جدید را در Nginx تنظیم کرده و برای آن گواهی SSL از Certbot دریافت می‌کند.
    """
    nginx_config_path = f"/etc/nginx/sites-available/{domain_name}"
    nginx_enabled_path = f"/etc/nginx/sites-enabled/{domain_name}"

    # مرحله ۱: ساخت کانفیگ موقت Nginx برای اعتبارسنجی Certbot
    temp_nginx_config = f"""
server {{
    listen 80;
    server_name {domain_name};
    root /var/www/html;
    index index.html index.htm;
}}
"""
    try:
        with open(f"/tmp/{domain_name}.conf", "w") as f:
            f.write(temp_nginx_config)
        run_shell_command(['mv', f'/tmp/{domain_name}.conf', nginx_config_path])
        
        if not os.path.exists(nginx_enabled_path):
             run_shell_command(['ln', '-s', nginx_config_path, nginx_enabled_path])

        # ریلود کردن Nginx برای اعمال کانفیگ موقت
        success, _ = run_shell_command(['systemctl', 'reload', 'nginx'])
        if not success:
            raise Exception("Failed to reload Nginx with temporary config.")

        # مرحله ۲: اجرای Certbot برای دریافت گواهی SSL
        certbot_command = [
            'certbot', '--nginx', '-d', domain_name,
            '--email', admin_email, '--agree-tos', '--non-interactive', '--redirect'
        ]
        success, error = run_shell_command(certbot_command)
        if not success:
            raise Exception(f"Certbot failed. Check DNS A record for {domain_name}. Error: {error}")

        # مرحله ۳: ساخت کانفیگ نهایی Nginx برای Proxy Pass
        # Certbot خودش کانفیگ را به روز می‌کند، ما فقط باید مطمئن شویم Proxy Pass اضافه شده
        # برای سادگی، ما کانفیگ را بازنویسی می‌کنیم تا مطمئن شویم درست است
        final_nginx_config = f"""
server {{
    listen 80;
    server_name {domain_name};
    return 301 https://$host$request_uri;
}}
server {{
    listen 443 ssl http2;
    server_name {domain_name};

    ssl_certificate /etc/letsencrypt/live/{domain_name}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain_name}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {{
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
        with open(f"/tmp/{domain_name}.conf", "w") as f:
            f.write(final_nginx_config)
        run_shell_command(['mv', f'/tmp/{domain_name}.conf', nginx_config_path])

        # مرحله ۴: ریلود نهایی Nginx
        success, _ = run_shell_command(['systemctl', 'reload', 'nginx'])
        if not success:
            raise Exception("Failed to reload Nginx with final config.")
            
        return True, "Domain setup and SSL certificate obtained successfully."

    except Exception as e:
        # پاک‌سازی در صورت بروز خطا
        run_shell_command(['rm', '-f', nginx_config_path])
        run_shell_command(['rm', '-f', nginx_enabled_path])
        run_shell_command(['systemctl', 'reload', 'nginx'])
        return False, str(e)