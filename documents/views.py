import json
import re
from datetime import datetime
from django.http import JsonResponse,FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from .models import Document, ApprovalLog
from .forms import DocumentUploadForm
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from .utils import generate_signed_pdf
from django.urls import reverse
from .utils import generate_signed_pdf, notify_next_approver, notify_document_creator

HIERARCHY_ORDER = [
    'supervisor',
    'junior manajer',
    'store administration manager',
    'store manager'
]

LEVEL_TO_STATUS = {
    'supervisor': 'waiting_supervisor',
    'junior manajer': 'waiting_junior_manager',
    'store administration manager': 'waiting_sam',
    'store manager': 'waiting_store_manager',
}

STATUS_TO_LEVEL = {v: k for k, v in LEVEL_TO_STATUS.items()}

def get_next_status(doc, current_userlevel):
    """
    Mencari level berikutnya hanya dari required_levels yang ada di dokumen.
    Jika tidak ada lagi level berikutnya, kembalikan 'approved'.
    """
    levels = doc.required_levels or []
    # Ambil index level sekarang dalam hierarki
    try:
        current_idx = HIERARCHY_ORDER.index(current_userlevel)
    except ValueError:
        current_idx = -1

    # Cari level berikutnya yang berada di atas level sekarang dan ada di required_levels
    for level in HIERARCHY_ORDER[current_idx + 1:]:
        if level in levels:
            return LEVEL_TO_STATUS[level]

    return 'approved'

@login_required(login_url='accounts:login')
def dashboard_view(request):
    user = request.user
    level = user.userlevel
    summary_levels = {
        'supervisor',
        'junior manajer',
        'store administration manager',
        'store manager',
    }
    queue_status_map = {
        'supervisor': 'waiting_supervisor',
        'junior manajer': 'waiting_junior_manager',
        'store administration manager': 'waiting_sam',
        'store manager': 'waiting_store_manager',
    }

    if level == 'staff':
        document_scope = Document.objects.filter(uploaded_by=user)
        active_queue = None
    elif level == 'supervisor':
        # SPV hanya melihat dokumen yang menargetkan divisinya.
        target_status = queue_status_map.get(level)
        document_scope = (
            Document.objects.filter(target_spv_divisi=user.divisi)
            if user.divisi
            else Document.objects.none()
        )
        active_queue = document_scope.filter(
            status=target_status,
        )
    elif level == 'junior manajer':
        # Store Junior Manajer hanya melihat dokumen yang menargetkan divisinya.
        target_status = queue_status_map.get(level)
        document_scope = (
            Document.objects.filter(target_jm_divisi=user.divisi)
            if user.divisi
            else Document.objects.none()
        )
        active_queue = document_scope.filter(
            status=target_status,
        )
    else:
        # SAM dan Store Manager memantau seluruh divisi.
        target_status = queue_status_map.get(level)
        document_scope = Document.objects.all()
        active_queue = document_scope.filter(status=target_status)

    show_summary = level in summary_levels
    summary = None
    if show_summary:
        summary = document_scope.aggregate(
            total=Count('pk'),
            approved=Count('pk', filter=Q(status='approved')),
            rejected=Count('pk', filter=Q(status='rejected')),
        )

    if level in {'supervisor', 'junior manajer'}:
        summary_scope_label = (
            f'Divisi {user.get_divisi_display()}'
            if user.divisi
            else 'Divisi belum diatur'
        )
    else:
        summary_scope_label = 'Semua divisi'

    doc_queryset = document_scope

    selected_status = request.GET.get('status', 'all')
    if selected_status and selected_status != 'all':
        doc_queryset = doc_queryset.filter(status=selected_status)

    doc_queryset = doc_queryset.order_by('-created_at')

    paginator = Paginator(doc_queryset, 5)
    page_number = request.GET.get('page')
    documents = paginator.get_page(page_number)
    upload_form = DocumentUploadForm()

    context = {
        'documents': documents,
        'active_queue': active_queue,
        'upload_form': upload_form,
        'user_level': level,
        'can_upload': level in ['staff', 'supervisor', 'junior manajer', 'store administration manager'],
        'today_date': datetime.now().strftime('%d/%m/%Y'),
        'selected_status': selected_status,
        'status_choices': Document.STATUS_CHOICES,
        'show_summary': show_summary,
        'summary': summary,
        'summary_scope_label': summary_scope_label,
    }
    return render(request, 'documents/dashboard.html', context)


