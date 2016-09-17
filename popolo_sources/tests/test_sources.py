from django.test import TestCase

from popolo_sources.models import PopoloSource


class PopoloSourceTests(TestCase):

    def test_object_creation(self):
        PopoloSource.objects.create(url='http://example.com/popolo.json')
