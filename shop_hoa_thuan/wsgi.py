import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shop_hoa_thuan.settings")

application = get_wsgi_application()
