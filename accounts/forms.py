from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.contrib.auth import authenticate
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
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


class CustomUserChangeForm(UserChangeForm):
    password = None

    class Meta:
        model = CustomUser
        fields = ('userid', 'nama_pengguna', 'email', 'userlevel', 'ttd_digital', 'is_active', 'is_staff', 'is_superuser')

    def clean_userid(self):
        userid = self.cleaned_data.get('userid', '')
        return userid.strip().upper() if userid else ''


# Form Registrasi Publik
class UserRegisterForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        label='Alamat Email',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    ttd_digital = forms.ImageField(
        required=True,
        label='Tanda Tangan Digital',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/png, image/jpeg'}),
        help_text='Wajib mengunggah file tanda tangan format PNG/JPG (Maks 2MB).'
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
        fields = ('userid', 'nama_pengguna', 'email', 'userlevel', 'divisi', 'ttd_digital')
        widgets = {
            'userid': forms.TextInput(attrs={'class': 'form-control text-uppercase'}),
            'nama_pengguna': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama lengkap Anda'}),
            'userlevel': forms.Select(attrs={'class': 'form-select'}),
            'divisi': forms.Select(attrs={'class': 'form-select', 'id': 'id_divisi'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['divisi'].required = False
        self.fields['divisi'].choices = [('', '-- Pilih Divisi --')] + list(CustomUser.DIVISI_CHOICES)

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

        # Validasi wajib divisi untuk level tertentu
        userlevel = cleaned_data.get('userlevel')
        divisi = cleaned_data.get('divisi')
        divisi_required_levels = ['staff', 'supervisor', 'junior manajer']

        if userlevel in divisi_required_levels:
            if not divisi:
                self.add_error('divisi', 'Divisi wajib dipilih untuk level Staff, Supervisor, dan Store Junior Manajer.')
        else:
            # Jika SAM atau Store Manager, kosongkan divisi
            cleaned_data['divisi'] = None

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.divisi = self.cleaned_data.get('divisi')
        if commit:
            user.save()
        return user

class UploadSignatureForm(forms.ModelForm):
    ttd_digital = forms.ImageField(
        required=True,
        label='Tanda Tangan Digital Baru',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/png, image/jpeg'})
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