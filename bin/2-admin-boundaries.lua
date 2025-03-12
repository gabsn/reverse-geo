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
        -- Try to convert to multipolygon
        local geom = object:as_multipolygon()
        
        -- If geometry is NULL, print a warning
        if geom == nil then
            print(string.format("WARNING: Failed to create geometry for relation %d (name: %s, admin_level: %s)",
                  object.id, object.tags.name or 'unnamed', object.tags.admin_level or 'unknown'))
        end
        
        -- Insert the relation even if geometry is NULL (for debugging)
        tables.boundaries:insert({
            osm_id = object.id,
            admin_level = tonumber(object.tags.admin_level),
            name = object.tags.name,
            tags = object.tags,
            geom = geom
        })
    end
end

-- We don't need to process nodes for administrative boundaries
function osm2pgsql.process_node(object)
    -- Administrative boundaries are relations, so we don't process nodes
end

function osm2pgsql.process_way(object)
    -- We could process ways tagged as boundary=administrative as a fallback
    -- This would help with simpler boundaries that are represented as ways
    if object.tags.boundary == 'administrative' and object.tags.admin_level and object.is_closed then
        local name = object.tags.name
        local admin_level = tonumber(object.tags.admin_level)
        
        -- Only process ways that form closed polygons and have admin_level
        if name and admin_level then
            print(string.format("Processing way %d as boundary: %s (admin_level: %s)",
                  object.id, name, object.tags.admin_level))
            
            tables.boundaries:insert({
                osm_id = object.id,
                admin_level = admin_level,
                name = name,
                tags = object.tags,
                geom = object:as_polygon()
            })
        end
    end
end 