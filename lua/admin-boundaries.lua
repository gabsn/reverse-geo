-- Admin boundaries flex output for osm2pgsql
-- This script properly handles administrative boundaries including relations
-- and tracks the hierarchy between different admin levels (city, state, country)

local tables = {}

-- Define a table for administrative boundaries
tables.boundaries = osm2pgsql.define_area_table('boundaries', {
    { column = 'osm_id',      type = 'bigint' },
    { column = 'osm_type',    type = 'text' },
    { column = 'admin_level', type = 'smallint' },
    { column = 'name',        type = 'text' },
    { column = 'name_en',     type = 'text' },  -- English name for international use
    { column = 'boundary',    type = 'text' },  -- Type of boundary
    { column = 'tags',        type = 'jsonb' }, -- All other tags
    { column = 'geom',        type = 'multipolygon', projection = 4326 },
})

-- Define a table for relation hierarchy
tables.admin_hierarchy = osm2pgsql.define_table('admin_hierarchy', {
    { column = 'parent_id',     type = 'bigint' },
    { column = 'parent_type',   type = 'text' },
    { column = 'parent_level',  type = 'smallint' },
    { column = 'parent_name',   type = 'text' },
    { column = 'child_id',      type = 'bigint' },
    { column = 'child_type',    type = 'text' },
    { column = 'child_level',   type = 'smallint' },
    { column = 'child_name',    type = 'text' },
    { column = 'role',          type = 'text' },
})

-- Define a table for places (cities, towns, etc.)
tables.places = osm2pgsql.define_node_table('places', {
    { column = 'osm_id',      type = 'bigint' },
    { column = 'place',       type = 'text' },
    { column = 'name',        type = 'text' },
    { column = 'name_en',     type = 'text' },
    { column = 'population',  type = 'integer' },
    { column = 'tags',        type = 'jsonb' },
    { column = 'geom',        type = 'point', projection = 4326 },
})

-- Special handling for the United States relation (id=148838)
-- This ensures we properly capture the US boundary and its states
local us_relation_id = 148838

-- Process relations with boundary=administrative
function osm2pgsql.process_relation(object)
    if object.tags.boundary == 'administrative' then
        local admin_level = tonumber(object.tags.admin_level) or 0
        
        -- Special handling for the US relation
        local is_us = (object.id == us_relation_id)
        if is_us then
            print("Processing United States relation (id=" .. us_relation_id .. ")")
        end
        
        -- Store the relation boundary
        tables.boundaries:insert({
            osm_id      = object.id,
            osm_type    = 'R',
            admin_level = admin_level,
            name        = object.tags.name,
            name_en     = object.tags['name:en'],
            boundary    = object.tags.boundary,
            tags        = object.tags,
            geom        = object:as_multipolygon()
        })
        
        -- Process relation members to build hierarchy
        for _, member in ipairs(object.members) do
            -- Handle relation members (sub-relations)
            if member.type == 'r' and member.ref > 0 then
                tables.admin_hierarchy:insert({
                    parent_id    = object.id,
                    parent_type  = 'R',
                    parent_level = admin_level,
                    parent_name  = object.tags.name,
                    child_id     = member.ref,
                    child_type   = 'R',
                    child_level  = 0, -- Will be updated later
                    child_name   = '',
                    role         = member.role,
                })
                
                -- Special handling for US states
                if is_us and member.role == 'subarea' then
                    print("Found US state relation: " .. member.ref)
                end
            end
            
            -- Handle way members (boundary segments)
            elseif member.type == 'w' and member.ref > 0 then
                tables.admin_hierarchy:insert({
                    parent_id    = object.id,
                    parent_type  = 'R',
                    parent_level = admin_level,
                    parent_name  = object.tags.name,
                    child_id     = member.ref,
                    child_type   = 'W',
                    child_level  = 0,
                    child_name   = '',
                    role         = member.role,
                })
            end
            
            -- Handle node members (cities, towns, etc.)
            elseif member.type == 'n' and member.ref > 0 then
                tables.admin_hierarchy:insert({
                    parent_id    = object.id,
                    parent_type  = 'R',
                    parent_level = admin_level,
                    parent_name  = object.tags.name,
                    child_id     = member.ref,
                    child_type   = 'N',
                    child_level  = 0,
                    child_name   = '',
                    role         = member.role,
                })
            end
        end
    end
end

-- Process ways with boundary=administrative
function osm2pgsql.process_way(object)
    if object.tags.boundary == 'administrative' then
        local admin_level = tonumber(object.tags.admin_level) or 0
        
        tables.boundaries:insert({
            osm_id      = object.id,
            osm_type    = 'W',
            admin_level = admin_level,
            name        = object.tags.name,
            name_en     = object.tags['name:en'],
            boundary    = object.tags.boundary,
            tags        = object.tags,
            geom        = object:as_multipolygon()
        })
    end
end

-- Process nodes with place tags (cities, towns, etc.)
function osm2pgsql.process_node(object)
    if object.tags.place then
        -- Convert population to number if available
        local population = nil
        if object.tags.population then
            population = tonumber(object.tags.population)
        end
        
        tables.places:insert({
            osm_id      = object.id,
            place       = object.tags.place,
            name        = object.tags.name,
            name_en     = object.tags['name:en'],
            population  = population,
            tags        = object.tags,
            geom        = object:as_point()
        })
    end
end

