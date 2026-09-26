"""
WSGI config for edurev_swap project.
"""
import os
import threading
import time
import urllib.request
import logging
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edurev_swap.settings')
application = get_wsgi_application()

logger = logging.getLogger(__name__)

def _keep_alive_cron():
    """
    Background keep-alive worker.
    Pings the public Render service every 10 minutes to reset Render's
    15-minute inactivity timer, preventing the instance from sleeping.
    """
    # Wait 45 seconds for Gunicorn to bind and open port
    time.sleep(45)
    
    target_url = os.environ.get(
        'KEEP_ALIVE_URL',
        'https://django-project-edurev.onrender.com/login/'
    )
    logger.info(f"[KeepAlive] Cron started. Target: {target_url}")
    
    while True:
        try:
            req = urllib.request.Request(
                target_url,
                headers={'User-Agent': 'RenderKeepAliveCron/1.0'}
            )
            with urllib.request.urlopen(req, timeout=15) as res:
                logger.info(f"[KeepAlive] Ping successful! Status: {res.status}")
        except Exception as err:
            logger.warning(f"[KeepAlive] Ping encountered note: {err}")
        
        # Sleep for 10 minutes (600s), well under Render's 15-minute timeout
        time.sleep(600)

# Launch daemon thread on web server startup (does not run during manage.py tasks)
if os.environ.get('RENDER') or os.environ.get('ENABLE_KEEP_ALIVE', 'true').lower() == 'true':
    t = threading.Thread(target=_keep_alive_cron, daemon=True, name="RenderKeepAliveCron")
    t.start()
