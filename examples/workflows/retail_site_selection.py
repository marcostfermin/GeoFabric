#!/usr/bin/env python3
"""
Retail Site Selection Workflow

Features: where + with_coordinates + buffer + with_area + sjoin + nearest
Use case: Score potential retail locations based on competition, traffic, and accessibility.
"""

import geofabric as gf


def main() -> None:
    """
    Score potential retail sites for new store locations.

    Steps:
    1. Load vacant retail spaces, competitors, POIs, demographics
    2. Create trade areas around potential sites
    3. Count population and competitors in trade area
    4. Compute accessibility scores
    5. Calculate composite site scores
    6. Rank and export top locations
    """
    # Load datasets
    vacant_retail = gf.open("file:///data/vacant_retail.parquet")
    competitors = gf.open("file:///data/competitor_locations.parquet")
    pois = gf.open("file:///data/points_of_interest.parquet")
    demographics = gf.open("file:///data/demographics_blocks.parquet")
    transit = gf.open("file:///data/transit_stops.parquet")

    market_area = gf.roi.bbox(-74.02, 40.70, -73.94, 40.78)

    # Step 1: Filter to suitable vacant spaces
    candidate_sites = (
        vacant_retail.query()
        .within(market_area)
        .where("sqft >= 2000 AND sqft <= 10000")
        .where("rent_per_sqft <= 100")
        .with_coordinates(x_col="site_lon", y_col="site_lat")
    )

    # Step 2: Create 500m trade areas
    trade_areas = (
        candidate_sites
        .buffer(distance=500, unit="meters")
        .with_area(col_name="trade_area_sqm")
    )

    # Step 3: Count competitors (negative factor)
    sites_with_competitors = candidate_sites.sjoin(
        competitors.query()
        .within(market_area)
        .buffer(distance=500, unit="meters"),
        predicate="intersects",
        how="left",
    )

    # Step 4: Count high-traffic POIs (positive factor)
    traffic_generators = (
        pois.query()
        .within(market_area)
        .where("category IN ('restaurant', 'entertainment', 'shopping', 'office')")
    )

    sites_with_traffic = candidate_sites.sjoin(
        traffic_generators.buffer(distance=300, unit="meters"),
        predicate="intersects",
        how="left",
    )

    # Step 5: Check transit accessibility
    transit_accessible = candidate_sites.nearest(
        transit.query().within(market_area),
        k=3,
        max_distance=400,
    )

    # Step 6: Get demographic data for trade areas
    demographics_in_area = (
        demographics.query()
        .within(market_area)
        .where("median_income >= 50000")
        .with_area(col_name="block_area")
    )

    sites_with_demographics = trade_areas.sjoin(
        demographics_in_area,
        predicate="intersects",
        how="inner",
    )

    # Step 7: Export analysis layers
    candidate_sites.to_parquet("candidate_retail_sites.parquet")
    candidate_sites.to_geojson("candidate_retail_sites.geojson")
    trade_areas.to_geojson("retail_trade_areas.geojson")

    sites_with_competitors.to_parquet("sites_competitor_analysis.parquet")
    sites_with_traffic.to_parquet("sites_traffic_analysis.parquet")
    transit_accessible.to_parquet("sites_transit_analysis.parquet")

    competitors.query().within(market_area).to_geojson("competitors.geojson")

    print("Retail site selection analysis complete")


if __name__ == "__main__":
    main()
