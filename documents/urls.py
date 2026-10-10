from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('upload/', views.upload_document_view, name='upload'),
    path('document/<int:doc_id>/preview/', views.document_preview_view, name='preview'),
    path('document/<int:doc_id>/file/', views.document_pdf_file_view, name='pdf_file'),
    path('document/<int:doc_id>/download/', views.download_document_view, name='download'),
    path('verify-password/', views.verify_password_view, name='verify_password'),
    path('document/<int:doc_id>/approve/', views.approve_document_view, name='approve'),
    path('document/<int:doc_id>/reject/', views.reject_document_view, name='reject'),
    path('my-signature/', views.my_signature_view, name='my_signature'),
    path('log/<int:log_id>/signature/', views.signature_log_view, name='log_signature'),
]