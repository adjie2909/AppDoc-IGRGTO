from django import forms
from .models import Document


# Hirarki level tanda tangan yang tersedia
APPROVAL_LEVEL_CHOICES = (
    ('supervisor', 'Supervisor'),
    ('junior manajer', 'Junior Manajer'),
    ('store administration manager', 'Store Administration Manager'),
    ('store manager', 'Store Manager'),
)

class DocumentUploadForm(forms.ModelForm):
    approval_targets = forms.MultipleChoiceField(
        choices=APPROVAL_LEVEL_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        label='Pilih Pejabat yang Butuh Tanda Tangan',
        help_text='Centang level yang wajib tanda tangan. Level yang tidak dicentang akan otomatis dilewati.'
    )

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