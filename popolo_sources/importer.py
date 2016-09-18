import requests

from django.contrib.contenttypes.models import ContentType

from popolo.importers.popolo_json import NEW_COLLECTIONS, PopoloJSONImporter
from popolo_sources.models import LinkToPopoloSource


class LinkCreator(object):

    def __init__(self, popolo_source):
        self.popolo_source = popolo_source

    def notify(self, collection, django_object, created, popolo_data):
        if created:
            LinkToPopoloSource.objects.create(
                popolo_object=django_object,
                popolo_source=self.popolo_source)


class PopoloSourceImporter(PopoloJSONImporter):

    def __init__(self, popolo_source, *args, **kwargs):
        super(PopoloSourceImporter, self).__init__(*args, **kwargs)
        self.popolo_source = popolo_source
        self.add_observer(LinkCreator(popolo_source))

    def update_from_source(self):
        r = requests.get(self.popolo_source.url)
        r.raise_for_status()
        self.import_from_export_json_data(r.json())

    # We need to override this so that we only consider something an
    # existing object if it's from the same PopoloSource, as well as
    # having the right identifier.

    def get_existing_django_object(self, popit_collection, popit_id):
        if popit_collection not in NEW_COLLECTIONS:
            raise Exception("Unknown collection '{collection}'".format(
                collection=popit_collection
            ))
        model_class = self.get_popolo_model_class(popit_collection)
        # Expressing this in the Django ORM is too painful for me.
        raw_qs = model_class.objects.raw(
            '''
SELECT po.*
    FROM popolo_{collection} po,
         popolo_identifier pi,
            django_content_type ct,
         popolo_sources_linktopopolosource ltps
    WHERE po.id = pi.object_id AND
          pi.content_type_id = ct.id AND
          pi.scheme = '{id_prefix}{collection}' AND
          pi.identifier = %s AND
          ct.app_label = 'popolo' AND
          ct.model = %s AND
          ltps.content_type_id = ct.id AND
          ltps.object_id = po.id AND
          ltps.popolo_source_id = %s
'''.format(id_prefix=self.id_prefix, collection=popit_collection),
            [popit_id, popit_collection, self.popolo_source.id]
        )
        matching_objects = list(raw_qs)
        count = len(matching_objects)
        if not count:
            return None
        if count > 1:
            msg = "Unexpectedly found more than 1 objects matching " \
                "{source}, collection '{collection}' and ID '{popit_id}' - " \
                "found {count} instead."
            raise model_class.MultipleObjectsReturned(msg.format(
                source=self.popolo_source,
                collection=popit_collection,
                popit_id=popit_id,
                count=count,
            ))
        return matching_objects[0]
