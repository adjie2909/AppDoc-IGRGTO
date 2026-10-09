from django import forms
from .models import Document


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ('judul_dokumen', 'file_dokumen')
        widgets = {
            'judul_dokumen': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contoh: Berita Acara Stock Opname Toko'
            }),
            'file_dokumen': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.docx'
            }),
        }