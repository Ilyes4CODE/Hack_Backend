from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AidCenter


User = get_user_model()


class LocatorOwnershipTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.farmer = User.objects.create_user(
            email='farmer1@example.com',
            password='StrongPass123',
            role='farmer',
        )
        self.other_farmer = User.objects.create_user(
            email='farmer2@example.com',
            password='StrongPass123',
            role='farmer',
        )
        self.client.force_authenticate(user=self.farmer)

    def test_farmer_creates_owned_aid_center(self):
        response = self.client.post(
            '/locator/all/',
            {
                'name': 'My Center',
                'center_type': 'itdas',
                'wilaya': 'Algiers',
                'latitude': 36.75,
                'longitude': 3.05,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        center = AidCenter.objects.get(id=response.data['id'])
        self.assertEqual(center.created_by, self.farmer)

    def test_farmer_lists_only_owned_aid_centers(self):
        AidCenter.objects.create(
            name='Owned Center',
            center_type='itdas',
            wilaya='Algiers',
            latitude=36.75,
            longitude=3.05,
            created_by=self.farmer,
        )
        AidCenter.objects.create(
            name='Other Center',
            center_type='itdas',
            wilaya='Oran',
            latitude=35.69,
            longitude=-0.64,
            created_by=self.other_farmer,
        )

        response = self.client.get('/locator/all/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Owned Center')

    def test_farmer_cannot_update_another_farmers_aid_center(self):
        center = AidCenter.objects.create(
            name='Other Center',
            center_type='itdas',
            wilaya='Oran',
            latitude=35.69,
            longitude=-0.64,
            created_by=self.other_farmer,
        )

        response = self.client.patch(
            f'/locator/{center.id}/manage/',
            {'name': 'Updated Name'},
            format='json',
        )

        self.assertEqual(response.status_code, 404)
        center.refresh_from_db()
        self.assertEqual(center.name, 'Other Center')

    def test_farmer_soft_deletes_owned_aid_center(self):
        center = AidCenter.objects.create(
            name='Owned Center',
            center_type='itdas',
            wilaya='Algiers',
            latitude=36.75,
            longitude=3.05,
            created_by=self.farmer,
        )

        response = self.client.delete(f'/locator/{center.id}/manage/')

        self.assertEqual(response.status_code, 204)
        center.refresh_from_db()
        self.assertFalse(center.is_active)
