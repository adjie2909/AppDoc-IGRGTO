# documents/utils.py
import fitz
from django.core.files.base import ContentFile
from io import BytesIO

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