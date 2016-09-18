from django.test import TestCase

from popolo.models import Person
from popolo_sources.models import PopoloSource, LinkToPopoloSource


class LinkToPopoloSourceTests(TestCase):

    def test_object_creation(self):
        person = Person.objects.create(name='Joe Bloggs')
        popolo_source = PopoloSource.objects.create(
            url='http://example.com/popolo.json')
        LinkToPopoloSource.objects.create(
            popolo_source=popolo_source,
            popolo_object=person,
        )
