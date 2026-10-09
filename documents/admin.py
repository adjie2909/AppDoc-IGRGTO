from django.contrib import admin
from .models import Document, ApprovalLog


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('judul_dokumen', 'uploaded_by', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('judul_dokumen', 'uploaded_by__nama_pengguna', 'uploaded_by__userid')


@admin.register(ApprovalLog)
class ApprovalLogAdmin(admin.ModelAdmin):
    list_display = ('document', 'approver', 'action', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('document__judul_dokumen', 'approver__nama_pengguna')