from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.contrib.auth import authenticate
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('userid', 'nama_pengguna', 'userlevel', 'ttd_digital')

    def clean_userid(self):
        userid = self.cleaned_data.get('userid', '')
        return userid.strip().upper() if userid else ''

    def save(self, commit=True):
        user = super().save(commit=False)
        user.userid = self.cleaned_data['userid'].strip().upper()
        user.nama_pengguna = self.cleaned_data['nama_pengguna']
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
        fields = ('userid', 'nama_pengguna', 'userlevel', 'ttd_digital', 'is_active', 'is_staff', 'is_superuser')

    def clean_userid(self):
        userid = self.cleaned_data.get('userid', '')
        return userid.strip().upper() if userid else ''


# Form Registrasi Publik
class UserRegisterForm(forms.ModelForm):
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
        fields = ('userid', 'nama_pengguna', 'userlevel', 'ttd_digital')
        widgets = {
            'userid': forms.TextInput(attrs={'class': 'form-control text-uppercase'}),
            'nama_pengguna': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama lengkap Anda'}),
            'userlevel': forms.Select(attrs={'class': 'form-select'}),
            'ttd_digital': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/png, image/jpeg'}),
        }

    def clean_userid(self):
        userid = self.cleaned_data.get('userid', '').strip().upper()
        if CustomUser.objects.filter(userid=userid).exists():
            raise forms.ValidationError('UserID ini sudah terdaftar.')
        return userid

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get('password')
        pwd_confirm = cleaned_data.get('password_confirm')

        if pwd and pwd_confirm and pwd != pwd_confirm:
            self.add_error('password_confirm', 'Password konfirmasi tidak cocok.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


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