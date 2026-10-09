from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('upload/', views.upload_document_view, name='upload'),
    path('document/<int:doc_id>/preview/', views.document_preview_view, name='preview'),
    path('verify-password/', views.verify_password_view, name='verify_password'),
    path('document/<int:doc_id>/approve/', views.approve_document_view, name='approve'),
    path('document/<int:doc_id>/reject/', views.reject_document_view, name='reject'),
]