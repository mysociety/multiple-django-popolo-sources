from __future__ import print_function, unicode_literals

import re

from django.core.management.base import BaseCommand, CommandError
from django.utils.six.moves.urllib.parse import urlsplit

from popolo_sources.models import PopoloSource
from popolo_sources.importer import PopoloSourceImporter


REQUIRED_ARG = 'POPOLO-JSON-URL | POPOLO-SOURCE-ID'


def is_url(s):
    try:
        split_url = urlsplit(s)
    except ValueError:
        return False
    return split_url.scheme in ('http', 'https')


def get_source(source_arg):
    if re.search(r'^\d+$', source_arg):
        source_id = int(source_arg)
        ps = PopoloSource.objects.get(pk=source_id)
    elif is_url(source_arg):
        ps = PopoloSource.objects.get(url=source_arg)
    else:
        raise CommandError(u'Malformed argument: {}'.format(source_arg))
    return ps


def create_source(source_arg):
    if not is_url(source_arg):
        msg = "If you specify --create, the argument must be a URL"
        raise CommandError(msg)
    return PopoloSource.objects.create(url=source_arg)


class Command(BaseCommand):

    help = 'Update from source of Popolo JSON'

    def add_arguments(self, parser):
        parser.add_argument(REQUIRED_ARG)
        parser.add_argument('--create', action='store_true')

    def handle(self, *args, **options):
        source_arg = options[REQUIRED_ARG]
        create = options['create']
        try:
            ps = get_source(source_arg)
            if create:
                msg = "You specified --create, but that source already exists"
                raise CommandError(msg)
        except PopoloSource.DoesNotExist:
            if create:
                ps = create_source(source_arg)
                print("Created a source for that URL: {0}".format(ps.id))
            else:
                print("That source could not be found.")
                if PopoloSource.objects.exists():
                    print("Did you mean one of the following?")
                    for existing_source in PopoloSource.objects.order_by('pk'):
                        print('{0.id}: {0.url}'.format(existing_source))
                raise CommandError('Source not found')
        print("Attempting to import from {0}".format(repr(ps)))
        importer = PopoloSourceImporter(ps)
        importer.update_from_source()
