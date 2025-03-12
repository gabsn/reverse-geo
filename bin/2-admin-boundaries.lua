-- Configuration for importing administrative boundaries

local tables = {}

-- Define a table for administrative boundaries
tables.boundaries = osm2pgsql.define_area_table('boundaries', {
    { column = 'osm_id', type = 'bigint' },
    { column = 'admin_level', type = 'smallint' },
    { column = 'name', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'multipolygon', projection = 4326 },
})

-- Process relations with boundary=administrative tag
function osm2pgsql.process_relation(object)
    if object.tags.boundary == 'administrative' then
        tables.boundaries:insert({
            osm_id = object.id,
            admin_level = tonumber(object.tags.admin_level),
            name = object.tags.name,
            tags = object.tags,
            geom = object:as_multipolygon()
        })
    end
end

-- We don't need to process nodes or ways for administrative boundaries
function osm2pgsql.process_node(object)
    -- Administrative boundaries are relations, so we don't process nodes
end

function osm2pgsql.process_way(object)
    -- Administrative boundaries are relations, so we don't process ways
end 