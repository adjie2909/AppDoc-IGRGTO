import os
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


def validate_file_extension(value):
    """Hanya mengizinkan file berformat PDF atau DOCX."""
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.pdf', '.docx']
    if ext not in valid_extensions:
        raise ValidationError('Format file tidak didukung. Harap unggah file .pdf atau .docx.')


class Document(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('waiting_supervisor', 'Menunggu Supervisor'),
        ('waiting_junior_manager', 'Menunggu Junior Manajer'),
        ('waiting_sam', 'Menunggu Store Administration Manager'),
        ('waiting_store_manager', 'Menunggu Store Manager'),
        ('approved', 'Selesai / Approved'),
        ('rejected', 'Ditolak / Rejected'),
    )

    judul_dokumen = models.CharField(max_length=255, verbose_name='Judul Dokumen')
    file_dokumen = models.FileField(
        upload_to='documents/%Y/%m/',
        validators=[validate_file_extension],
        verbose_name='File Dokumen (PDF/DOCX)'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_documents',
        verbose_name='Diupload Oleh'
    )
    status = models.CharField(
        max_length=35,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Status Dokumen'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Tanggal Upload')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Terakhir Diperbarui')

    class Meta:
        verbose_name = 'Dokumen'
        verbose_name_plural = 'Daftar Dokumen'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.judul_dokumen} [{self.get_status_display()}]"


class ApprovalLog(models.Model):
    ACTION_CHOICES = (
        ('submitted', 'Diajukan'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    )

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='approval_logs',
        verbose_name='Dokumen'
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='approval_actions',
        verbose_name='Petugas/Approver'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Tindakan')
    comment = models.TextField(blank=True, null=True, verbose_name='Komentar / Alasan Penolakan')
    signature_snapshot = models.ImageField(
        upload_to='signatures_log/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Snapshot Tanda Tangan'
    )
    sig_x = models.FloatField(blank=True, null=True, verbose_name='Koordinat X')
    sig_y = models.FloatField(blank=True, null=True, verbose_name='Koordinat Y')
    sig_scale = models.CharField(max_length=50, blank=True, null=True, verbose_name='Skala/Dimensi TTD')
    sig_page = models.IntegerField(blank=True, null=True, verbose_name='Halaman Dokumen')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Waktu Eksekusi')

    
    date_text = models.CharField(max_length=50, blank=True, null=True)
    date_x = models.FloatField(blank=True, null=True)
    date_y = models.FloatField(blank=True, null=True)
    date_scale = models.CharField(max_length=50, blank=True, null=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log Persetujuan'
        verbose_name_plural = 'Daftar Log Persetujuan'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.document.judul_dokumen} - {self.action} oleh {self.approver.nama_pengguna}"