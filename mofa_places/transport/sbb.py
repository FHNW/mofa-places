import logging
import requests

import json
from moxie.core.metrics import statsd
from moxie.transport.providers import TransportRTIProvider
from moxie.transport.providers.ldb import override_loglevel

logger = logging.getLogger(__name__)

OPERATOR_KEY = "title"
UNKNOWN_OPERATOR = "unknown"

class SbbRtiProvider(TransportRTIProvider):
    """
    """

    STATIONBOARD = "http://transport.opendata.ch/v1/stationboard"
    _ATTRIBUTION = {'title': ("Powered by SBB OpenData"),
                    'url': "http://www.sbb.ch"}

    provides = {'rail-departures': "Departures",
                'rail-arrivals': "Arrivals"}

    def __init__(self, url, max_services=15):
        self.url = url
        self._max_services = max_services

    def handles(self, doc, rti_type=None):
        if rti_type and rti_type not in self.provides:
            return False
        for ident in doc.identifiers:
            if ident.startswith('sbb'):
                return True
        return False

    def invoke(self, doc, rti_type):
        for ident in doc.identifiers:
            if ident.startswith('sbb'):
                _, sbb_code = ident.split(':')
                with statsd.timer('transport.providers.sbb.rti'):
                    if rti_type == 'rail-departures':
                        services, messages = self.get_departure_board(sbb_code)
                    elif rti_type == 'rail-arrivals':
                        services, messages = self.get_arrival_board(sbb_code)
                title = self.provides.get(rti_type)
                return services, messages, rti_type, title

    def get_departure_board(self, sbb_code):
        with override_loglevel('WARNING'):
            resp = requests.get(self.STATIONBOARD,
                                params={'limit': self._max_services,
                                        'id': sbb_code})
            result = json.loads(resp.text)
            messages = []
            services = [item['stop'] for item in result.get('stationboard', '')]
            import sys
            print >> sys.stderr, services
            return services, messages

    def get_arrival_board(self, crs):
        with override_loglevel('WARNING'):
            # XXX not implemented yet
            return [], []


