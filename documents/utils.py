# documents/utils.py
import fitz
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from io import BytesIO
from django.template.loader import render_to_string
from django.utils.html import strip_tags

STATUS_TO_LEVEL = {
    'waiting_supervisor': 'supervisor',
    'waiting_junior_manager': 'junior manajer',
    'waiting_sam': 'store administration manager',
    'waiting_store_manager': 'store manager',
}

def notify_next_approver(doc, request=None):
    """
    Mengirim notifikasi email ke user yang bertugas menandatangani dokumen pada status saat ini.
    """
    target_level = STATUS_TO_LEVEL.get(doc.status)
    if not target_level:
        return

    User = get_user_model()
    # Cari semua user aktif yang memiliki level tersebut dan email valid
    approvers = User.objects.filter(userlevel=target_level, is_active=True).exclude(email__isnull=True).exclude(email__exact='')
    
    recipient_emails = [u.email for u in approvers if u.email]
    if not recipient_emails:
        return

    doc_url = request.build_absolute_uri(f"/documents/document/{doc.id}/preview/") if request else f"/documents/document/{doc.id}/preview/"

    subject = f"[AppDoc-IGRGTO] Permintaan Tanda Tangan: {doc.judul_dokumen}"
    message = (
        f"Halo Bapak/Ibu,\n\n"
        f"Dokumen berikut membutuhkan tanda tangan dan persetujuan dari Anda:\n\n"
        f"Judul Dokumen : {doc.judul_dokumen}\n"
        f"Dibuat Oleh   : {doc.uploaded_by.nama_pengguna} ({doc.uploaded_by.get_userlevel_display()})\n"
        f"Status        : {doc.get_status_display()}\n\n"
        f"Silakan tinjau dan bubuhkan tanda tangan Anda melalui tautan berikut:\n"
        f"{doc_url}\n\n"
        f"Terima kasih.\n"
        f"Sistem Otomatis AppDoc-IGRGTO"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=recipient_emails,
            fail_silently=True,  # fail_silently=True agar jika internet kantor/SMTP gagal, transaksi web tidak crash
        )
    except Exception as e:
        print(f"[Email Error] Gagal kirim notifikasi approver: {e}")


def notify_next_approver(doc, request=None):
    """
    Mengirim notifikasi email ke user yang bertugas menandatangani dokumen pada status saat ini.
    """
    target_level = STATUS_TO_LEVEL.get(doc.status)
    if not target_level:
        return

    User = get_user_model()
    approvers = User.objects.filter(
        userlevel=target_level, 
        is_active=True
    ).exclude(email__isnull=True).exclude(email__exact='')
    
    recipient_emails = [u.email for u in approvers if u.email]
    if not recipient_emails:
        return

    doc_url = request.build_absolute_uri(f"/documents/document/{doc.id}/preview/") if request else f"/documents/document/{doc.id}/preview/"

    subject = f"[AppDoc-IGRGTO] Permintaan Tanda Tangan: {doc.judul_dokumen}"
    message = (
        f"Halo Bapak/Ibu,\n\n"
        f"Terdapat dokumen Berita Acara yang membutuhkan tanda tangan dan persetujuan dari Anda:\n\n"
        f"Judul Dokumen : {doc.judul_dokumen}\n"
        f"Dibuat Oleh   : {doc.uploaded_by.nama_pengguna} ({doc.uploaded_by.get_userlevel_display()})\n"
        f"Status        : {doc.get_status_display()}\n\n"
        f"Silakan periksa dan bubuhkan tanda tangan Anda melalui tautan berikut:\n"
        f"{doc_url}\n\n"
        f"Terima kasih.\n"
        f"Sistem Otomatis AppDoc-IGRGTO"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=recipient_emails,
            fail_silently=False,
        )
    except Exception as e:
        print(f"[Email Error] Gagal kirim notifikasi approver: {e}")


