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

#### Next Steps

After extracting the administrative boundaries, you'll be ready to proceed with the next steps of the project setup (to be documented).
