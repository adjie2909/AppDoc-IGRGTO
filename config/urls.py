from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.static import serve
from django.urls import re_path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('documents/', include('documents.urls')),
    path('', lambda request: redirect('documents:dashboard')),  # Langsung redirect ke dashboard dokumen
]
urlpatterns += [
    re_path(r'^(?P<path>documents/.*)$', serve, {'document_root': settings.BASE_DIR}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)