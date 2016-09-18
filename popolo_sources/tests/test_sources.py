from django.test import TestCase

from popolo_sources.models import PopoloSource


class PopoloSourceTests(TestCase):

    def test_object_creation(self):
        PopoloSource.objects.create(url='http://example.com/popolo.json')

    def test_popolo_source_repr(self):
        ps = PopoloSource.objects.create(url='http://example.com/popolo.json')
        self.assertEqual(
            repr(ps),
            "PopoloSource(id={0}, url='http://example.com/popolo.json')".format(ps.id)
        )
