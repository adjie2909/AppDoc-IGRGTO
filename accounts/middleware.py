from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone


class SessionIdleTimeoutMiddleware:
    '''Logout pengguna yang tidak aktif lebih dari batas waktu sesi.'''

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = timezone.now().timestamp()
            last_activity = request.session.get('last_activity')
            timeout = getattr(settings, 'SESSION_IDLE_TIMEOUT', 30 * 60)

            if last_activity and now - last_activity > timeout:
                logout(request)
                messages.warning(
                    request,
                    'Silakan login kembali.',
                    extra_tags='popup',
                )
                return redirect('accounts:login')

            request.session['last_activity'] = now

        return self.get_response(request)


class RequireSignatureMiddleware:
    """
    Mencegat setiap akses dari pengguna terautentikasi yang belum mengunggah TTD.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            # Rute yang tidak dicegat agar tidak terjadi loop redirect
            exempt_urls = [
                reverse('accounts:upload_signature'),
                reverse('accounts:logout'),
            ]

            # Cek apakah user sudah punya TTD
            has_ttd = bool(request.user.ttd_digital)
            path = request.path

            if not has_ttd and path not in exempt_urls and not path.startswith('/static/') and not path.startswith('/media/'):
                return redirect('accounts:upload_signature')

        return self.get_response(request)
