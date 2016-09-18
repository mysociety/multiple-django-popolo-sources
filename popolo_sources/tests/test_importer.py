import json
from mock import patch
from os.path import dirname, exists, join
from six.moves.urllib.parse import urlsplit

from django.test import TestCase

from popolo.models import Person
from popolo_sources.models import PopoloSource, LinkToPopoloSource
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
    basename = split.path.lstrip('/').replace('/', '_')
    filename = join(dirname(__file__), 'fixtures', basename)
    if not exists(filename):
        raise Exception("The URL '{0}' hasn't been faked".format(url))
    with open(filename) as f:
        return FakeResponse(f.read())


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

    def test_more_popolo_collections(self, faked_get):
        popolo_source = PopoloSource.objects.create(
            url='http://example.com/more-collections.json')
        importer = PopoloSourceImporter(popolo_source)
        importer.update_from_source()
        # Check all the expected links have been created. Note that
        # this doesn't include ContactDetail, Identifier, Source or
        # other objects related to the top-level collections - it's
        # just the top-level objects.
        links_cts = LinkToPopoloSource.objects.values_list(
            'content_type__model', flat=True)
        self.assertEqual(
            sorted(links_cts),
            ['area', 'membership', 'organization', 'person', 'post']
        )

    def test_two_people_one_later_removed(self, faked_get):
        popolo_source = PopoloSource.objects.create(
            url='http://example.com/two-people.json')
        importer = PopoloSourceImporter(popolo_source)
        importer.update_from_source()
        # Now change the URL of the source to one that only has one
        # person:
        popolo_source.url = 'http://example.com/single-person.json'
        popolo_source.save()
        importer.update_from_source()
        self.assertEqual(2, LinkToPopoloSource.objects.count())
        deleted_person = LinkToPopoloSource.objects.get(deleted_from_source=True)
        self.assertEqual(deleted_person.popolo_object.name, 'Bob')
