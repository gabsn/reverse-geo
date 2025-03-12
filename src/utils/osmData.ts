/**
 * Utility functions for working with OpenStreetMap data
 */

import * as fs from "fs";
import * as path from "path";

/**
 * Configuration for OSM data paths
 */
export const OSM_CONFIG = {
  dataDir: path.resolve(__dirname, "../../data"),
  countriesFile: path.resolve(__dirname, "../../data/countries.osm.pbf"),
};

/**
 * Check if the required OSM data files exist
 * @returns boolean indicating if all required files exist
 */
export function checkOsmDataFiles(): boolean {
  try {
    if (!fs.existsSync(OSM_CONFIG.dataDir)) {
      console.error(`Data directory not found: ${OSM_CONFIG.dataDir}`);
      return false;
    }

    if (!fs.existsSync(OSM_CONFIG.countriesFile)) {
      console.error(
        `Countries OSM file not found: ${OSM_CONFIG.countriesFile}`
      );
      console.error(
        "Please run the osmium filter command to generate this file:"
      );
      console.error(
        "osmium tags-filter data/planet.osm.pbf --output=data/countries.osm.pbf nwr/admin_level=2"
      );
      return false;
    }

    return true;
  } catch (error) {
    console.error("Error checking OSM data files:", error);
    return false;
  }
}

/**
 * Get information about the OSM data files
 * @returns Object with information about the OSM data files
 */
export function getOsmDataInfo(): Record<string, any> {
  try {
    const info: Record<string, any> = {};

    if (fs.existsSync(OSM_CONFIG.countriesFile)) {
      const stats = fs.statSync(OSM_CONFIG.countriesFile);
      info.countriesFile = {
        path: OSM_CONFIG.countriesFile,
        size: `${(stats.size / (1024 * 1024)).toFixed(2)} MB`,
        lastModified: stats.mtime,
      };
    }

    return info;
  } catch (error) {
    console.error("Error getting OSM data info:", error);
    return {};
  }
}
