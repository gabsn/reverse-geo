# Reverse Geo

A tool for reverse geocoding using OpenStreetMap data.

## Project Setup

### Step 0: PostgreSQL Setup and Control

This project provides a convenient script to manage your PostgreSQL server with optimized settings:

```bash
# Start PostgreSQL with optimized configuration
./bin/pg.sh start

# Check PostgreSQL status
./bin/pg.sh status

# Stop PostgreSQL
./bin/pg.sh stop

# Restart PostgreSQL with optimized configuration
./bin/pg.sh restart
```

The script automatically:

- Detects your PostgreSQL installation (Homebrew on macOS or systemd on Linux)
- Applies the optimized configuration settings (if not already applied)
- Creates the `reverse_geo` database if it doesn't exist
- Enables the PostGIS and hstore extensions in the database
- Manages the PostgreSQL service

This is the recommended way to start and stop PostgreSQL for this project, as it ensures the performance optimizations are applied and the database is properly set up.

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

Before running the import script, you need to make sure PostgreSQL is running with the required database and extensions:

```bash
# Start PostgreSQL with optimized configuration and set up the database
./bin/pg.sh start
```

This command will:

1. Start PostgreSQL with optimized settings
2. Create the `reverse_geo` database if it doesn't exist
3. Enable the PostGIS and hstore extensions

Alternatively, you can start PostgreSQL using your system's native commands and set up the database manually:

**macOS (with Homebrew):**

```bash
# Start PostgreSQL service
brew services start postgresql@14  # Replace 14 with your PostgreSQL version

# Verify PostgreSQL is running
psql -c "SELECT version();"

# Create database and enable extensions
createdb reverse_geo
psql -d reverse_geo -c "CREATE EXTENSION postgis;"
psql -d reverse_geo -c "CREATE EXTENSION hstore;"
```

**Linux (Ubuntu/Debian):**

```

```

### Step 3: Reverse Geocoding

After importing the administrative boundaries into PostgreSQL, you can use the reverse geocoding script to find the city, state, and country for any latitude and longitude coordinates.

#### Prerequisites

- Python 3.6 or later
- `psycopg2` Python package (install with `pip install psycopg2-binary`)

#### Usage

The script takes latitude and longitude coordinates as input and returns the corresponding city, state, and country information.

```bash
./bin/3-reverse-geocoding.py --lat <latitude> --lon <longitude> [--format <format>] [--debug]
```

Options:

- `--lat`: Latitude in decimal degrees (required)
- `--lon`: Longitude in decimal degrees (required)
- `--format`: Output format, either `text` (default) or `json`
- `--debug`: Print debug information

#### Examples

**Example 1: San Francisco, CA, USA**

```bash
./bin/3-reverse-geocoding.py --lat 37.7749 --lon -122.4194
```

Output:

```
Coordinates: 37.7749, -122.4194
City: San Francisco
  (Note: City is approximate, nearest match)
State/Region: California
Country: United States of America
  (Note: Country is approximate, derived from state)
```

**Example 2: Paris, France (with JSON output)**

```bash
./bin/3-reverse-geocoding.py --lat 48.8566 --lon 2.3522 --format json
```

Output:

```json
{
  "city": "Paris",
  "state": "Ile-de-France",
  "country": "France",
  "lat": 48.8566,
  "lon": 2.3522
}
```

**Example 3: Tokyo, Japan**

```bash
./bin/3-reverse-geocoding.py --lat 35.6762 --lon 139.6503
```

Output:

```
Coordinates: 35.6762, 139.6503
City: Tokyo
State/Region: Tokyo
Country: Japan
```

**Example 4: Debugging Mode**

For troubleshooting or to see more details about the matching boundaries:

```bash
./bin/3-reverse-geocoding.py --lat 37.7749 --lon -122.4194 --debug
```

This will show additional information such as:

- Database structure
- Number of matching boundaries
- All administrative boundaries containing the point
- Fallback mechanisms used (if any)

#### Database Connection

By default, the script connects to the PostgreSQL database using the current system username. You can customize the connection parameters using environment variables:

```bash
PGDATABASE=reverse_geo PGUSER=your_username PGPASSWORD=your_password ./bin/3-reverse-geocoding.py --lat 37.7749 --lon -122.4194
```

Available environment variables:

- `PGDATABASE`: Database name (default: `reverse_geo`)
- `PGUSER`: Database user (default: current system user)
- `PGPASSWORD`: Database password (default: empty)
- `PGHOST`: Database host (default: `localhost`)
- `PGPORT`: Database port (default: `5432`)
