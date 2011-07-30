==================================
:mod:`objects` -- Core objects
==================================

.. automodule:: archon.objects

Entity Types
==================================

Entity Instantiation
----------------------------------

#. When created, the datastore looks for JSON files in its directory and
   inspects them. If they have the appropriate structure, the data is stored
   in a thunk for later loading.
#. When code requests something from the datastore, that object is
   loaded. (See :doc:`datastore` for more details.) If that object is an
   entity, it is assumed to be a *prototype* and should not be modified.
#. Any code that needs to use an entity should call :meth:`Entity.copy`. If
   the entity is mutable, this will create a shallow copy; else, the
   prototype itself will be returned.
#. Mutable entities will be located in a special location: the `instances`
   datastore in the same datastore as the player entity. They will be saved or
   loaded to this location, so that changes are preserved.

.. autoclass:: Entity
   :members:

   .. attribute:: prototype

.. autoclass:: Room
   :members:

   .. attribute:: contents

   .. attribute:: outputs

   .. attribute:: allContents

.. autoclass:: EntityKey

.. autoclass:: EntityData

Entity Hooks
=================================

When an entity is created, it searches for an entity hook with the same
"kind" as the entity. Applications use these hooks to define special
behavior for different kinds of entities, such as characters, weapons, and
consumables.

.. autoclass:: EntityHook
   :members:

.. autoclass:: MutableEntityHook
   :members:

.. autoclass:: PlayerEntityHook
   :members:
