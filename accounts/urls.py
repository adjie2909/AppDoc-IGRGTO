from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_redirect_view, name='dashboard_redirect'),
    path('my-signature/', views.my_signature_view, name='my_signature'),
    path('upload-signature/', views.upload_signature_view, name='upload_signature'),
]