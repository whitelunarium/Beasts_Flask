#!/usr/bin/env python3
"""
Import neighborhood boundary polygons from a GeoJSON FeatureCollection.

Usage:
    python scripts/import_neighborhood_polygons.py path/to/neighborhoods.geojson

Each feature should include either a neighborhood number or name in properties.
Supported property keys:
    number, neighborhood_number, NeighborhoodNumber, id, name, neighborhood_name, Neighborhood
"""

import json
import sys
from pathlib import Path

from app import create_app, db
from app.models.neighborhood import Neighborhood


NUMBER_KEYS = ('number', 'neighborhood_number', 'NeighborhoodNumber', 'id')
NAME_KEYS = ('name', 'neighborhood_name', 'Neighborhood')


def main():
    if len(sys.argv) != 2:
        print('Usage: python scripts/import_neighborhood_polygons.py path/to/neighborhoods.geojson')
        return 2

    geojson_path = Path(sys.argv[1])
    if not geojson_path.exists():
        print(f'File not found: {geojson_path}')
        return 2

    data = json.loads(geojson_path.read_text(encoding='utf-8'))
    features = data.get('features', [])
    if data.get('type') != 'FeatureCollection' or not features:
        print('Expected a GeoJSON FeatureCollection with features.')
        return 2

    app = create_app()
    with app.app_context():
        updated = 0
        skipped = 0

        for feature in features:
            neighborhood = find_neighborhood_for_feature(feature)
            geometry = feature.get('geometry')

            if not neighborhood or not geometry:
                skipped += 1
                continue

            neighborhood.polygon_coords_json = json.dumps(geometry, separators=(',', ':'))
            updated += 1

        db.session.commit()

    print(f'Imported polygons for {updated} neighborhoods. Skipped {skipped} features.')
    return 0


def find_neighborhood_for_feature(feature):
    properties = feature.get('properties') or {}

    number = first_property(properties, NUMBER_KEYS)
    if number is not None:
        try:
            neighborhood = Neighborhood.query.filter_by(number=int(number)).first()
            if neighborhood:
                return neighborhood
        except (TypeError, ValueError):
            pass

    name = first_property(properties, NAME_KEYS)
    if name:
        return Neighborhood.query.filter(Neighborhood.name.ilike(str(name).strip())).first()

    return None


def first_property(properties, keys):
    for key in keys:
        value = properties.get(key)
        if value not in (None, ''):
            return value
    return None


if __name__ == '__main__':
    raise SystemExit(main())
