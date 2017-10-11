'''
Just a utility file to store some SQL queries for easy reference

@author: Toby Murray
'''
createNoteTable = '''CREATE EXTENSION IF NOT EXISTS hstore;
  CREATE TABLE note (
  id bigint,
  created_at timestamp without time zone,
  closed_at timestamp without time zone,  
  lat numeric(10,7),
  lon numeric(10,7)
);
CREATE TABLE note_comment (
  comment_note_id bigint not null,
  comment_action text not null,
  comment_date timestamp without time zone not null,
  comment_user_id bigint,
  comment_user_name varchar(255),
  comment_text text
);
'''

dropIndexes = '''ALTER TABLE note DROP CONSTRAINT IF EXISTS note_pkey CASCADE;
DROP INDEX IF EXISTS created_idx, closed_idx, note_geom_gist ;
'''

createConstraints = '''ALTER TABLE note ADD CONSTRAINT note_pkey PRIMARY KEY(id);'''

createIndexes = '''CREATE INDEX created_idx ON note(created_at);
CREATE INDEX closed_idx ON note(closed_at);
'''

createGeometryColumn = '''
CREATE EXTENSION IF NOT EXISTS postgis;
SELECT AddGeometryColumn('note','geom', 4326, 'POINT', 2);
'''

createGeomIndex = '''
CREATE INDEX note_geom_gist ON note USING GIST(geom);
'''
