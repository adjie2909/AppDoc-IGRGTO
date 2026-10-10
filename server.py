# server.py
import os
import sys
from django.conf import settings
from whitenoise import WhiteNoise
from waitress import serve
from config.wsgi import application

HOST = '0.0.0.0'
PORT = 8000
THREADS = 6

app = WhiteNoise(
    application, root=str(settings.STATIC_ROOT), prefix=settings.STATIC_URL
)

if os.path.exists(settings.MEDIA_ROOT):
  app.add_files(str(settings.MEDIA_ROOT), prefix=settings.MEDIA_URL)

if __name__ == '__main__':
  print('=' * 60)
  print('          MEMULAI SERVER APPDOC IGRGTO (WAITRESS)          ')
  print('=' * 60)
  print(f' * Server aktif di: http://{HOST}:{PORT}')
  print(f' * Threads berjalan: {THREADS}')
  print(' * Tekan CTRL + C untuk mematikan server.')
  print('=' * 60)

  try:
    serve(
        app,  # <-- SUDAH DIGANTI MENJADI 'app'
        host=HOST,
        port=PORT,
        threads=THREADS,
        channel_timeout=60,
        cleanup_interval=30,
    )
  except KeyboardInterrupt:
    print('\nServer berhasil dihentikan.')
    sys.exit(0)