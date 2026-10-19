from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageChops, ImageFilter, ImageOps, UnidentifiedImageError


def make_signature_transparent(uploaded_file):
    """Buat latar kertas putih/abu-abu transparan dan simpan guratan sebagai PNG RGBA."""
    try:
        with Image.open(uploaded_file) as source:
            image = ImageOps.exif_transpose(source).convert('RGBA')
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError('Berkas tanda tangan bukan gambar yang valid.') from exc

    canvas = Image.new('RGBA', image.size, 'white')
    canvas.alpha_composite(image)
    rgb = canvas.convert('RGB')

    gray = ImageOps.grayscale(rgb)
    # shortcut: threshold cocok untuk kertas putih/abu-abu; ganti ke adaptive threshold jika latar berwarna.
    radius = max(4, min(gray.size) // 40)
    local_background = gray.filter(ImageFilter.GaussianBlur(radius))
    difference = ImageChops.difference(gray, local_background)
    alpha = difference.point(
        lambda value: 0 if value <= 18 else min(255, (value - 18) * 255 // 54)
    )

    bbox = alpha.getbbox()
    if bbox is None:
        raise ValidationError('Guratan tanda tangan tidak terdeteksi pada gambar.')

    padding = 8
    left, top, right, bottom = bbox
    crop_box = (
        max(0, left - padding),
        max(0, top - padding),
        min(rgb.width, right + padding),
        min(rgb.height, bottom + padding),
    )
    clean = rgb.crop(crop_box).convert('RGBA')
    clean.putalpha(alpha.crop(crop_box))

    output = BytesIO()
    clean.save(output, format='PNG', optimize=True)
    stem = Path(uploaded_file.name).stem or 'signature'
    return ContentFile(output.getvalue(), name=f'{stem}.png')
