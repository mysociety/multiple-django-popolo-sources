from __future__ import unicode_literals

from django.db import models

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class PopoloSource(models.Model):
    url = models.URLField(max_length=255)

    def __repr__(self):
        fmt = str("PopoloSource(id={0.id}, url='{0.url}')")
        return fmt.format(self)


class LinkToPopoloSource(models.Model):
    deleted_from_source = models.BooleanField(default=False)
    # Fields needed for the generic foreign key to a django-popolo
    # model.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    popolo_object = GenericForeignKey('content_type', 'object_id')
    # Now the source that this object was created from (or is associated with):
    popolo_source = models.ForeignKey(PopoloSource)
