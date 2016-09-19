from contextlib import contextmanager
import json
from mock import patch
from os.path import dirname, exists, join
import sys

from django.utils import six
from django.utils.six.moves.urllib.parse import urlsplit

from django.contrib.contenttypes.models import ContentType
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


@contextmanager
def capture_output():
    # Suggested here: http://stackoverflow.com/a/17981937/223092
    new_out, new_err = six.StringIO(), six.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield new_out, new_err
    finally:
        sys.stdout, sys.stderr = old_out, old_err


@patch('popolo_sources.importer.requests.get', side_effect=fake_requests_get)
class PopoloSourceTests(TestCase):

    def test_missing_source(self, faked_get):
        with self.assertRaises(Exception):
            popolo_source = PopoloSource.objects.create(
                url='http://example.com/does-not-exist.json')
            importer = PopoloSourceImporter(popolo_source)
            importer.update_from_source()

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

    def test_deleted_person_reappears(self, faked_get):
        popolo_source = PopoloSource.objects.create(
            url='http://example.com/two-people.json')
        # Create a deleted Alice by hand:
        alice = Person.objects.create(name='Alice')
        alice.identifiers.create(
            scheme='popit-person',
            identifier='a1b2')
        LinkToPopoloSource.objects.create(
            popolo_object=alice,
            popolo_source=popolo_source,
            deleted_from_source=True)
        # Now try updating from the source:
        importer = PopoloSourceImporter(popolo_source)
        importer.update_from_source()
        # Now try getting the link and checking that Alice is no
        # longer deleted:
        self.assertEqual(2, Person.objects.count())
        self.assertEqual(2, LinkToPopoloSource.objects.count())
        link = LinkToPopoloSource.objects.get(
            object_id=alice.id,
            content_type=ContentType.objects.get_for_model(alice),
            popolo_source=popolo_source)
        self.assertFalse(link.deleted_from_source)

    def test_multiple_identifiers_found(self, faked_get):
        popolo_source = PopoloSource.objects.create(
            url='http://example.com/single-person.json')
        alice = Person.objects.create(name='Alice')
        alice.identifiers.create(
            scheme='popit-person',
            identifier='a1b2')
        bob_with_alice_id = Person.objects.create(name='Bob')
        bob_with_alice_id.identifiers.create(
            scheme='popit-person',
            identifier='a1b2')
        LinkToPopoloSource.objects.create(
            object_id=alice.id,
            content_type=ContentType.objects.get_for_model(alice),
            popolo_source=popolo_source)
        LinkToPopoloSource.objects.create(
            object_id=bob_with_alice_id.id,
            content_type=ContentType.objects.get_for_model(bob_with_alice_id),
            popolo_source=popolo_source)
        # Now there should be multiple identifiers found when
        # importing Alice from source:
        importer = PopoloSourceImporter(popolo_source)
        with capture_output() as (out, err):
            with self.assertRaisesRegexp(
                    Person.MultipleObjectsReturned,
                    r"^Unexpectedly found more than 1 objects matching PopoloSource object, collection 'person' and ID 'a1b2' - found 2 instead.$"):
                importer.update_from_source()

    def test_unknown_collection(self, faked_get):
        popolo_source = PopoloSource.objects.create(
            url='http://example.com/single-person.json')
        importer = PopoloSourceImporter(popolo_source)
        with self.assertRaisesRegexp(
                Exception,
                r"Unknown collection 'not-a-collection'"):
            importer.get_existing_django_object('not-a-collection', 'y1z2')