-- Create a function to find the containing admin boundaries for places
function osm2pgsql.process_stage1()
    -- Create a spatial index on places
    print("Creating spatial index on places...")
    osm2pgsql.run_sql([[
        CREATE INDEX IF NOT EXISTS places_geom_idx ON places USING GIST (geom);
    ]])
    
    -- Create a spatial index on boundaries
    print("Creating spatial index on boundaries...")
    osm2pgsql.run_sql([[
        CREATE INDEX IF NOT EXISTS boundaries_geom_idx ON boundaries USING GIST (geom);
    ]])
    
    -- Find containing admin boundaries for each place
    print("Finding containing admin boundaries for places...")
    osm2pgsql.run_sql([[
        INSERT INTO admin_hierarchy (
            parent_id, parent_type, parent_level, parent_name,
            child_id, child_type, child_level, child_name, role
        )
        SELECT 
            b.osm_id, b.osm_type, b.admin_level, b.name,
            p.osm_id, 'N', 0, p.name, 'contains'
        FROM 
            boundaries b,
            places p
        WHERE 
            ST_Contains(b.geom, p.geom)
            AND NOT EXISTS (
                SELECT 1 FROM admin_hierarchy 
                WHERE parent_id = b.osm_id AND parent_type = b.osm_type 
                AND child_id = p.osm_id AND child_type = 'N'
            );
    ]])
    
    -- Update child levels and names in the hierarchy table
    print("Updating child information in hierarchy...")
    osm2pgsql.run_sql([[
        UPDATE admin_hierarchy h
        SET 
            child_level = b.admin_level,
            child_name = b.name
        FROM 
            boundaries b
        WHERE 
            h.child_id = b.osm_id AND h.child_type = b.osm_type;
    ]])
    
    -- Create a view for easier reverse geocoding
    print("Creating reverse geocode view...")
    osm2pgsql.run_sql([[
        CREATE OR REPLACE VIEW reverse_geocode_view AS
        SELECT 
            b.osm_id,
            b.osm_type,
            b.name,
            b.name_en,
            b.admin_level,
            parent.osm_id AS parent_id,
            parent.osm_type AS parent_type,
            parent.name AS parent_name,
            parent.name_en AS parent_name_en,
            parent.admin_level AS parent_level,
            b.geom
        FROM 
            boundaries b
        LEFT JOIN admin_hierarchy h ON b.osm_id = h.child_id AND b.osm_type = h.child_type
        LEFT JOIN boundaries parent ON h.parent_id = parent.osm_id AND h.parent_type = parent.osm_type
        WHERE 
            b.admin_level IS NOT NULL;
    ]])
    
    -- Create a view for place hierarchy (city -> state -> country)
    print("Creating place hierarchy view...")
    osm2pgsql.run_sql([[
        CREATE OR REPLACE VIEW place_hierarchy AS
        WITH RECURSIVE hierarchy AS (
            -- Start with places (cities, towns, etc.)
            SELECT 
                p.osm_id AS place_id,
                p.name AS place_name,
                p.name_en AS place_name_en,
                p.place AS place_type,
                NULL::bigint AS state_id,
                NULL::text AS state_name,
                NULL::text AS state_name_en,
                NULL::bigint AS country_id,
                NULL::text AS country_name,
                NULL::text AS country_name_en,
                p.geom
            FROM 
                places p
            
            UNION ALL
            
            -- Find containing admin boundaries
            SELECT 
                h.place_id,
                h.place_name,
                h.place_name_en,
                h.place_type,
                CASE WHEN b.admin_level = 4 THEN b.osm_id ELSE h.state_id END AS state_id,
                CASE WHEN b.admin_level = 4 THEN b.name ELSE h.state_name END AS state_name,
                CASE WHEN b.admin_level = 4 THEN b.name_en ELSE h.state_name_en END AS state_name_en,
                CASE WHEN b.admin_level = 2 THEN b.osm_id ELSE h.country_id END AS country_id,
                CASE WHEN b.admin_level = 2 THEN b.name ELSE h.country_name END AS country_name,
                CASE WHEN b.admin_level = 2 THEN b.name_en ELSE h.country_name_en END AS country_name_en,
                h.geom
            FROM 
                hierarchy h
            JOIN 
                admin_hierarchy ah ON ah.child_id = 
                    CASE 
                        WHEN h.country_id IS NOT NULL THEN h.country_id
                        WHEN h.state_id IS NOT NULL THEN h.state_id
                        ELSE h.place_id
                    END
                AND ah.child_type = 
                    CASE 
                        WHEN h.country_id IS NOT NULL THEN 'R'
                        WHEN h.state_id IS NOT NULL THEN 'R'
                        ELSE 'N'
                    END
            JOIN 
                boundaries b ON b.osm_id = ah.parent_id AND b.osm_type = ah.parent_type
            WHERE 
                (h.country_id IS NULL OR h.state_id IS NULL)
                AND b.admin_level IN (2, 4)
        )
        SELECT DISTINCT ON (place_id)
            place_id, place_name, place_name_en, place_type,
            state_id, state_name, state_name_en,
            country_id, country_name, country_name_en,
            geom
        FROM 
            hierarchy
        WHERE 
            country_id IS NOT NULL OR state_id IS NOT NULL
        ORDER BY 
            place_id, 
            CASE WHEN country_id IS NOT NULL AND state_id IS NOT NULL THEN 1 ELSE 2 END;
    ]])
    
    print("Processing complete!")
end 