from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from .forms import UserRegisterForm, LoginForm
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from .forms import UserRegisterForm, LoginForm, UploadSignatureForm


def register_view(request):
    """Menangani pendaftaran akun pengguna baru."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Akun {user.userid} berhasil dibuat! Silakan masuk.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Pendaftaran gagal. Periksa kembali isian formulir Anda.')
    else:
        form = UserRegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Menangani autentikasi masuk pengguna."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Selamat datang kembali, {user.nama_pengguna}!')
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('accounts:dashboard_redirect')
        else:
            messages.error(request, 'UserID atau Password salah.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Menangani sesi keluar pengguna."""
    logout(request)
    messages.info(request, 'Anda telah keluar dari sistem.')
    return redirect('accounts:login')


def dashboard_redirect_view(request):
    return redirect('documents:dashboard')

@login_required(login_url='accounts:login')
def my_signature_view(request):
  """Mengalirkan gambar tanda tangan milik user yang sedang login."""
  user = request.user
  if not user.ttd_digital:
    raise Http404('Pengguna belum memiliki tanda tangan digital.')

  # Cek keberadaan file fisik di storage
  try:
    return FileResponse(user.ttd_digital.open('rb'))
  except FileNotFoundError:
    raise Http404('Berkas tanda tangan tidak ditemukan di server.')

@login_required(login_url='accounts:login')
def upload_signature_view(request):
    """View wajib untuk user yang belum memiliki tanda tangan digital."""
    if request.user.ttd_digital:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        form = UploadSignatureForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tanda tangan digital berhasil diunggah! Anda sekarang dapat mengakses dashboard.')
            return redirect('accounts:dashboard_redirect')
        else:
            messages.error(request, 'Gagal mengunggah berkas tanda tangan. Periksa kembali format dan ukurannya.')
    else:
        form = UploadSignatureForm(instance=request.user)

    return render(request, 'accounts/upload_signature.html', {'form': form})