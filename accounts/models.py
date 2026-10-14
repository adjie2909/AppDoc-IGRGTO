import re
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


def validate_ttd_size(image):
    """Memastikan file gambar tanda tangan tidak melebihi 2MB."""
    max_size_bytes = 2 * 1024 * 1024  # 2MB
    if image.size > max_size_bytes:
        raise ValidationError('Ukuran gambar tanda tangan maksimal 2MB.')


class CustomUserManager(BaseUserManager):
    def create_user(self, userid, nama_pengguna, email=None, password=None, **extra_fields):
        if not userid:
            raise ValueError('UserID harus diisi.')
        if not nama_pengguna:
            raise ValueError('Nama pengguna harus diisi.')
        
        userid = userid.strip().upper()
        email = self.normalize_email(email) if email else None
        
        user = self.model(
            userid=userid, 
            nama_pengguna=nama_pengguna, 
            email=email, 
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, userid, nama_pengguna, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('userlevel', 'store manager')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser harus memiliki is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser harus memiliki is_superuser=True.')

        return self.create_user(userid, nama_pengguna, email=email, password=password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    USERLEVEL_CHOICES = (
        ('staff', 'Staff'),
        ('supervisor', 'Supervisor'),
        ('junior manajer', 'Store Junior Manajer'),
        ('store administration manager', 'Store Administration Manager'),
        ('store manager', 'Store Manager'),
    )

    DIVISI_CHOICES = (
        ('food', 'Food'),
        ('non food', 'Non Food'),
        ('perishable', 'Perishable'),
        ('logistik 1', 'Logistik 1'),
        ('logistik 2', 'Logistik 2'),
        ('member service', 'Member Service'),
        ('back office', 'Back Office'),
    )

   
    userid_validator = RegexValidator(
        regex=r'^[A-Za-z0-9]{3}$',
        message='UserID harus terdiri dari tepat 3 karakter alfanumerik (huruf/angka).'
    )

    userid = models.CharField(
        max_length=3,
        primary_key=True,
        unique=True,
        validators=[userid_validator],
        help_text='3 karakter alfanumerik (Contoh: A01, ADJ, ST1). Disimpan dalam huruf besar.'
    )
    nama_pengguna = models.CharField(max_length=150, verbose_name='Nama Pengguna')

    email = models.EmailField(
        max_length=254, 
        unique=True, 
        null=True, 
        blank=True, 
        verbose_name='Alamat Email'
    )

    userlevel = models.CharField(
        max_length=35,
        choices=USERLEVEL_CHOICES,
        default='staff',
        verbose_name='Level User'
    )

    divisi = models.CharField(
        max_length=30,
        choices=DIVISI_CHOICES,
        null=True,
        blank=True,
        verbose_name='Divisi'
    )

    ttd_digital = models.ImageField(
        upload_to='signatures/',
        null=True,
        blank=True,
        validators=[validate_ttd_size],
        verbose_name='Tanda Tangan Digital (PNG/JPG Max 2MB)'
    )

    # Field wajib untuk integrasi auth Django
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'userid'
    REQUIRED_FIELDS = ['nama_pengguna','email']

    class Meta:
        verbose_name = 'Pengguna'
        verbose_name_plural = 'Daftar Pengguna'

    def clean(self):
        super().clean()
        if self.userid:
            self.userid = self.userid.strip().upper()

    def save(self, *args, **kwargs):
        if self.userid:
            self.userid = self.userid.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.userid} - {self.nama_pengguna} ({self.get_userlevel_display()})"