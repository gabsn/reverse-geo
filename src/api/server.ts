/**
 * API Server for Reverse Geocoding
 */

import express, { Request, Response } from "express";
import cors from "cors";
import { checkOsmDataFiles } from "../utils/osmData";
import { Coordinates } from "../index";
import { GeocodingService, CountryInfo } from "../utils/geoUtils";

// Check if the required OSM data files exist
const dataFilesExist = checkOsmDataFiles();
if (!dataFilesExist) {
  console.error(
    "Required OSM data files are missing. Please check the README for data preparation instructions."
  );
  process.exit(1);
}

// Create Express app
const app = express();
const PORT = process.env.PORT || 8080;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize the geocoding service
const geocodingService = new GeocodingService();

// Initialize the geocoding service before starting the server
async function initializeGeocodingService() {
  try {
    console.log("Loading GeoJSON data...");
    await geocodingService.loadData();
    console.log("GeoJSON data loaded successfully");

    // Start the server after data is loaded
    startServer();
  } catch (error) {
    console.error("Failed to load GeoJSON data:", error);
    process.exit(1);
  }
}

/**
 * Get country information by coordinates
 */
function getCountryByCoordinates(req: Request, res: Response): void {
  try {
    // Get latitude and longitude from query parameters
    const lat = parseFloat(req.query.lat as string);
    const lon = parseFloat(req.query.lon as string);

    // Validate coordinates
    if (isNaN(lat) || isNaN(lon)) {
      res.status(400).json({
        error:
          "Invalid coordinates. Please provide valid lat and lon query parameters.",
      });
      return;
    }

    // Check if coordinates are within valid range
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      res.status(400).json({
        error:
          "Coordinates out of range. Latitude must be between -90 and 90, longitude between -180 and 180.",
      });
      return;
    }

    // Create coordinates object
    const coordinates: Coordinates = {
      latitude: lat,
      longitude: lon,
    };

    // Get country information using the geocoding service
    const countryInfo = geocodingService.getCountryByCoordinates(coordinates);

    if (countryInfo) {
      // Return country information
      res.json({
        coordinates,
        country: countryInfo,
      });
    } else {
      // No country found for the given coordinates
      res.status(404).json({
        coordinates,
        error: "No country found for the given coordinates",
      });
    }
  } catch (error) {
    console.error("Error in getCountryByCoordinates:", error);
    res.status(500).json({
      error: "Internal server error",
    });
  }
}

// Country endpoint
app.get("/api/country", getCountryByCoordinates);

// Root route
app.get("/", (req: Request, res: Response) => {
  res.json({
    message: "Reverse Geocoding API",
    endpoints: {
      country: "/api/country?lat=48.8566&lon=2.3522",
    },
  });
});

// Start the server
function startServer() {
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
    console.log(`API available at http://localhost:${PORT}`);
    console.log("Available endpoints:");
    console.log("- GET /api/country?lat=48.8566&lon=2.3522");
  });
}

// Initialize the geocoding service and start the server
initializeGeocodingService();
