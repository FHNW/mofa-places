import logging
import requests
from requests import RequestException
from lxml import etree
from datetime import datetime, date, time

from moxie_sbb.domain import Station

logger = logging.getLogger(__name__)


class DefaultSbbProvider(object):
    """ SBB - Swiss railway info
    """

    _ATTRIBUTION = {'title': ("SBB - Schweizer Verkehrs Info"),
                    'url': "http://www.sbb.ch"}

    provides = {'rail-departures': "Departures",
                'rail-arrivals': "Arrivals"}

    def __init__(self, max_services=15):
        self._max_services = max_services

    def import_data(self):
        r = requests.get(self.url)
        return iter(self._scrape_json(r.text.encode('utf-8', 'ignore')))

    def _scrape_xml(self, content):
        parser = etree.HTMLParser(encoding='utf-8')
        root = etree.fromstring(content, parser)

        raise NotImplementedError
        for offer in root.iterfind('.//div[@class="offer"]'):
            obj = Station()
            #obj.name = offer.find('.//div[@class="title"]').text.strip()
            #description = offer.find('.//div[@class="trimmings"]')
            #obj.description = ' '.join(etree.tostring(
            #     description, method='text', encoding='utf-8').splitlines())
            yield obj


if __name__ == '__main__':
   provider = DefaultSbbProviderProvider()
   for x in provider.import_data():
      print(x.as_dict())
