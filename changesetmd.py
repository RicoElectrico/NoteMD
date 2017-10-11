#!/usr/bin/python
'''
ChangesetMD is a simple XML parser to read the weekly changeset metadata dumps
from OpenStreetmap into a postgres database for querying.

@author: Toby Murray
'''

import os
import sys
import argparse
import psycopg2
import psycopg2.extras
import queries
import gzip
import urllib2
import yaml
from lxml import etree
from datetime import datetime
from datetime import timedelta
from StringIO import StringIO

try:
    from bz2file import BZ2File
    bz2Support = True
except ImportError:
    bz2Support = False

BASE_REPL_URL = "http://planet.openstreetmap.org/replication/changesets/"

class ChangesetMD():
    def __init__(self, createGeometry):
        self.createGeometry = createGeometry

    def truncateTables(self, connection):
        print 'truncating tables'
        cursor = connection.cursor()
        cursor.execute("TRUNCATE TABLE note_comment CASCADE;")
        cursor.execute("TRUNCATE TABLE note CASCADE;")
        cursor.execute(queries.dropIndexes)
        connection.commit()

    def createTables(self, connection):
        print 'creating tables'
        cursor = connection.cursor()
        cursor.execute(queries.createNoteTable)
        if self.createGeometry:
            cursor.execute(queries.createGeometryColumn)
        connection.commit()

    def insertNew(self, connection, id, createdAt, closedAt, lat, lon, comments):
        cursor = connection.cursor()
        if self.createGeometry:          
            cursor.execute('''INSERT into note
                    (id, created_at, closed_at, lon, lat, geom)
                    values (%s,%s,%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s), 4326))''',
                    (id, createdAt, closedAt, lon, lat, lon, lat))
        else:
            cursor.execute('''INSERT into note
                    (id, created_at, closed_at, lon, lat)
                    values (%s,%s,%s,%s,%s)''',
                    (id, createdAt, closedAt, lon, lat))
        for comment in comments:
            cursor.execute('''INSERT into note_comment
                    (comment_note_id, comment_action, comment_date, comment_user_id, comment_user_name, comment_text)
                    values (%s,%s,%s,%s,%s,%s)''',
                    (id, comment['action'], comment['timestamp'], comment['uid'], comment['user'], comment['text']))

    def parseFile(self, connection, changesetFile):
        parsedCount = 0
        startTime = datetime.now()
        cursor = connection.cursor()
        context = etree.iterparse(changesetFile)
        action, root = context.next()
        for action, elem in context:
            if(elem.tag != 'note'):
                continue

            parsedCount += 1

            comments = []
            for commentElement in elem.iterchildren(tag='comment'):
                comment = dict()
                comment['action'] = commentElement.attrib.get('action')
                comment['timestamp'] = commentElement.attrib.get('timestamp')               
                comment['uid'] = commentElement.attrib.get('uid', None)
                comment['user'] = commentElement.attrib.get('user', None)
                comment['text'] = commentElement.text
                comments.append(comment)


            self.insertNew(connection, elem.attrib['id'], elem.attrib['created_at'], elem.attrib.get('closed_at', None),
                           elem.attrib['lat'], elem.attrib['lon'], comments)

            if((parsedCount % 10000) == 0):
                print "parsed %s" % ('{:,}'.format(parsedCount))
                print "cumulative rate: %s/sec" % '{:,.0f}'.format(parsedCount/timedelta.total_seconds(datetime.now() - startTime))

            #clear everything we don't need from memory to avoid leaking
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        connection.commit()
        print "parsing complete"
        print "parsed {:,}".format(parsedCount)


if __name__ == '__main__':
    beginTime = datetime.now()
    endTime = None
    timeCost = None

    argParser = argparse.ArgumentParser(description="Parse OSM Changeset metadata into a database")
    argParser.add_argument('-t', '--trunc', action='store_true', default=False, dest='truncateTables', help='Truncate existing tables (also drops indexes)')
    argParser.add_argument('-c', '--create', action='store_true', default=False, dest='createTables', help='Create tables')
    argParser.add_argument('-H', '--host', action='store', dest='dbHost', help='Database hostname')
    argParser.add_argument('-P', '--port', action='store', dest='dbPort', default=None, help='Database port')
    argParser.add_argument('-u', '--user', action='store', dest='dbUser', default=None, help='Database username')
    argParser.add_argument('-p', '--password', action='store', dest='dbPass', default=None, help='Database password')
    argParser.add_argument('-d', '--database', action='store', dest='dbName', help='Target database', required=True)
    argParser.add_argument('-f', '--file', action='store', dest='fileName', help='OSM changeset file to parse')
    argParser.add_argument('-g', '--geometry', action='store_true', dest='createGeometry', default=False, help='Build geometry of changesets (requires postgis)')

    args = argParser.parse_args()

    conn = psycopg2.connect(database=args.dbName, user=args.dbUser, password=args.dbPass, host=args.dbHost, port=args.dbPort)


    md = ChangesetMD(args.createGeometry)
    if args.truncateTables:
        md.truncateTables(conn)

    if args.createTables:
        md.createTables(conn)

    psycopg2.extras.register_hstore(conn)


    if not (args.fileName is None):
        if args.createGeometry:
            print 'parsing changeset file with geometries'
        else:
            print 'parsing changeset file'
        changesetFile = None
        if(args.fileName[-4:] == '.bz2'):
            if(bz2Support):
                changesetFile = BZ2File(args.fileName)
            else:
                print 'ERROR: bzip2 support not available. Unzip file first or install bz2file'
                sys.exit(1)
        else:
            changesetFile = open(args.fileName, 'rb')

        if(changesetFile != None):
            md.parseFile(conn, changesetFile)
        else:
            print 'ERROR: no changeset file opened. Something went wrong in processing args'
            sys.exist(1)

        cursor = conn.cursor()
        print 'creating constraints'
        cursor.execute(queries.createConstraints)
        print 'creating indexes'
        cursor.execute(queries.createIndexes)
        if args.createGeometry:
            cursor.execute(queries.createGeomIndex)
        conn.commit()

        conn.close()

    endTime = datetime.now()
    timeCost = endTime - beginTime

    print 'Processing time cost is ', timeCost

    print 'All done. Enjoy your (meta)data!'
