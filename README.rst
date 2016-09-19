Manage data from multiple sources using django-popolo
=====================================================

This package provides a PopoloSource Django model to represent a
URL from which you can fetch Popolo JSON data.  It allows you to
import data from multiple such sources into django-popolo models
while maintaining an association with the source they came from,
and making sure that a change in one source doesn't affect the
models from any other.

In addition, this package allows you to track objects that have
been deleted from a source; they are marked as having
disappeared, but the django-popolo models are not deleted.  If
they reappear with the same ID in the Popolo JSON source, the
disappeared flag (`deleted_from_source`) will be set back to
`True`.

It is only the objects that are listed at the top level of a
Popolo JSON file that are tracked by the code in this package.
That includes:

* `Area`
* `Membership`
* `Organization`
* `Person`
* `Post`

But does not include, for example, `ContactDetail`.

Usage
-----

To create a new `PopoloSource` you can do:

.. code:: python

    from popolo_sources.models import PopoloSource

    ps = PopoloSource(url='http://example.com/parliament.json')

To then create django-popolo models (`Person`, `Organization`,
etc.) based on the Popolo JSON at that URL, you can now do:

.. code:: python

    ps.update_from_source()

You can run `.update_from_source()` again to update the models
based on any changes in the Popolo JSON source.

The model that represents the join table linking `PopoloSource`
models with django-popolo models is
`popolo_sources.models.LinkToPopoloSource`. This model has the
`deleted_from_source` attributed, so you can find all
non-deleted top-level django-popolo with code like:

.. code:: python

    for ltps in LinkToPopoloSource.filter(deleted_from_source=False):
        print ltps.popolo_object

Tests
-----

To run the tests you can do:

.. code:: bash

    pip install -e .[test]
    ./runtests.py
