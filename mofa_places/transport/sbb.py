import logging
import requests

import json
from itertools import chain
from requests.exceptions import RequestException
from moxie.core.exceptions import ServiceUnavailable
from moxie.core.metrics import statsd
from moxie.transport.providers import TransportRTIProvider

logger = logging.getLogger(__name__)

OPERATOR_KEY = "title"
UNKNOWN_OPERATOR = "unknown"

class SbbRtiProvider(TransportRTIProvider):
    """
    """

    provides = {'train': "Live train departure times"}

    def __init__(self, url, timeout=2):
        """
        Init
        :param url: URL of SBB instance
        :param timeout: (optional) timeout when trying to reach URL
        """
        self.url = url
        self.timeout = timeout

    def handles(self, doc, rti_type=None):
        if rti_type and rti_type not in self.provides:
            return False
        for ident in doc.identifiers:
            if ident.startswith('sbb'):
                import inspect
                import sys
                print >> sys.stderr, inspect.stack()
                return True
        return False

    def invoke(self, doc, rti_type):
        for ident in doc.identifiers:
            if ident.startswith('sbb'):
                _, sbb_code = ident.split(':')
                services, messages = self.get_rti(sbb_code)
                title = self.provides.get(rti_type)
                return services, messages, rti_type, title

    def get_url(self, sbb_code):
        """
        Format a URL with a naptan code and URL of the instance
        @param sbb_code: Naptan code to append to the URL
        @return: formatted URL
        """
        return "http://transport.opendata.ch/v1/stationboard?id={0}&limit=5".format(sbb_code)

    def get_rti(self, sbb_code):
        """
        Get a dict containing RTI
        @param sbb_code: SMS code to search for
        @return: dictionary of services
        """
        try:
            with statsd.timer('transport.providers.sbb.rti_request'):
                response = requests.get(self.get_url(sbb_code),
                                        timeout=self.timeout)
                response.raise_for_status()
        except RequestException:
            logger.warning('Error in request to SBB', exc_info=True,
                         extra={
                             'data': {
                                 'url': self.url,
                                 'naptan': sbb_code}
                         })
            raise ServiceUnavailable()
        else:
            with statsd.timer('transport.providers.cloudamber.parse_html'):
                return self.parse_json(response.text)

    def parse_json(self, content):
        """
        Parse JSON content from a Opendata SBB page
        @param content: JSON content
        @return: list of services, messages
        """
        services = []
        messages = []
        try:
            
            xml = etree.fromstring(content, parser=etree.HTMLParser())
            # we need the second table
            cells = xml.findall('.//div[@class="cloud-amber"]')[0].findall('.//table')[1].findall('tbody/tr/td')

            # retrieved all cells, splitting every CELLS_PER_ROW to get rows
            CELLS_PER_ROW = 5
            rows = [cells[i:i+CELLS_PER_ROW] for i in range(0, len(cells), CELLS_PER_ROW)]

            parsed_services = {}

            for row in rows:
                service, destination, proximity = [row[i].text.encode('utf8').replace('\xc2\xa0', '')
                                                   for i in range(3)]

                # Get the operator e.g. "OBC" this is "title" attr from an
                # image, if there is an error accessing set to UNKNOWN_OPERATOR
                try:
                    operator = row[3][0]
                    operator = operator.get(OPERATOR_KEY, UNKNOWN_OPERATOR)
                except IndexError:
                    # For some reason the operator column is missing
                    operator = UNKNOWN_OPERATOR

                if proximity.lower() == 'due':
                    diff = 0
                else:
                    diff = int(proximity.split(' ')[0])

                if not service in parsed_services:
                    # first departure of this service
                    parsed_services[service] = (destination, (proximity, diff), [], operator)
                else:
                    # following departure of this service
                    parsed_services[service][2].append((proximity, diff))

            services = [(s[0], s[1][0], s[1][1], s[1][2], s[1][3]) for s in parsed_services.items()]
            services.sort(key=lambda x: (' '*(5-len(x[0]) + (1 if x[0][-1].isalpha() else 0)) + x[0]))
            services.sort(key=lambda x: x[2][1])

            services = [{'service': s[0],
                         'destination': s[1],
                         'next': s[2][0],
                         'following': [f[0] for f in s[3]],
                         'operator': s[4],
                         } for s in services]

            # messages that can be displayed (bus stop)
            cells = xml.findall('.//table')[0].findall('tr/td')

            try:
                messages = cells[3]
                parts = ([messages.text] +
                         list(chain(*([c.text, etree.tostring(c), c.tail] for c in messages.getchildren()))) +
                         [messages.tail])
                messages = ''.join([p for p in parts if p])
                messages = [messages]
            except IndexError:
                pass
                # no message

        except Exception:
            logger.info('Unable to parse HTML', exc_info=True, extra={
                'data': {
                    'html_content': content,
                    },
                })

        return services, messages
