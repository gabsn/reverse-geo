/**
 * Controller for country-related endpoints
 */

import { Request, Response } from "express";
import { reverseGeocode, Coordinates } from "../../index";
import { CountryService } from "../models/countryModel";

// Initialize the country service
const countryService = new CountryService();

/**
 * Get country information by coordinates
 * @param {Request} req - Express request object
 * @param {Response} res - Express response object
 * @returns {Response} JSON response with country information
 */
export const getCountryByCoordinates = (req: Request, res: Response) => {
  try {
    // Get latitude and longitude from query parameters
    const lat = parseFloat(req.query.lat as string);
    const lon = parseFloat(req.query.lon as string);

    // Validate coordinates
    if (isNaN(lat) || isNaN(lon)) {
      return res.status(400).json({
        error:
          "Invalid coordinates. Please provide valid lat and lon query parameters.",
      });
    }

    // Check if coordinates are within valid range
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      return res.status(400).json({
        error:
          "Coordinates out of range. Latitude must be between -90 and 90, longitude between -180 and 180.",
      });
    }

    // Create coordinates object
    const coordinates: Coordinates = {
      latitude: lat,
      longitude: lon,
    };

    // Get country information
    const countryInfo = countryService.getCountryByCoordinates(coordinates);

    // Return country information
    return res.json({
      coordinates,
      country: countryInfo,
    });
  } catch (error) {
    console.error("Error in getCountryByCoordinates:", error);
    return res.status(500).json({
      error: "Internal server error",
    });
  }
};