@login_required(login_url='accounts:login')
def upload_document_view(request):
    """Mengunggah dokumen dan menyimpan tanda tangan pembuat secara bersamaan."""
    allowed_roles = ['staff', 'supervisor', 'junior manajer', 'store administration manager']
    if request.user.userlevel not in allowed_roles:
        messages.error(request, 'Anda tidak memiliki hak otorisasi untuk mengunggah Berita Acara.')
        return redirect('documents:dashboard')

    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                sig_x = float(request.POST.get('sig_x') or request.POST.get('creator_hidden_sig_x') or 0)
                sig_y = float(request.POST.get('sig_y') or request.POST.get('creator_hidden_sig_y') or 0)
                sig_page = int(request.POST.get('sig_page') or request.POST.get('creator_hidden_sig_page') or 1)

                date_x = float(request.POST.get('date_x') or request.POST.get('creator_hidden_date_x') or 0)
                date_y = float(request.POST.get('date_y') or request.POST.get('creator_hidden_date_y') or 0)
            except (ValueError, TypeError):
                sig_x, sig_y, sig_page = 0, 0, 1
                date_x, date_y = 0, 0

            sig_scale = request.POST.get('sig_scale') or request.POST.get('creator_hidden_sig_scale') or '15.0:8.0'
            date_text = request.POST.get('date_text', datetime.now().strftime('%d/%m/%Y'))
            date_scale = request.POST.get('date_scale') or request.POST.get('creator_hidden_date_scale') or '14.0:4.0'

            selected_levels = form.cleaned_data['approval_targets']
            sorted_levels = [lvl for lvl in HIERARCHY_ORDER if lvl in selected_levels]

            user_idx = HIERARCHY_ORDER.index(request.user.userlevel) if request.user.userlevel in HIERARCHY_ORDER else -1
            filtered_levels = [lvl for lvl in sorted_levels if HIERARCHY_ORDER.index(lvl) > user_idx]

            if not filtered_levels:
                messages.error(request, 'Pilih setidaknya satu pejabat dengan level di atas Anda untuk tanda tangan.')
                return redirect('documents:dashboard')

            # Ambil target divisi dari POST
            target_spv_divisi = request.POST.get('target_spv_divisi') if 'supervisor' in filtered_levels else None
            target_jm_divisi = request.POST.get('target_jm_divisi') if 'junior manajer' in filtered_levels else None

            # Validasi jika dicentang tapi tidak memilih divisi
            if 'supervisor' in filtered_levels and not target_spv_divisi:
                messages.error(request, 'Harap pilih divisi untuk Supervisor yang dituju.')
                return redirect('documents:dashboard')
            if 'junior manajer' in filtered_levels and not target_jm_divisi:
                messages.error(request, 'Harap pilih divisi untuk Store Junior Manajer yang dituju.')
                return redirect('documents:dashboard')

            initial_status = LEVEL_TO_STATUS[filtered_levels[0]]

            with transaction.atomic():
                doc = form.save(commit=False)
                doc.uploaded_by = request.user
                doc.required_levels = filtered_levels
                doc.target_spv_divisi = target_spv_divisi
                doc.target_jm_divisi = target_jm_divisi
                doc.status = initial_status
                doc.save()

                ApprovalLog.objects.create(
                    document=doc,
                    approver=request.user,
                    action='submitted',
                    comment=f'Dibuat dan ditandatangani oleh {request.user.get_userlevel_display()}',
                    signature_snapshot=request.user.ttd_digital,
                    sig_x=sig_x,
                    sig_y=sig_y,
                    sig_scale=str(sig_scale),
                    sig_page=sig_page,
                    date_text=date_text,
                    date_x=date_x,
                    date_y=date_y,
                    date_scale=str(date_scale),
                )
                notify_next_approver(doc, request=request)

            messages.success(request, f'Dokumen "{doc.judul_dokumen}" berhasil dibuat dan diteruskan ke tahap berikutnya.')
            return redirect('documents:dashboard')
        else:
            messages.error(request, 'Gagal mengunggah dokumen. Periksa isian formulir Anda.')
    return redirect('documents:dashboard')


