import os
import sys
from django.core.wsgi import get_wsgi_application

print("Current working directory:", os.getcwd(), file=sys.stderr)
print("Python path:", sys.path, file=sys.stderr)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yt_transcription.settings')
application = get_wsgi_application()
