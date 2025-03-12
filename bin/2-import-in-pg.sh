#!/bin/bash
set -e

# Check if PostgreSQL is running
echo "Checking if PostgreSQL is running..."
if ! pg_isready > /dev/null 2>&1; then
    echo "Error: PostgreSQL is not running. Please start PostgreSQL first."
    echo "On macOS with Homebrew: brew services start postgresql@14"
    echo "On Linux: sudo systemctl start postgresql"
    echo "On Windows: Start the PostgreSQL service from Services or the PostgreSQL application"
    exit 1
fi
echo "PostgreSQL is running."

# Create a database if it doesn't exist
DB_NAME="reverse_geo"

# Check if database exists
if ! psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo "Creating database $DB_NAME..."
    createdb $DB_NAME
    echo "Enabling PostGIS extension..."
    psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS postgis;"
    psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS hstore;"
else
    echo "Database $DB_NAME already exists."
fi

# Check if PostGIS extension is enabled
if ! psql -d $DB_NAME -c "SELECT postgis_version();" > /dev/null 2>&1; then
    echo "Enabling PostGIS extension..."
    psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS postgis;"
    psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS hstore;"
fi

# Check if the input file exists
if [ ! -f "data/admin-boundaries.osm.pbf" ]; then
    echo "Error: Input file data/admin-boundaries.osm.pbf not found."
    echo "Please run ./bin/filter-boundaries.sh first to extract administrative boundaries."
    exit 1
fi

# Check if the Lua configuration file exists
if [ ! -f "bin/2-admin-boundaries.lua" ]; then
    echo "Error: Lua configuration file bin/2-admin-boundaries.lua not found."
    echo "Please make sure the Lua configuration file exists."
    exit 1
fi

# Import the data using osm2pgsql with the flex output
echo "Importing administrative boundaries into PostgreSQL..."
osm2pgsql \
    --database $DB_NAME \
    --output flex \
    --style bin/2-admin-boundaries.lua \
    --hstore-all \
    --keep-coastlines \
    --slim \
    data/admin-boundaries.osm.pbf

echo "Creating indexes for better query performance..."
psql -d $DB_NAME -c "CREATE INDEX IF NOT EXISTS boundaries_admin_level_idx ON boundaries (admin_level);"
psql -d $DB_NAME -c "CREATE INDEX IF NOT EXISTS boundaries_name_idx ON boundaries (name);"
psql -d $DB_NAME -c "CREATE INDEX IF NOT EXISTS boundaries_geom_idx ON boundaries USING GIST (geom);"

echo "Import completed successfully!"
echo "You can now query administrative boundaries from the 'boundaries' table in the '$DB_NAME' database." 