from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)
from .models import CustomUser, validate_ttd_size
from .utils import make_signature_transparent


class SignatureCleanMixin:
    def clean_ttd_digital(self):
        image = self.cleaned_data.get('ttd_digital')
        if (
            image
            and not getattr(image, '_signature_processed', False)
            and not getattr(image, '_committed', True)
        ):
            image = make_signature_transparent(image)
            image._signature_processed = True
        return image


class CustomUserCreationForm(SignatureCleanMixin, UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('userid', 'nama_pengguna', 'email', 'userlevel', 'ttd_digital')

    def clean_userid(self):
        userid = self.cleaned_data.get('userid', '')
        return userid.strip().upper() if userid else ''

    def save(self, commit=True):
        user = super().save(commit=False)
        user.userid = self.cleaned_data['userid'].strip().upper()
        user.nama_pengguna = self.cleaned_data['nama_pengguna']
        user.email = self.cleaned_data.get('email')
        user.userlevel = self.cleaned_data['userlevel']
        if 'ttd_digital' in self.cleaned_data:
            user.ttd_digital = self.cleaned_data['ttd_digital']
        if commit:
            user.save()
        return user


class CustomUserChangeForm(SignatureCleanMixin, UserChangeForm):
    password = None

    class Meta:
        model = CustomUser
        fields = ('userid', 'nama_pengguna', 'email', 'userlevel', 'ttd_digital', 'is_active', 'is_staff', 'is_superuser')

    def clean_userid(self):
        userid = self.cleaned_data.get('userid', '')
        return userid.strip().upper() if userid else ''


class UserRegisterForm(SignatureCleanMixin, forms.ModelForm):
    email = forms.EmailField(
        required=True,
        label='Alamat Email',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    divisi = forms.ChoiceField(
        required=True,
        choices=[('', '-- Pilih Divisi --')] + list(CustomUser.DIVISI_CHOICES),
        label='Divisi',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    ttd_digital = forms.ImageField(
        required=True,
        label='Tanda Tangan Digital',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/png, image/jpeg'}),
        validators=[validate_ttd_size],
        help_text='Latar kertas otomatis dibuat transparan (PNG/JPG, maks 2MB).'
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password_confirm = forms.CharField(
        label='Konfirmasi Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = CustomUser
        fields = ('userid', 'nama_pengguna', 'email', 'divisi', 'ttd_digital')
        widgets = {
            'userid': forms.TextInput(attrs={'class': 'form-control text-uppercase'}),
            'nama_pengguna': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama lengkap Anda'}),
        }

    def clean_userid(self):
        userid = self.cleaned_data.get('userid', '').strip().upper()
        if CustomUser.objects.filter(userid=userid).exists():
            raise forms.ValidationError('UserID ini sudah terdaftar.')
        return userid

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Email ini sudah digunakan oleh akun lain.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get('password')
        pwd_confirm = cleaned_data.get('password_confirm')
        if pwd and pwd_confirm and pwd != pwd_confirm:
            self.add_error('password_confirm', 'Password konfirmasi tidak cocok.')
        
        # Validasi divisi wajib dipilih
        divisi = cleaned_data.get('divisi')
        if not divisi:
            self.add_error('divisi', 'Harap pilih salah satu divisi.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.userlevel = 'staff'  # Otomatis staff untuk registrasi publik
        user.divisi = self.cleaned_data.get('divisi')  # Ambil dan tetapkan nilai divisi
        if commit:
            user.save()
        return user

class UploadSignatureForm(SignatureCleanMixin, forms.ModelForm):
    ttd_digital = forms.ImageField(
        required=True,
        label='Tanda Tangan Digital Baru',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/png, image/jpeg'}),
        validators=[validate_ttd_size],
    )

    class Meta:
        model = CustomUser
        fields = ('ttd_digital',)

# Form Login Kustom berbasis UserID
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='UserID',
        widget=forms.TextInput(attrs={'class': 'form-control text-uppercase'})
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean_username(self):
        return self.cleaned_data.get('username', '').strip().upper()


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
