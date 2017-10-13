NoteMD
=========

NoteMD is a simple XML parser written in python that takes the daily note dump file from http://planet.openstreetmap.org/ and shoves the data into a simple postgres database so it can be queried.

It's a modification of the ChangesetMD utility.


Setup
------------

NoteMD works with python 2.7.

Aside from postgresql, NoteMD depends on the python libraries psycopg2 and lxml.
On Debian-based systems this means installing the python-psycopg2 and python-lxml packages.

If you want to parse the notes file without first unzipping it, you will also need to install the [bz2file library](http://pypi.python.org/pypi/bz2file) since the built in bz2 library can not handle multi-stream bzip files.

For building geometries, ```postgis``` extension needs to be [installed](http://postgis.net/install).

NoteMD expects a postgres database to be set up for it. It can likely co-exist within another database if desired. Otherwise, As the postgres user execute:

    createdb notes

It is easiest if your OS user has access to this database. I just created a user and made myself a superuser. Probably not best practices.

    createuser <username>


Execution
------------
The first time you run it, you will need to include the -c | --create option to create the table:

    python notemd.py -d <database> -c

The create function can be combined with the file option to immediately parse a file.

To parse a dump file, use the -f | --file option.

    python notemd.py -d <database> -f /tmp/planet-notes-latest.osn

If no other arguments are given, it will access postgres using the default settings of the postgres client, typically connecting on the unix socket as the current OS user. Use the ```--help``` argument to see optional arguments for connecting to postgres.

You can add the `-g` | `--geometry` option to build point geometries (the database also needs to be created with this option).

Replication
------------
**TODO.**
As of now (2017-10-13) there are no replication files for OSM notes. However 1) the dumps are created daily and loading them is fast 2) it's possible to use one of the RSS feeds to get URLs of notes to update.
While the feed presents only notes from last 2 hours or so, any updates missed due to downtime could be corrected as soon as new notes dump is available.

Notes
------------
- Prints a status message every 10,000 records.
- Takes less than 10 minutes to import the current dump on a decent home computer.
- Might be faster to process the XML into a flat file and then use the postgres COPY command to do a bulk load but this would make incremental updates a little harder
- I have commonly queried fields indexed. Depending on what you want to do, you may need more indexes.

Table Structure
------------
NoteMD populates two tables with the following structure:

note:
Primary table of all notes with the following columns:
- `id`: note ID
- `created_at/closed_at`: create/closed time. `closed_at` is NULL for notes that are open. 
- `lat/lon` note coordinates in decimal degrees
- `geom`: [optional] a postgis geometry column of `Polygon` type (SRID: 4326)

Only closed\_at can be null.

note_comment:
All comments and actions made on notes
- `comment_note_id`: Foreign key to the note ID
- `comment_action`: one of:  `opened`, `commented`, `closed`, `reopened`, `hidden`. There is only one `opened` action per `comment_note_id` and it contains the initial note text.
- `comment_date`: timestamp of when the comment was created
- `comment_user_id`: numeric OSM user ID or `NULL` if the comment was sent anonymously
- `comment_user_name`: OSM username or `NULL` if the comment was sent anonymously



Example queries
------------
Count how many notes are open:

    SELECT COUNT(*)
    FROM note
    WHERE closed_at IS NULL;

Find all notes that were created by user scout_osm:

    SELECT COUNT(*)
    FROM note_comment
    WHERE comment_action = 'opened' and comment_user_name = 'scout_osm';

Find all notes that were created in Liberty Island:

    SELECT count(id)
    FROM note c, (SELECT ST_SetSRID(ST_MakeEnvelope(-74.0474545,40.6884971,-74.0433990,40.6911817),4326) AS geom) s
    WHERE ST_CoveredBy(c.geom, s.geom);

License
------------
Copyright (C) 2017 Michał Brzozowski (C) 2012  Toby Murray

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  

See the GNU Affero General Public License for more details: http://www.gnu.org/licenses/agpl.txt
