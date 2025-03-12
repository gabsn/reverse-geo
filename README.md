# Reverse Geo

A tool for reverse geocoding using OpenStreetMap data.

## Project Setup

### Step 1: Extract Administrative Boundaries

The first step in setting up this project is to extract administrative boundaries from an OpenStreetMap data file (PBF format).

#### Prerequisites

- [Osmium Tool](https://osmcode.org/osmium-tool/) must be installed on your system
- You need an OpenStreetMap data file (e.g., `planet.osm.pbf` or a regional extract)

#### Extracting Administrative Boundaries

We use the `bin/filter-boundaries.sh` script to filter only the administrative boundaries from the OpenStreetMap data file and save them to a separate PBF file.

1. Place your OpenStreetMap data file in the `data/` directory with the name `planet.osm.pbf`
2. Run the filter script:

```bash
./bin/filter-boundaries.sh
```

This script uses Osmium's tag filtering functionality to extract only the elements with the tag `boundary=administrative` and saves them to `data/admin-boundaries.osm.pbf`.

The script contains the following command:

```bash
osmium tags-filter \
    data/planet.osm.pbf \
    r/boundary=administrative \
    -o data/admin-boundaries.osm.pbf
```

This significantly reduces the file size by keeping only the administrative boundary relations that are needed for geocoding.

### Step 2: Import Administrative Boundaries into PostgreSQL

After extracting the administrative boundaries, the next step is to import them into a PostgreSQL database for efficient querying and geocoding.

#### Prerequisites

- [PostgreSQL](https://www.postgresql.org/) with [PostGIS](https://postgis.net/) extension installed
- [osm2pgsql](https://osm2pgsql.org/) installed (version 1.8.0 or later recommended for flex output support)

#### Setting Up PostgreSQL

Before running the import script, you need to make sure PostgreSQL is running:

**macOS (with Homebrew):**

```bash
# Start PostgreSQL service
brew services start postgresql@14  # Replace 14 with your PostgreSQL version

# Verify PostgreSQL is running
psql -c "SELECT version();"
```

**Linux (Ubuntu/Debian):**

```bash
# Start PostgreSQL service
sudo systemctl start postgresql

# Verify PostgreSQL is running
sudo -u postgres psql -c "SELECT version();"
```

**Windows:**

```bash
# PostgreSQL should be running as a service
# You can check in Services or start it from the PostgreSQL application
```

If you encounter connection issues, make sure:

1. PostgreSQL service is running
2. Your user has permission to connect to the database
3. PostgreSQL is configured to accept local connections

#### Importing the Data

We use the `bin/2-import-in-pg.sh` script to import the administrative boundaries into PostgreSQL.

1. Ensure PostgreSQL is running (see above)
2. Run the import script:

```bash
./bin/2-import-in-pg.sh
```

This script:

1. Creates a database named `reverse_geo` if it doesn't exist
2. Enables the PostGIS and hstore extensions
3. Creates a Lua configuration file for osm2pgsql that defines how to import the data
4. Imports the administrative boundaries using osm2pgsql's flex output
5. Creates indexes for better query performance

The imported data will be available in the `boundaries` table with the following columns:

- `osm_id`: The OpenStreetMap ID of the boundary
- `admin_level`: The administrative level (1-10, where lower numbers are larger areas)
- `name`: The name of the administrative area
- `tags`: All tags associated with the boundary in JSONB format
- `geom`: The geometry of the boundary as a multipolygon in WGS84 (EPSG:4326)

#### Next Steps

After importing the administrative boundaries into PostgreSQL, you'll be ready to proceed with the next steps of the project setup (to be documented).
