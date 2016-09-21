from collections import defaultdict

import requests

from django.contrib.contenttypes.models import ContentType

from popolo.importers.popolo_json import NEW_COLLECTIONS, PopoloJSONImporter
from popolo_sources.models import LinkToPopoloSource


class LinkCreator(object):

    def __init__(self, popolo_source):
        self.popolo_source = popolo_source
        self.collection_to_content_type = {
            collection: ContentType.objects.get(
                app_label='popolo', model=collection)
            for collection in NEW_COLLECTIONS}

    def notify(self, collection, django_object, created, popolo_data):
        LinkToPopoloSource.objects.update_or_create(
            content_type=self.collection_to_content_type[collection],
            object_id=django_object.id,
            popolo_source=self.popolo_source,
            defaults={'deleted_from_source': False})


class CurrentObjectsTracker(object):

    def __init__(self):
        self.seen = set()

    def notify(self, collection, django_object, created, popolo_data):
        self.seen.add((type(django_object), django_object.id))


class PopoloSourceImporter(PopoloJSONImporter):

    def __init__(self, popolo_source, *args, **kwargs):
        super(PopoloSourceImporter, self).__init__(*args, **kwargs)
        self.popolo_source = popolo_source
        self.add_observer(LinkCreator(popolo_source))

    def get_existing_objects(self, deleted):
        model_and_object_id_tuples = set()
        for collection in NEW_COLLECTIONS:
            ct = ContentType.objects.get(app_label='popolo', model=collection)
            model_class = ct.model_class()
            for ltps in LinkToPopoloSource.objects.filter(
                    deleted_from_source=deleted,
                    popolo_source=self.popolo_source,
                    content_type=ct):
                model_and_object_id_tuples.add(
                    (model_class, ltps.object_id)
                )
        return model_and_object_id_tuples

    def mark_as_deleted(self, model_and_object_id_tuples):
        class_to_object_ids = defaultdict(set)
        for mc, object_id in model_and_object_id_tuples:
            class_to_object_ids[mc].add(object_id)
        for mc, object_ids in class_to_object_ids.items():
            ct = ContentType.objects.get_for_model(mc)
            LinkToPopoloSource.objects.filter(
                popolo_source=self.popolo_source,
                content_type=ct,
                object_id__in=object_ids).update(
                    deleted_from_source=True)

    def update_from_source(self):
        # Save the objects we knew about before the update:
        existing_live_objects = self.get_existing_objects(False)
        existing_deleted_objects = self.get_existing_objects(True)
        # And set up a tracker to see what's now in the source:
        tracker = CurrentObjectsTracker()
        self.add_observer(tracker)
        # Then do the update:
        r = requests.get(self.popolo_source.url)
        r.raise_for_status()
        self.import_from_export_json_data(r.json())
        # Now after importing, we can find those objects that no
        # longer exist in the source and mark them as such.
        disappeared = existing_live_objects - tracker.seen
        self.mark_as_deleted(disappeared)

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
