from contextlib import contextmanager
from mock import patch
import sys

from django.core.management import call_command, CommandError
from django.test import TestCase
from django.utils import six

from popolo_sources.models import PopoloSource
from popolo_sources.importer import PopoloSourceImporter


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


@patch(
    'popolo_sources.management.commands.' \
    'popolo_sources_update.PopoloSourceImporter',
    autospec=PopoloSourceImporter)
class UpdateCommandTests(TestCase):

    def test_update_source(self, mock_importer):
        ps = PopoloSource.objects.create(url='http://example.com/foo.json')
        with capture_output():
            call_command('popolo_sources_update', 'http://example.com/foo.json')
        mock_importer.assert_called_once_with(ps)
        mock_importer.return_value.update_from_source.assert_called_once_with()

    def test_update_source_from_id(self, mock_importer):
        ps = PopoloSource.objects.create(url='http://example.com/foo.json')
        with capture_output():
            call_command('popolo_sources_update', str(ps.id))
        mock_importer.assert_called_once_with(ps)
        mock_importer.return_value.update_from_source.assert_called_once_with()

    def test_update_source_id_does_not_exist(self, mock_importer):
        with self.assertRaisesRegexp(CommandError, r'^Source not found$'):
            with capture_output():
                call_command('popolo_sources_update', '1')
        mock_importer.assert_not_called()

    def test_update_source_url_does_not_exist(self, mock_importer):
        with self.assertRaisesRegexp(CommandError, r'^Source not found$'):
            with capture_output():
                call_command('popolo_sources_update', 'http://example.com/asdpofiaj')
        mock_importer.assert_not_called()

    def test_invalid_url(self, mock_importer):
        # It's remarkably hard to find something that urlsplit won't
        # parse, but this malformed IPv6 address does it:
        with self.assertRaisesRegexp(CommandError, r'^Malformed argument'):
            call_command('popolo_sources_update', 'http://[::1')
        mock_importer.assert_not_called()

    def test_create_specified_for_an_existing_source(self, mock_importer):
        PopoloSource.objects.create(url='http://example.com/foo.json')
        with self.assertRaisesRegexp(
                CommandError,
                r'You specified --create, but that source already exists'):
            call_command(
                'popolo_sources_update',
                '--create',
                'http://example.com/foo.json')
        mock_importer.assert_not_called()

    def test_create_only_works_with_a_url(self, mock_importer):
        with self.assertRaisesRegexp(
                CommandError,
                r'If you specify --create, the argument must be a URL'):
            call_command(
                'popolo_sources_update',
                '--create',
                '1')
        mock_importer.assert_not_called()

    def test_successfully_create_a_source(self, mock_importer):
        with capture_output():
            call_command(
                'popolo_sources_update',
                '--create',
                'http://example.com/foo.json')
        ps = PopoloSource.objects.get()
        self.assertEqual(ps.url, 'http://example.com/foo.json')

    def test_other_sources_suggested(self, mock_importer):
        existing_sources = [
            PopoloSource.objects.create(url='http://example.com/foo.json'),
            PopoloSource.objects.create(url='http://example.com/bar.json'),
        ]
        with capture_output() as (out, err):
            with self.assertRaisesRegexp(CommandError, r'^Source not found'):
                call_command('popolo_sources_update', 'http://foo')
        self.assertEqual(
            out.getvalue().strip().splitlines(),
            ['That source could not be found.',
             'Did you mean one of the following?',
             '{0.id}: {0.url}'.format(existing_sources[0]),
             '{0.id}: {0.url}'.format(existing_sources[1])])
