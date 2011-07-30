======================================
:mod:`common` -- Utility functionality
======================================

.. automodule:: archon.common

The `denoter` utility
======================================

.. autoclass:: denoter
   :members:

.. autoclass:: DenotedNotFoundError

.. autoclass:: DenotedInvalidError

The `Merge` utility
======================================

Patch Format
--------------------------------------

A patch is simply a dictionary containing up to three keys: create, update,
and delete. They define operations to perform on the root of the dictionary
to patch.

Example Source::

    {
        "key_to_remove": "value",
        "update_this": {
            "subkey_to_remove": 2,
            "subkey_to_change": "this was changed"
        }
    }

Example patch::

    {
        "delete": ["key_to_remove"],
        "create": {"i": "was created"},
        "update": {
            "update_this": {
                "delete": ["subkey_to_remove"],
                "create": {
                    "subkey_to_change": "I changed!",
                    "subkey_created": "I'm new!"
                }
            }
        }
    }

Result::

    >>> import archon.common
    >>> merge = archon.common.Merge(source, patch=patch)
    >>> merge.patched()
    {'i': 'was created', 'update_this': {'subkey_to_change': 'I changed!', 'subkey_created': "I'm new!"}}

:create: A dictionary of keys and values to create.
:update: A dictionary of keys and patches to apply.
:delete: A list of keys to delete.

.. autoclass:: Merge
   :members:
