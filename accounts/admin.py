from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserChangeForm


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = ('userid', 'nama_pengguna', 'userlevel', 'is_active', 'is_staff')
    list_filter = ('userlevel', 'is_active', 'is_staff')
    search_fields = ('userid', 'nama_pengguna')
    ordering = ('userid',)

    # Tampilan saat edit user yang sudah ada
    fieldsets = (
        (None, {'fields': ('userid',)}),
        ('Informasi Pribadi', {'fields': ('nama_pengguna', 'userlevel', 'ttd_digital')}),
        ('Hak Akses', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    # Tampilan form saat pertama kali klik "Tambah Pengguna" (+ Add)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('userid', 'nama_pengguna', 'userlevel', 'ttd_digital', 'password1', 'password2'),
        }),
    )