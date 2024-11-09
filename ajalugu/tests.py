from django.test import TestCase
from django.urls import reverse, resolve

from . import views

class BaseUrlTests(TestCase):

    def test_ilm_view(self):
        response = self.client.get(reverse('ajalugu:index'))
        self.assertEqual(response.status_code, 200)