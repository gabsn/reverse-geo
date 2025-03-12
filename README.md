# Reverse Geocoding Application

A TypeScript application for reverse geocoding using OpenStreetMap data.

## Overview

This project provides functionality to convert geographic coordinates (latitude, longitude) into human-readable addresses using OpenStreetMap data. It uses filtered OSM data containing country boundaries.

## Data Preparation

The application uses filtered OpenStreetMap data. The data preparation process involves:

1. Downloading the planet.osm.pbf file (approximately 72GB)
2. Filtering the data to extract country boundaries using osmium:

```bash
osmium tags-filter data/planet.osm.pbf --output=data/countries.osm.pbf nwr/admin_level=2
```

This command extracts all nodes, ways, and relations with the tag `admin_level=2`, which represents country boundaries in OpenStreetMap.

## Current Implementation

The current implementation uses a simplified approach with predefined country data for testing purposes. It includes bounding boxes for several major countries:

- France
- Germany
- United Kingdom
- United States
- Canada
- Australia
- Japan
- Brazil

The API uses these predefined boundaries to determine which country a given set of coordinates belongs to.

## Project Setup

### Prerequisites

- Node.js (v14 or later)
- npm
- TypeScript
- osmium command-line tool (for data preparation)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/reverse-geo.git
cd reverse-geo
```

2. Install dependencies:

```bash
npm install
```

### Development

- Run the development server:

```bash
npm run dev
```

- Build the project:

```bash
npm run build
```

- Run the built project:

```bash
npm start
```

- Run the API server:

```bash
npm run api
```

## API Usage

The application provides a REST API for reverse geocoding. The API runs on port 8080 by default.

### Endpoints

#### Get Country by Coordinates

```
GET /api/country?lat={latitude}&lon={longitude}
```

Parameters:

- `lat`: Latitude (between -90 and 90)
- `lon`: Longitude (between -180 and 180)

Example:

```
GET /api/country?lat=48.8566&lon=2.3522
```

Response:

```json
{
  "coordinates": {
    "latitude": 48.8566,
    "longitude": 2.3522
  },
  "country": {
    "name": "France",
    "code": "FR",
    "continent": "Europe",
    "population": 67000000
  }
}
```

If no country is found for the given coordinates, the API returns a 404 response:

```json
{
  "coordinates": {
    "latitude": 0,
    "longitude": 0
  },
  "error": "No country found for the given coordinates"
}
```

## Future Improvements

1. **Use actual OSM data**: Replace the predefined country data with actual OSM data from the filtered countries.osm.pbf file.
2. **Add more detailed geocoding**: Extend the API to provide more detailed information such as cities, addresses, and postal codes.
3. **Improve performance**: Implement spatial indexing to speed up the reverse geocoding process.
4. **Add caching**: Implement caching to improve response times for frequently requested coordinates.

## Project Structure

```
reverse-geo/
├── data/                  # Directory for OSM data files
│   ├── planet.osm.pbf     # Original OSM planet file
│   └── countries.osm.pbf  # Filtered country boundaries
├── src/                   # TypeScript source files
│   ├── api/               # API server code
│   │   ├── server.ts      # API server entry point
│   ├── utils/             # Utility functions
│   │   ├── geoUtils.ts    # Geocoding utilities
│   │   └── osmData.ts     # OSM data utilities
│   └── index.ts           # Main entry point
├── dist/                  # Compiled JavaScript files
├── package.json           # Project configuration
├── tsconfig.json          # TypeScript configuration
└── README.md              # Project documentation
```

## License

ISC
