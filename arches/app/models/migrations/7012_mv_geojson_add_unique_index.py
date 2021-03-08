from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("models", "5605_searchexporthistory_downloadfile")]

    operations = [
        migrations.RunSQL(
            #forward
            """
            DROP MATERIALIZED VIEW mv_geojson_geoms;
            CREATE MATERIALIZED VIEW mv_geojson_geoms AS
                SELECT public.uuid_generate_v1mc() AS uid,
                    t.tileid,
                    t.resourceinstanceid,
                    n.nodeid,
                    ST_Transform(ST_SetSRID(
                    st_geomfromgeojson(
                        (
                            json_array_elements(
                                t.tiledata::json ->
                                n.nodeid::text ->
                            'features') -> 'geometry'
                        )::text
                    ),
                    4326
                ), 3857) AS geom
                FROM tiles t
                LEFT JOIN nodes n ON t.nodegroupid = n.nodegroupid
                WHERE n.datatype = 'geojson-feature-collection'::text;

            CREATE UNIQUE INDEX ON mv_geojson_geoms (uid);
            CREATE INDEX mv_geojson_geoms_gix ON mv_geojson_geoms USING GIST (geom);
            """,
            #reverse
            """
            DROP MATERIALIZED VIEW mv_geojson_geoms;
            CREATE MATERIALIZED VIEW mv_geojson_geoms AS
                SELECT t.tileid,
                    t.resourceinstanceid,
                    n.nodeid,
                    ST_Transform(ST_SetSRID(
                       st_geomfromgeojson(
                           (
                               json_array_elements(
                                   t.tiledata::json ->
                                   n.nodeid::text ->
                               'features') -> 'geometry'
                           )::text
                       ),
                       4326
                   ), 3857) AS geom
                FROM tiles t
                LEFT JOIN nodes n ON t.nodegroupid = n.nodegroupid
                WHERE n.datatype = 'geojson-feature-collection'::text;

            CREATE INDEX mv_geojson_geoms_gix ON mv_geojson_geoms USING GIST (geom);
            """
        )
    ]
