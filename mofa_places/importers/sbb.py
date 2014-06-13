import logging
import sqlite3

from xml.sax import ContentHandler, make_parser
from collections import defaultdict

from moxie.places.importers.helpers import prepare_document

logger = logging.getLogger(__name__)




def dict_factory(cursor, row):
    """ Return sqlite data as dict """
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class SBBStationImporter(object):
    def __init__(self, indexer, precedence, sbb_db, areas, identifier_key='identifiers'):
        self.indexer = indexer
        self.precedence = precedence
        self.sbb_db = sbb_db
        self.areas = areas
        self.identifier_key = identifier_key

    def run(self):
        conn = sqlite3.connect('/home/tom/moxie/bin/example.db')
        conn.row_factory = dict_factory
        db = conn.cursor()
        if self.indexer:
            docs = []

            sql = "SELECT * FROM station"
            for row in db.execute(sql).fetchall():
                data = {}
                data['id'] = "stoparea:%s" % str(row['id'])
                data[self.identifier_key] = [str(row['id'])]
                data['location'] = "%s,%s" % (row['x'], row['y'])
                data['name'] = row['name']
                data['name_sort'] = row['name']
                data['type'] = "/transport/stop-area"
                search_results = self.indexer.search_for_ids(
                    self.identifier_key, data[self.identifier_key])
                docs.append(prepare_document(data, search_results, self.precedence))
            for atco_code, sp in self.handler.stop_points.items():
                search_results = self.indexer.search_for_ids(
                    self.identifier_key, sp[self.identifier_key])
                docs.append(prepare_document(sp, search_results, self.precedence))
            self.indexer.index(docs)
            self.indexer.commit()


def main():
    import argparse
    args = argparse.ArgumentParser()
    #args.add_argument('naptanfile', type=argparse.FileType('r'))
    db = '/home/tom/moxie/bin/example.db'
    from moxie.core.search import SearchService
    indexer = SearchService('solr+http://localhost:8983/solr/#/places')
    naptan_importer = SBBImporter(indexer, 10, db, ['340'], 'identifiers')
    naptan_importer.run()
    import pprint
    pprint.pprint(naptan_importer.handler.stop_points)
    pprint.pprint(naptan_importer.handler.stop_areas)


if __name__ == '__main__':
    main()
