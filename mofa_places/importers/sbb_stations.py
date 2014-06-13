#! -*_ coding: utf-8 -*-
from __future__ import print_function

import cgi
import csv
import hashlib
import os.path
import re
import requests
import sqlite3
import time
import datetime
from lxml import etree


BOUNDS = '5.85,45.75,10.7,47.8'

def dict_factory(cursor, row):
    """ Return sqlite data as dict """
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def now():
    return datetime.datetime.now().isoformat()

class Polygon(object):

    def __init__(self):
        self.vertices = []

    def load_from_file(self, f):
        with open(f, 'rb') as csvfile:
            locreader = csv.reader(csvfile)
            self.vertices.extend([{'x': row[0], 'y': row[1]} for row in locreader])

    def contains_point(self, point):
        px = point['x']
        py = point['y']

        inPolygon = False
        j = len(vertices) - 1
        for i, v in enumerate(vertices):
            v1x = v['x']
            v1y = v['y']
            v2x = vertices[j]['x']
            v2y = vertices[j]['y']

            if (((v1y > py) != (v2y > py)) and (px < (v2x - v1x) * (py - v1y) / (v2y - v1y) + v1x)):
                inPolygon = not inPolygon

            j = i

        return inPolygon

class Stations(object):
    """ Crawl SBB page to fetch stations and put it in a sqlite DB """

    def __init__(self):
        self.basedir = os.getcwd()
        self.conn = sqlite3.connect('example.db')
        self.conn.row_factory = dict_factory
        self.db = self.conn.cursor()
        default_station = {'id': '8503000',
                           'name': u'Zürich HB',
                           'x': 8.540192,
                           'y': 47.378177,
                           'modified': now()}
        self.db.execute("""CREATE TABLE station (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255),
                x REAL,
                y REAL,
                type VARCHAR(25),
                modified TEXT
        )""")

        self.insertStation(default_station)
        self.conn.commit()

    def extractIDs(self, rows):
        return [row['id'] for row in rows]

    def fetch(self):
        sql = "SELECT * FROM station"
        checkedIDs = []

        stopSearching = False
        while not stopSearching:
            stopSearching = True

            rows = self.db.execute(sql).fetchall()
            dbIDs = self.extractIDs(rows)

            print('\nSTART ITERATION: %s records in DB / %s visited' % (len(rows), len(checkedIDs)))

            for station in rows:
                sbbID = station['id']
                if sbbID in checkedIDs:
                    continue

                # p "Searching around " + station['name'] + "(" + sbbID + ")"
                newStations = self.findStationsNear(sbbID)
                for station in newStations:
                    if station['id'] in dbIDs:
                        continue
                    print(".",end="")
                    self.insertStation(station)
                self.conn.commit()

                checkedIDs.append(sbbID)

                newIDs = self.extractIDs(newStations)
                if len(set(newIDs).difference(dbIDs)) > 0:
                    # New stations found, mark another iteration
                    stopSearching = False

                dbIDs += newIDs

    def insertStation(self, station):
        sql = "INSERT INTO station (id, name, x, y) VALUES (?, ?, ?, ?)"
        self.db.execute(sql, [station['id'], station['name'], station['x'], station['y']])

    def findStationsNear(self, input_, ignoreAmbigous=True):
        input_ = str(input_)
        if re.search(r'^[0-9]+?$', input_) is None:
            sha1 = hashlib.sha1()
            sha1.update(input_)
            cacheFile = sha1.hexdigest() + '.html'
        else:
            cacheFile = input_ + '.html'

        # TODO: stationCacheFolder - global scope ?
        stationCacheFolder = os.path.join(self.basedir, "tmp", "cache", "station")
        stationCacheFile = os.path.join(stationCacheFolder, cacheFile)

        def fetchSBBStation(input_, cacheFile, ignoreAmbigous):
            sbbURL = "http://fahrplan.sbb.ch/bin/bhftafel.exe/dn?distance=50&input=" + cgi.escape(input_) + "&near=Anzeigen"
              # p "Fetching " + sbbURL
            r = requests.get(sbbURL)
            sbbHTML = (r.text)
            time.sleep(0.1)

            if not ignoreAmbigous:
                isAmbigous = re.search(r'<option value=".+?#([0-9]+?)">', sbbHTML)
                if isAmbigous is not None:
                    ignoreAmbigous = True
                    fetchSBBStation(isAmbigous[1], cacheFile, params)
            with open(cacheFile, 'w') as f:
                  f.write(sbbHTML)

        if not os.path.exists(stationCacheFile):
          fetchSBBStation(input_, stationCacheFile, ignoreAmbigous)

        scf = open(stationCacheFile)
        parser = etree.HTMLParser()
        doc = etree.parse(scf, parser)

        newStations = []
        for tr in doc.xpath('.//tr[@class="zebra-row-0" or @class="zebra-row-1"]'):
            href = tr.find('td[1]/a').attrib['href']
            coordinates = re.search("MapLocation\.X=([0-9]+?)&MapLocation\.Y=([0-9]+?)&", href).groups()
            longitude = int(coordinates[0]) * 0.000001
            latitude = int(coordinates[1]) * 0.000001

            if self.pointIsOutside(longitude, latitude):
                continue

            try:
                idmatch  = re.search("input=([0-9]+?)&", tr.xpath('td[2]/a')[0].attrib['href'])
            except IndexError:
                print("Error @ %s" % (input_))
                continue
            if idmatch is None:
                print("Error @ %s" % (input_))
                continue

            sbbID = idmatch.group(1)
            newStations.append({
                'id':  int(sbbID),
                'name': tr.xpath('td[2]/a')[0].text.strip(),
                'x': longitude,
                'y': latitude,
                'modified': now()})

        return newStations

    def pointIsOutside(self, longitude, latitude):
        cornerSW_X, cornerSW_Y, cornerNE_X, cornerNE_Y = BOUNDS.split(',')

        return (longitude < cornerSW_X) and (latitude > cornerNE_Y) and (longitude > cornerNE_X) and (latitude < cornerSW_Y)

    def clean_geo(self):
        sql = "SELECT id, x, y FROM station"
        rows = self.db.execute(sql)

        contourCSV = os.path.join(os.path.dirname(__file__), "resources", "contour_ch_wgs84.txt")
        chPolygon = Polygon()
        chPolygon.load_from_file(contourCSV)

        for r in rows:
            if not chPolygon.contains_point({'x': r['x'], 'y': r['y']}):
                sql = "DELETE FROM station WHERE id = " + r['id']
                self.db.execute(sql)
        self.conn.commit()


def main():
    os.remove('example.db')
    s = Stations()
    s.fetch()
    s.clean_geo()


if __name__ == '__main__':
   main()
