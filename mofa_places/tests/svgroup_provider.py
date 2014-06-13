import unittest
from os.path import join, dirname
from datetime import date

from moxie_food.providers.svgroup import FhnwSvGroupFoodProvider


class FhnwSvGroupProviderTest(unittest.TestCase):
    """
    Tests for FHNW SV Group food provider
    """

    def test_import_food(self):
        with open(join(dirname(__file__), 'data', 'menuplan.html')) as f:
            content = f.read()
        provider = FhnwSvGroupFoodProvider(None)
        items = [item.as_dict() for item in provider._scrape_xml(content)]
        self.assertEqual(
            items,
           [{'menu_type': 'Suppe', 'price_int': 2.0, 'name': u'Gem\xfcsebouillon', 'price_ext': 3.0, 'description': 'mit Gem\xc3\xbcsestreifen'}, {'menu_type': 'Menu', 'price_int': 8.5, 'name': 'Pasta alla  Melanzane', 'price_ext': 11.5, 'description': 'dazu Basilikum-Tomatensauce'}, {'menu_type': 'Vegi', 'price_int': 8.5, 'name': 'Rotes Linsenstew mit  Aprikosen', 'price_ext': 11.5, 'description': 'und Kichererbsen dazu servieren wir Stampfkartoffeln und ein Menusalat "vegan"'}, {'menu_type': 'Tageshit', 'price_int': 7.0, 'name': 'Pouletgeschnetzeltes  "Crispy"', 'price_ext': 10.0, 'description': 'mit Risi-Bisi'}, {'menu_type': 'Special', 'price_int': 16.5, 'name': 'Grillierte Lammhuft', 'price_ext': 20.5, 'description': 'mit Thymianjus dazu Ratatouille und Kartoffelgratin'}])