def notify_document_creator(doc, action, reason=None, request=None):
    """
    Mengirim email ke pembuat dokumen ketika dokumennya selesai disetujui atau ditolak.
    """
    creator = doc.uploaded_by
    if not creator or not creator.email:
        return

    doc_url = request.build_absolute_uri(f"/documents/document/{doc.id}/preview/") if request else f"/documents/document/{doc.id}/preview/"

    if action == 'approved':
        subject = f"[AppDoc-IGRGTO] Dokumen Telah Disetujui Sepenuhnya: {doc.judul_dokumen}"
        message = (
            f"Halo {creator.nama_pengguna},\n\n"
            f"Kabar baik! Dokumen Berita Acara Anda telah disetujui sepenuhnya oleh seluruh pejabat terkait:\n\n"
            f"Judul Dokumen : {doc.judul_dokumen}\n"
            f"Status        : Selesai / Approved\n\n"
            f"Anda dapat mengunduh berkas PDF lengkap yang sudah bertanda tangan melalui tautan berikut:\n"
            f"{doc_url}\n\n"
            f"Terima kasih.\n"
            f"AppDoc-IGRGTO"
        )
    elif action == 'rejected':
        subject = f"[AppDoc-IGRGTO] Dokumen Ditolak: {doc.judul_dokumen}"
        message = (
            f"Halo {creator.nama_pengguna},\n\n"
            f"Dokumen Berita Acara yang Anda ajukan telah DITOLAK oleh pejabat pemeriksa.\n\n"
            f"Judul Dokumen   : {doc.judul_dokumen}\n"
            f"Alasan Penolakan: {reason}\n\n"
            f"Silakan periksa detailnya pada tautan berikut:\n"
            f"{doc_url}\n\n"
            f"Terima kasih.\n"
            f"AppDoc-IGRGTO"
        )
    else:
        return

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=[creator.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"[Email Error] Gagal kirim notifikasi pembuat dokumen: {e}")

def generate_signed_pdf(doc):
    doc_pdf = fitz.open(doc.file_dokumen.path)
    logs = doc.approval_logs.filter(action__in=['submitted', 'approved']).order_by('timestamp')

    for log in logs:
        page_idx = (log.sig_page or 1) - 1
        if page_idx < 0 or page_idx >= len(doc_pdf):
            continue

        page = doc_pdf[page_idx]
        p_w = page.rect.width
        p_h = page.rect.height

        # 1. Bubuhkan Gambar Tanda Tangan
        if log.signature_snapshot and log.sig_x is not None:
            w_pct, h_pct = 20.0, 10.0
            if log.sig_scale and ':' in str(log.sig_scale):
                parts = str(log.sig_scale).split(':')
                w_pct = float(parts[0])
                h_pct = float(parts[1])

            x0 = (log.sig_x / 100.0) * p_w
            y0 = (log.sig_y / 100.0) * p_h
            x1 = x0 + (w_pct / 100.0) * p_w
            y1 = y0 + (h_pct / 100.0) * p_h

            rect_sig = fitz.Rect(x0, y0, x1, y1)
            try:
                sig_img_bytes = log.signature_snapshot.read()
                page.insert_image(rect_sig, stream=sig_img_bytes)
            except Exception:
                pass

        # 2. Bubuhkan Teks Tanggal
        if log.date_text and log.date_x is not None and log.date_y is not None:
            dw_pct, dh_pct = 12.0, 3.0
            if log.date_scale and ':' in str(log.date_scale):
                dparts = str(log.date_scale).split(':')
                dw_pct = float(dparts[0])
                dh_pct = float(dparts[1])

            dx0 = (log.date_x / 100.0) * p_w
            dy0 = (log.date_y / 100.0) * p_h
            box_w = (dw_pct / 100.0) * p_w
            box_h = (dh_pct / 100.0) * p_h

            fontsize = 8.5
            text = str(log.date_text).strip()

            # Hitung lebar teks agar posisi horizontal persis di tengah kotak
            text_len = fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
            text_x = dx0 + max(0.0, (box_w - text_len) / 2.0)
            
            # Baseline vertikal pas di tengah ketinggian kotak
            text_y = dy0 + (box_h / 2.0) + (fontsize / 3.0)

            page.insert_text(
                fitz.Point(text_x, text_y),
                text,
                fontsize=fontsize,
                fontname="helv",
                color=(0, 0, 0)
            )

    output_stream = BytesIO()
    doc_pdf.save(output_stream)
    doc_pdf.close()

    filename = f"SIGNED_{doc.id}_{doc.file_dokumen.name.split('/')[-1]}"
    doc.signed_file.save(filename, ContentFile(output_stream.getvalue()), save=True)