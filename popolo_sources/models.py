from django.db import models


class PopoloSource(models.Model):
    url = models.URLField(max_length=255)
