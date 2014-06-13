Food endpoint
================

Endpoint to search and retrieve information about restaurant food. Follows specification of Moxie.

.. http:get:: /food

    Get weather information

    **Example request**:

    .. sourcecode:: http

		GET /foos HTTP/1.1
		Host: api.m.ox.ac.uk
		Accept: application/json

    **Example response as JSON**:

    .. sourcecode:: http
    
        HTTP/1.1 200 OK
        Content-Type: application/json

XXX


    :statuscode 200: resource found
    :statuscode 503: service not available