@login_required(login_url='accounts:login')
def document_preview_view(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)
    user = request.user
    level_permission_map = {
        'supervisor': 'waiting_supervisor',
        'junior manajer': 'waiting_junior_manager',
        'store administration manager': 'waiting_sam',
        'store manager': 'waiting_store_manager',
    }

    is_matching_status = (level_permission_map.get(user.userlevel) == doc.status)
    if user.userlevel == 'supervisor':
        can_action = is_matching_status and (user.divisi == doc.target_spv_divisi)
    elif user.userlevel == 'junior manajer':
        can_action = is_matching_status and (user.divisi == doc.target_jm_divisi)
    else:
        can_action = is_matching_status

    logs = doc.approval_logs.all().order_by('-timestamp')
    approved_signatures_data = []

    for log in logs:
        if log.action in ['approved', 'submitted'] and log.signature_snapshot and log.sig_x is not None:
            approved_signatures_data.append({
                'approver': log.approver.nama_pengguna,
                'url': reverse('documents:log_signature', args=[log.id]),
                'x': log.sig_x,
                'y': log.sig_y,
                'scale': log.sig_scale if log.sig_scale else '15.0:8.0',
                'page': log.sig_page if log.sig_page else 1,
                'date_text': log.date_text or '',
                'date_x': log.date_x,
                'date_y': log.date_y,
                'date_scale': log.date_scale or '14.0:4.0',
            })

    context = {
        'doc': doc,
        'can_action': can_action,
        'logs': logs,
        'approved_signatures_data': approved_signatures_data,
        'today_date': datetime.now().strftime('%d/%m/%Y'),
    }
    return render(request, 'documents/preview.html', context)


@login_required(login_url='accounts:login')
def approve_document_view(request, doc_id):
    if request.method != 'POST':
        return redirect('documents:preview', doc_id=doc_id)

    doc = get_object_or_404(Document, id=doc_id)
    user = request.user

    expected_level = STATUS_TO_LEVEL.get(doc.status)
    if not expected_level or user.userlevel != expected_level:
        messages.error(request, 'Anda tidak memiliki hak otorisasi untuk menyetujui dokumen ini saat ini.')
        return redirect('documents:preview', doc_id=doc.id)

    # Validasi kesesuaian divisi target
    if user.userlevel == 'supervisor' and user.divisi != doc.target_spv_divisi:
        messages.error(request, f'Dokumen ini ditujukan untuk Supervisor Divisi {doc.target_spv_divisi.title() if doc.target_spv_divisi else "-"}.')
        return redirect('documents:preview', doc_id=doc.id)
    if user.userlevel == 'junior manajer' and user.divisi != doc.target_jm_divisi:
        messages.error(request, f'Dokumen ini ditujukan untuk Store Junior Manajer Divisi {doc.target_jm_divisi.title() if doc.target_jm_divisi else "-"}.')
        return redirect('documents:preview', doc_id=doc.id)

    try:
        sig_x = float(request.POST.get('sig_x', 0))
        sig_y = float(request.POST.get('sig_y', 0))
        sig_page = int(request.POST.get('sig_page', 1))
        date_x = float(request.POST.get('date_x', 0))
        date_y = float(request.POST.get('date_y', 0))
    except (ValueError, TypeError):
        sig_x, sig_y, sig_page = 0, 0, 1
        date_x, date_y = 0, 0

    sig_scale = request.POST.get('sig_scale', '15.0:8.0')
    date_text = request.POST.get('date_text', datetime.now().strftime('%d/%m/%Y'))
    date_scale = request.POST.get('date_scale', '14.0:4.0')

    new_status = get_next_status(doc, user.userlevel)
    doc.status = new_status
    doc.save()

    ApprovalLog.objects.create(
        document=doc,
        approver=user,
        action='approved',
        comment=f'Disetujui oleh {user.get_userlevel_display()}',
        signature_snapshot=user.ttd_digital,
        sig_x=sig_x,
        sig_y=sig_y,
        sig_scale=str(sig_scale),
        sig_page=sig_page,
        date_text=date_text,
        date_x=date_x,
        date_y=date_y,
        date_scale=str(date_scale),
    )

    if new_status == 'approved':
        doc.save()
        try:
            generate_signed_pdf(doc)
        except Exception as e:
            messages.warning(request, f'Dokumen approved, tetapi terjadi kendala generate PDF: {e}')
        notify_document_creator(doc, action='approved', request=request)
        messages.success(request, f'Dokumen "{doc.judul_dokumen}" telah selesai disetujui sepenuhnya!')
    else:
        doc.save()
        notify_next_approver(doc, request=request)
        messages.success(request, f'Dokumen "{doc.judul_dokumen}" berhasil disetujui dan diteruskan ke tahap berikutnya.')

    return redirect('documents:dashboard')

@login_required(login_url='accounts:login')
def download_document_view(request, doc_id):
    """Mengunduh PDF final hanya jika status dokumen sudah 'approved'."""
    doc = get_object_or_404(Document, id=doc_id)

    if doc.status != 'approved':
        messages.error(request, 'Dokumen belum selesai diapprove dan belum dapat diunduh.')
        return redirect('documents:preview', doc_id=doc.id)

    # Ambil signed_file, jika belum tergenerate coba buatkan
    if not doc.signed_file:
        try:
            generate_signed_pdf(doc)
        except Exception:
            raise Http404("Berkas tanda tangan belum siap.")

    return FileResponse(doc.signed_file.open('rb'), as_attachment=True, filename=f"SIGNED_{doc.judul_dokumen}.pdf")

