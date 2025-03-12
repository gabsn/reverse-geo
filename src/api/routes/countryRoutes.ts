/**
 * Routes for country-related endpoints
 */

import { Router, Request, Response } from "express";
import { getCountryByCoordinates } from "../controllers/countryController";

const router = Router();

/**
 * @route GET /api/country
 * @desc Get country information by coordinates
 * @param {number} lat - Latitude
 * @param {number} lon - Longitude
 * @returns {object} Country information
 */
router.get("/", function (req: Request, res: Response) {
  getCountryByCoordinates(req, res);
});

export default router;
