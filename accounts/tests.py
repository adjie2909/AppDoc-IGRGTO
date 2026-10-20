from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image, ImageDraw

from .models import CustomUser
from .utils import make_signature_transparent


def make_signature_upload():
    image = Image.new('RGB', (240, 120), 'white')
    ImageDraw.Draw(image).line((40, 60, 200, 60), fill='black', width=8)
    buffer = BytesIO()
    image.save(buffer, format='JPEG')
    return SimpleUploadedFile('ttd.jpg', buffer.getvalue(), content_type='image/jpeg')


class SignatureProcessingTests(TestCase):
    def test_background_becomes_transparent_png(self):
        cleaned = make_signature_transparent(make_signature_upload())
        image = Image.open(cleaned)

        self.assertEqual(image.mode, 'RGBA')
        self.assertEqual(image.getpixel((0, 0))[3], 0)
        self.assertIsNotNone(image.getchannel('A').getbbox())

    def test_blank_image_rejected(self):
        image = Image.new('RGB', (100, 100), 'white')
        buffer = BytesIO()
        image.save(buffer, format='PNG')

        with self.assertRaises(ValidationError):
            make_signature_transparent(SimpleUploadedFile('blank.png', buffer.getvalue()))


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class RegistrationMessageTests(TestCase):
    def test_new_staff_user_is_told_to_contact_admin_for_level_upgrade(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'userid': 'N01',
                'nama_pengguna': 'New User',
                'email': 'new@example.com',
                'divisi': 'food',
                'password': 'NewPass123!',
                'password_confirm': 'NewPass123!',
                'ttd_digital': make_signature_upload(),
            },
            follow=True,
        )

        self.assertContains(response, 'Userlevel saat ini masih Staff')
        self.assertContains(response, 'Hubungi EDP jika userlevel perlu diubah')
        self.assertContains(response, 'id="systemMessageModal"')
        self.assertContains(response, 'alert-warning')
        self.assertNotContains(response, 'toast-slide-box')
        self.assertEqual(CustomUser.objects.get(userid='N01').userlevel, 'staff')

    def test_non_registration_message_still_uses_toast(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'unknown', 'password': 'wrong'},
        )

        self.assertContains(response, 'UserID atau Password salah.')
        self.assertContains(response, 'toast-slide-box')
        self.assertNotContains(response, 'id="systemMessageModal"')


@override_settings(
    SESSION_IDLE_TIMEOUT=30 * 60,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class SessionIdleTimeoutTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            'T02',
            'Idle User',
            email='idle@example.com',
            password='TestPass123!',
            ttd_digital='signatures/dummy.png',
        )
        self.client.force_login(self.user)

    def test_idle_session_returns_user_to_login_with_popup(self):
        session = self.client.session
        session['last_activity'] = timezone.now().timestamp() - (30 * 60 + 1)
        session.save()

        response = self.client.get(reverse('documents:dashboard'), follow=True)

        self.assertEqual(response.redirect_chain[0][0], reverse('accounts:login'))
        self.assertContains(response, 'Silakan login kembali.')
        self.assertContains(response, 'id="systemMessageModal"')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_active_session_refreshes_activity_timestamp(self):
        last_activity = timezone.now().timestamp() - 60
        session = self.client.session
        session['last_activity'] = last_activity
        session.save()

        response = self.client.get(reverse('documents:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertGreater(self.client.session['last_activity'], last_activity)
        self.assertNotContains(response, 'systemMessageModal')

    def test_login_starts_activity_timer(self):
        self.client.logout()

        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'T02', 'password': 'TestPass123!'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('last_activity', self.client.session)


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class ProfileAndUploadTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            'T01', 'Test User', email='test@example.com', password='OldPass123!'
        )
        self.client.force_login(self.user)

    def test_upload_signature_is_cleaned(self):
        response = self.client.post(
            reverse('accounts:upload_signature'), {'ttd_digital': make_signature_upload()}
        )

        self.assertRedirects(
            response, reverse('accounts:dashboard_redirect'), fetch_redirect_response=False
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.ttd_digital.name.endswith('.png'))
        with self.user.ttd_digital.open('rb') as saved:
            image = Image.open(saved)
            self.assertEqual(image.mode, 'RGBA')

    def test_model_save_processes_direct_upload(self):
        self.user.ttd_digital = make_signature_upload()
        self.user.save()

        self.assertTrue(self.user.ttd_digital.name.endswith('.png'))
        with self.user.ttd_digital.open('rb') as saved:
            self.assertEqual(Image.open(saved).mode, 'RGBA')

    def test_profile_shows_signature_and_changes_password(self):
        self.user.ttd_digital = make_signature_upload()
        self.user.save()

        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, reverse('accounts:my_signature'))
        self.assertContains(response, 'Ubah password')
        self.assertContains(response, 'data-password-strength')
        self.assertContains(response, 'data-dropzone')

        response = self.client.post(
            reverse('accounts:profile'),
            {
                'old_password': 'OldPass123!',
                'new_password1': 'NewPass456!',
                'new_password2': 'NewPass456!',
            },
        )
        self.assertRedirects(response, reverse('accounts:profile'))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))
        self.assertEqual(self.client.get(reverse('accounts:profile')).status_code, 200)

    def test_profile_updates_signature(self):
        self.user.ttd_digital = make_signature_upload()
        self.user.save()

        response = self.client.post(
            reverse('accounts:profile'),
            {'ttd_digital': make_signature_upload(), 'signature_submit': '1'},
        )

        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.ttd_digital.name.endswith('.png'))
        with self.user.ttd_digital.open('rb') as saved:
            self.assertEqual(Image.open(saved).mode, 'RGBA')
