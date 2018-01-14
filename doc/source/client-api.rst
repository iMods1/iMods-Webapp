API endpoints
**********************

User APIs
======================
These are APIs for iMods app, they are only called on the client side. Administration APIs use separate endpoints.

.. autoflask:: imods:app
    :blueprints: api_mods
    :endpoints:
    :undoc-static:

.. automodule:: imods.api.routes
    :members: success_response

Constants
======================

.. automodule:: imods.models.constants
    :members:
    :undoc-members:

Exceptions
======================
.. automodule:: imods.api.exceptions
    :members:
    :undoc-members:

