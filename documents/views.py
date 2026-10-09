import json
import re
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Document, ApprovalLog
from .forms import DocumentUploadForm
from django.core.paginator import Paginator


@login_required(login_url='accounts:login')
def dashboard_view(request):
    user = request.user
    level = user.userlevel

    queue_status_map = {
        'supervisor': 'waiting_supervisor',
        'junior manajer': 'waiting_junior_manager',
        'store administration manager': 'waiting_sam',
        'store manager': 'waiting_store_manager',
    }

    if level == 'staff':
        doc_queryset = Document.objects.filter(uploaded_by=user)
        active_queue = None
    else:
        target_status = queue_status_map.get(level)
        active_queue = Document.objects.filter(status=target_status)
        doc_queryset = Document.objects.all()

    selected_status = request.GET.get('status', 'all')
    if selected_status and selected_status != 'all':
        doc_queryset = doc_queryset.filter(status=selected_status)

    doc_queryset = doc_queryset.order_by('-created_at')

        # Pagination: 5 dokumen per halaman
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

            role_initial_status = {
                'staff': 'waiting_supervisor',
                'supervisor': 'waiting_junior_manager',
                'junior manajer': 'waiting_sam',
                'store administration manager': 'waiting_store_manager',
            }

            with transaction.atomic():
                doc = form.save(commit=False)
                doc.uploaded_by = request.user
                doc.status = role_initial_status.get(request.user.userlevel, 'waiting_supervisor')
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

            messages.success(request, f'Dokumen "{doc.judul_dokumen}" berhasil dibuat dan diteruskan ke tahap berikutnya.')
            return redirect('documents:dashboard')
        else:
            messages.error(request, 'Gagal mengunggah dokumen. Pastikan file berformat .pdf.')

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

    can_action = (level_permission_map.get(user.userlevel) == doc.status)
    logs = doc.approval_logs.all().order_by('-timestamp')

    approved_signatures_data = []
    for log in logs:
        if log.action in ['approved', 'submitted'] and log.signature_snapshot and log.sig_x is not None:
            approved_signatures_data.append({
                'approver': log.approver.nama_pengguna,
                'url': log.signature_snapshot.url,
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
    """Menyimpan persetujuan pejabat berjenjang."""
    if request.method != 'POST':
        return redirect('documents:preview', doc_id=doc_id)

    doc = get_object_or_404(Document, id=doc_id)
    user = request.user

    next_status_map = {
        'waiting_supervisor': ('supervisor', 'waiting_junior_manager'),
        'waiting_junior_manager': ('junior manajer', 'waiting_sam'),
        'waiting_sam': ('store administration manager', 'waiting_store_manager'),
        'waiting_store_manager': ('store manager', 'approved'),
    }

    rule = next_status_map.get(doc.status)
    if not rule or user.userlevel != rule[0]:
        messages.error(request, 'Anda tidak memiliki hak otorisasi untuk menyetujui dokumen ini.')
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

    new_status = rule[1]
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
        messages.success(request, f'Dokumen "{doc.judul_dokumen}" telah selesai disetujui sepenuhnya!')
    else:
        messages.success(request, f'Dokumen "{doc.judul_dokumen}" berhasil disetujui dan diteruskan ke tahap berikutnya.')

    return redirect('documents:dashboard')


@login_required(login_url='accounts:login')
def verify_password_view(request):
    """Memvalidasi kata sandi approver sebelum membubuhkan tanda tangan."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            password = data.get('password', '')
            if request.user.check_password(password):
                if not request.user.ttd_digital:
                    return JsonResponse({
                        'success': False,
                        'message': 'Anda belum mengunggah tanda tangan digital di profil Anda.'
                    }, status=400)

                return JsonResponse({
                    'success': True,
                    'signature_url': request.user.ttd_digital.url
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Kata sandi yang Anda masukkan salah.'
                }, status=400)
        except Exception:
            return JsonResponse({'success': False, 'message': 'Terjadi kesalahan sistem.'}, status=500)

    return JsonResponse({'success': False, 'message': 'Metode tidak diizinkan.'}, status=405)


@login_required(login_url='accounts:login')
def reject_document_view(request, doc_id):
    """Menangani penolakan dokumen dengan validasi ketat alasan penolakan."""
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

    messages.warning(request, f'Dokumen "{doc.judul_dokumen}" telah ditolak.')
    return redirect('documents:dashboard')