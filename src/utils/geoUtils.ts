/**
 * Utility functions for working with OSM data and performing reverse geocoding
 */

import * as fs from "fs";
import * as path from "path";
import * as turf from "@turf/turf";
import { Coordinates } from "../index";
import {
  Feature,
  FeatureCollection,
  Geometry,
  Point,
  Polygon,
  MultiPolygon,
} from "geojson";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

/**
 * Configuration for OSM data paths
 */
export const GEO_CONFIG = {
  dataDir: path.resolve(__dirname, "../../data"),
  countriesFile: path.resolve(__dirname, "../../data/countries.osm.pbf"),
  // Use a smaller subset of the data for testing
  testDataDir: path.resolve(__dirname, "../../data/test"),
};

/**
 * Country information
 */
export interface CountryInfo {
  name: string;
  code?: string;
  continent?: string;
  population?: number;
}

/**
 * Class for performing reverse geocoding using OSM data
 */
export class GeocodingService {
  private isLoaded = false;
  private countryBoundaries: Map<string, any> = new Map();

  /**
   * Load the OSM data
   * @returns Promise that resolves when the data is loaded
   */
  async loadData(): Promise<void> {
    if (this.isLoaded) {
      return;
    }

    try {
      // Check if the OSM file exists
      if (!fs.existsSync(GEO_CONFIG.countriesFile)) {
        throw new Error(
          `Countries OSM file not found: ${GEO_CONFIG.countriesFile}`
        );
      }

      // Create test directory if it doesn't exist
      if (!fs.existsSync(GEO_CONFIG.testDataDir)) {
        fs.mkdirSync(GEO_CONFIG.testDataDir, { recursive: true });
      }

      // Extract a few countries for testing
      await this.extractTestCountries();

      // For now, we'll use a simple approach with predefined country data
      this.loadPredefinedCountries();

      this.isLoaded = true;
      console.log("Country data loaded successfully");
    } catch (error) {
      console.error("Error loading OSM data:", error);
      throw error;
    }
  }

  /**
   * Extract test countries from the OSM file
   */
  private async extractTestCountries(): Promise<void> {
    try {
      // We'll skip the actual extraction for now and use predefined data
      console.log("Using predefined country data for testing");
    } catch (error) {
      console.error("Error extracting test countries:", error);
    }
  }

  /**
   * Load predefined country data for testing
   */
  private loadPredefinedCountries(): void {
    // Define some common countries with their bounding boxes
    const countries = [
      {
        name: "France",
        code: "FR",
        continent: "Europe",
        population: 67000000,
        bbox: [-5.1, 41.3, 9.6, 51.1], // [west, south, east, north]
      },
      {
        name: "Germany",
        code: "DE",
        continent: "Europe",
        population: 83000000,
        bbox: [5.8, 47.2, 15.0, 55.1],
      },
      {
        name: "United Kingdom",
        code: "GB",
        continent: "Europe",
        population: 67000000,
        bbox: [-8.6, 49.9, 1.8, 60.9],
      },
      {
        name: "United States",
        code: "US",
        continent: "North America",
        population: 331000000,
        bbox: [-125.0, 24.0, -66.0, 49.0],
      },
      {
        name: "Canada",
        code: "CA",
        continent: "North America",
        population: 38000000,
        bbox: [-141.0, 41.7, -52.6, 83.1],
      },
      {
        name: "Australia",
        code: "AU",
        continent: "Oceania",
        population: 25000000,
        bbox: [113.0, -43.6, 153.6, -10.6],
      },
      {
        name: "Japan",
        code: "JP",
        continent: "Asia",
        population: 126000000,
        bbox: [129.5, 31.0, 145.8, 45.5],
      },
      {
        name: "Brazil",
        code: "BR",
        continent: "South America",
        population: 212000000,
        bbox: [-73.9, -33.7, -34.7, 5.2],
      },
    ];

    // Convert bounding boxes to polygons and store them
    countries.forEach((country) => {
      const [west, south, east, north] = country.bbox;
      const polygon = turf.bboxPolygon([west, south, east, north]);
      this.countryBoundaries.set(country.code, {
        ...country,
        geometry: polygon.geometry,
      });
    });

    console.log(`Loaded ${this.countryBoundaries.size} predefined countries`);
  }

  /**
   * Get country information by coordinates
   * @param coordinates Latitude and longitude
   * @returns Country information or null if not found
   */
  getCountryByCoordinates(coordinates: Coordinates): CountryInfo | null {
    if (!this.isLoaded) {
      throw new Error("Country data not loaded. Call loadData() first.");
    }

    try {
      // Create a point from the coordinates
      const point = turf.point([coordinates.longitude, coordinates.latitude]);

      // Find the country that contains the point
      for (const [code, country] of this.countryBoundaries.entries()) {
        const polygon = turf.polygon(country.geometry.coordinates);
        if (turf.booleanPointInPolygon(point, polygon)) {
          return {
            name: country.name,
            code: country.code,
            continent: country.continent,
            population: country.population,
          };
        }
      }

      return null;
    } catch (error) {
      console.error("Error in getCountryByCoordinates:", error);
      return null;
    }
  }

  /**
   * Check if the data is loaded
   * @returns True if the data is loaded, false otherwise
   */
  isDataLoaded(): boolean {
    return this.isLoaded;
  }
}
