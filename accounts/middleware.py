from django.shortcuts import redirect
from django.urls import reverse

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