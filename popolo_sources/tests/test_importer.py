import json
from mock import patch
from urlparse import urlsplit

from django.test import TestCase

from popolo.models import Person
from popolo_sources.models import PopoloSource
from popolo_sources.importer import PopoloSourceImporter


class FakeResponse(object):

    def __init__(self, response_data):
        self.response_data = response_data

    def json(self):
        return json.loads(self.response_data)

    def raise_for_status(self):
        pass


def fake_requests_get(url, *args, **kwargs):
    split = urlsplit(url)
    if split.path == '/single-person.json':
        data = '''
{
    "persons": [
        {
            "id": "a1b2",
            "name": "Alice"
        }

    ],
    "organizations": [],
    "memberships": []
}
'''
    elif split.path == '/same-person-different-source.json':
        data = '''
{
    "persons": [
        {
            "id": "a1b2",
            "name": "Alice"
        }

    ],
    "organizations": [],
    "memberships": []
}
'''
    elif split.path == '/two-people.json':
        data = '''
{
    "persons": [
        {
            "id": "a1b2",
            "name": "Alice"
        },
        {
            "id": "b1c2",
            "name": "Bob"
        }
    ]
}
'''
    else:
        raise Exception("The URL '{0}' hasn't been faked")
    return FakeResponse(data)


@patch('popolo_sources.importer.requests.get', side_effect=fake_requests_get)
class PopoloSourceTests(TestCase):

    def test_import(self, faked_get):
        popolo_source = PopoloSource.objects.create(
            url='http://example.com/single-person.json')
        importer = PopoloSourceImporter(popolo_source)
        importer.update_from_source()
        self.assertEqual(Person.objects.count(), 1)

    def test_import_two_people_twice(self, faked_get):
        popolo_source = PopoloSource.objects.create(
            url='http://example.com/two-people.json')
        importer = PopoloSourceImporter(popolo_source)
        importer.update_from_source()
        self.assertEqual(Person.objects.count(), 2)
        importer.update_from_source()
        self.assertEqual(Person.objects.count(), 2)

    def test_second_import_from_same_source_the_same(self, faked_get):
        popolo_source = PopoloSource.objects.create(
            url='http://example.com/single-person.json')
        importer = PopoloSourceImporter(popolo_source)
        importer.update_from_source()
        self.assertEqual(Person.objects.count(), 1)
        importer.update_from_source()
        self.assertEqual(Person.objects.count(), 1)

    def test_same_id_mulitiple_sources(self, faked_get):
        popolo_source_a = PopoloSource.objects.create(
            url='http://example.com/single-person.json')
        importer_a = PopoloSourceImporter(popolo_source_a)
        importer_a.update_from_source()
        popolo_source_b = PopoloSource.objects.create(
            url='http://example.com/same-person-different-source.json')
        importer_b = PopoloSourceImporter(popolo_source_b)
        importer_b.update_from_source()
        self.assertEqual(Person.objects.count(), 2)