@login_required(login_url='accounts:login')
def verify_password_view(request):
  """Memvalidasi kata sandi approver sebelum membubuhkan tanda tangan."""
  if request.method == 'POST':
    try:
      data = json.loads(request.body)
      password = data.get('password', '')
      if request.user.check_password(password):
        if not request.user.ttd_digital:
          return JsonResponse(
              {
                  'success': False,
                  'message': (
                      'Anda belum mengunggah tanda tangan digital di profil'
                      ' Anda.'
                  ),
              },
              status=400,
          )


        sig_url = reverse('documents:my_signature')

        return JsonResponse({'success': True, 'signature_url': sig_url})
      else:
        return JsonResponse(
            {'success': False, 'message': 'Kata sandi yang Anda masukkan salah.'},
            status=400,
        )
    except Exception:
      return JsonResponse(
          {'success': False, 'message': 'Terjadi kesalahan sistem.'}, status=500
      )
  return JsonResponse(
      {'success': False, 'message': 'Metode tidak diizinkan.'}, status=405
  )


@login_required(login_url='accounts:login')
def reject_document_view(request, doc_id):
    if request.method != 'POST':
        return redirect('documents:preview', doc_id=doc_id)

    doc = get_object_or_404(Document, id=doc_id)
    user = request.user

    level_permission_map = {
        'supervisor': 'waiting_supervisor',
        'junior manajer': 'waiting_junior_manager',
        'store administration manager': 'waiting_sam',
        'store manager': 'waiting_store_manager',
    }

    expected_status = level_permission_map.get(user.userlevel)
    if expected_status != doc.status:
        messages.error(request, 'Anda tidak memiliki hak otorisasi untuk menolak dokumen ini.')
        return redirect('documents:preview', doc_id=doc.id)

    # Validasi divisi target sebelum reject
    if user.userlevel == 'supervisor' and user.divisi != doc.target_spv_divisi:
        messages.error(request, 'Anda tidak memiliki hak otorisasi untuk menolak dokumen ini.')
        return redirect('documents:preview', doc_id=doc.id)
    if user.userlevel == 'junior manajer' and user.divisi != doc.target_jm_divisi:
        messages.error(request, 'Anda tidak memiliki hak otorisasi untuk menolak dokumen ini.')
        return redirect('documents:preview', doc_id=doc.id)

    raw_reason = request.POST.get('reject_reason', '')
    cleaned_reason = raw_reason.strip()
    if len(cleaned_reason) < 15:
        messages.error(request, 'Penolakan gagal: Alasan penolakan minimal harus 15 karakter.')
        return redirect('documents:preview', doc_id=doc.id)

    garbage_pattern = r'^[.\-_\/,\s]+$'
    if re.fullmatch(garbage_pattern, cleaned_reason):
        messages.error(request, 'Penolakan gagal: Alasan penolakan tidak boleh hanya berupa simbol atau tanda baca.')
        return redirect('documents:preview', doc_id=doc.id)

    doc.status = 'rejected'
    doc.save()

    ApprovalLog.objects.create(
        document=doc,
        approver=user,
        action='rejected',
        comment=cleaned_reason,
    )
    notify_document_creator(doc, action='rejected', reason=cleaned_reason, request=request)
    messages.warning(request, f'Dokumen "{doc.judul_dokumen}" telah ditolak.')
    return redirect('documents:dashboard')


@login_required(login_url='accounts:login')
def document_pdf_file_view(request, doc_id):
    """Mengalirkan file PDF langsung ke preview browser tanpa bergantung MEDIA_URL."""
    doc = get_object_or_404(Document, id=doc_id)
    if not doc.file_dokumen:
        raise Http404("Dokumen tidak memiliki berkas PDF.")
    
    try:
        # Buka file langsung dari disk server
        return FileResponse(doc.file_dokumen.open('rb'), content_type='application/pdf')
    except FileNotFoundError:
        raise Http404("Berkas fisik PDF tidak ditemukan di server.")

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
def signature_log_view(request, log_id):
  """Menyajikan gambar tanda tangan dari ApprovalLog."""
  log = get_object_or_404(ApprovalLog, id=log_id)
  if not log.signature_snapshot:
    raise Http404('Tidak ada berkas tanda tangan.')
  return FileResponse(log.signature_snapshot.open('rb'))
