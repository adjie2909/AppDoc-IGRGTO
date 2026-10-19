from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import CustomUser
from .models import Document


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class DashboardSummaryTests(TestCase):
    def setUp(self):
        self.staff = self.make_user('S01', 'Staff Food', 'staff', 'food')
        self.supervisor_food = self.make_user('V01', 'SPV Food', 'supervisor', 'food')
        self.junior_food = self.make_user('J01', 'SJM Food', 'junior manajer', 'food')
        self.sam = self.make_user(
            'A01', 'Store Administration Manager', 'store administration manager', 'back office'
        )
        self.store_manager = self.make_user(
            'M01', 'Store Manager', 'store manager', 'store manager'
        )

        self.food_approved = self.make_document(
            'Food Approved', 'approved', 'food', 'food'
        )
        self.food_rejected = self.make_document(
            'Food Rejected', 'rejected', 'food', 'food'
        )
        self.food_waiting = self.make_document(
            'Food Waiting', 'waiting_supervisor', 'food', 'food'
        )
        self.nonfood_approved = self.make_document(
            'Non Food Approved', 'approved', 'non food', 'non food'
        )
        self.global_approved = self.make_document('Global Approved', 'approved', None, None)

    def make_user(self, userid, name, userlevel, divisi):
        return CustomUser.objects.create_user(
            userid,
            name,
            email=f'{userid.lower()}@example.com',
            password='TestPass123!',
            userlevel=userlevel,
            divisi=divisi,
            ttd_digital='signatures/dummy.png',
        )

    def make_document(self, title, status, spv_divisi, jm_divisi):
        return Document.objects.create(
            judul_dokumen=title,
            file_dokumen=SimpleUploadedFile(f'{title}.pdf', b'%PDF-1.4'),
            uploaded_by=self.staff,
            status=status,
            target_spv_divisi=spv_divisi,
            target_jm_divisi=jm_divisi,
        )

    def dashboard(self, user, query=''):
        self.client.force_login(user)
        return self.client.get(reverse('documents:dashboard') + query)

    def test_supervisor_summary_and_history_are_limited_to_division(self):
        response = self.dashboard(self.supervisor_food)

        self.assertEqual(
            response.context['summary'],
            {'total': 3, 'approved': 1, 'rejected': 1},
        )
        self.assertEqual(response.context['summary_scope_label'], 'Divisi Food')
        titles = [doc.judul_dokumen for doc in response.context['documents']]
        self.assertCountEqual(
            titles, ['Food Approved', 'Food Rejected', 'Food Waiting']
        )
        self.assertNotIn('Non Food Approved', titles)

    def test_supervisor_status_filter_does_not_change_summary(self):
        response = self.dashboard(self.supervisor_food, '?status=approved')

        self.assertEqual(
            response.context['summary'],
            {'total': 3, 'approved': 1, 'rejected': 1},
        )
        titles = [doc.judul_dokumen for doc in response.context['documents']]
        self.assertEqual(titles, ['Food Approved'])

    def test_junior_manager_summary_and_history_are_limited_to_division(self):
        response = self.dashboard(self.junior_food)

        self.assertEqual(
            response.context['summary'],
            {'total': 3, 'approved': 1, 'rejected': 1},
        )
        self.assertEqual(response.context['summary_scope_label'], 'Divisi Food')
        titles = [doc.judul_dokumen for doc in response.context['documents']]
        self.assertNotIn('Non Food Approved', titles)

    def test_sam_and_store_manager_see_all_divisions(self):
        for user in (self.sam, self.store_manager):
            with self.subTest(user=user.userid):
                response = self.dashboard(user)
                self.assertEqual(
                    response.context['summary'],
                    {'total': 5, 'approved': 3, 'rejected': 1},
                )
                self.assertEqual(response.context['summary_scope_label'], 'Semua divisi')
                titles = [doc.judul_dokumen for doc in response.context['documents']]
                self.assertIn('Non Food Approved', titles)
                self.assertIn('Global Approved', titles)

    def test_staff_does_not_get_summary_cards(self):
        response = self.dashboard(self.staff)

        self.assertFalse(response.context['show_summary'])
        self.assertIsNone(response.context['summary'])
        self.assertNotContains(response, 'Ringkasan dokumen')
