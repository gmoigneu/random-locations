import uvicorn
from platformshconfig import Config

from fastapi import FastAPI, Response, status
import geojson
import json
from random import randrange
import random
from shapely.affinity import affine_transform
from shapely.geometry import Point, Polygon
from shapely.ops import triangulate
import time
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()
config = Config()

with open('countries.geojson') as f:
    gj = geojson.load(f)


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
        <html>
            <head>
                <title>Random location faker.</title>
            </head>
            <body>
                <h1>Random location faker.</h1>
                <h3>GET /country/{country}?count=100</h3>
                <p>Generate up to 100 points in the specified country. The country must be set as its ISO 3166-1 alpha-3 code.
                <a href="https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3">List available on Wikipedia</a>
            </body>
        </html>
        """


@app.get("/country/{country}", status_code=200)
async def locations(country: str, response: Response, count: int = 10):
    if count > 100:
        return JSONResponse(status_code=422, content={"message": "You can only request up to 100 points."})

    start = time.process_time()
    feature = [obj for obj in gj['features'] if obj['properties']['ISO_A3'] == country.upper()]

    if len(feature) == 0:
        return JSONResponse(status_code=404, content={
            "message": "Country not found. Check https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3"})
    else:
        coordinates = feature[0]['geometry']['coordinates']

        points = []
        point = Point

        for i in range(0, count):
            if len(coordinates) > 1:
                point = random_point_in_polygon(coordinates[randrange(len(coordinates)) - 1][0])
            else:
                point = random_point_in_polygon(coordinates[0])
            assert isinstance(point, Point)
            points.append(point)

        return {
            "points": [obj.coords for obj in points],
            "country": {
                "name": feature[0]['properties']['ADMIN'],
                "code": country.upper()
            },
            "time": time.process_time() - start
        }


# Triangulate the polygon and calculate the area of each triangle.
#
# For each sample:
# Pick the triangle t containing the sample, using random selection weighted by the area of each triangle.
# Pick a random point uniformly in the triangle, as follows:
# Pick a random point x,y uniformly in the unit square.
# If x+y>1, use the point 1−x,1−y instead. The effect of this is to ensure that the point is chosen uniformly in the unit right triangle with vertices (0,0),(0,1),(1,0)
#
# Apply the appropriate affine transformation to transform the unit right triangle to the triangle t.
def random_point_in_polygon(zone):
    polygon = Polygon(zone)
    areas = []
    transforms = []

    for t in triangulate(polygon):
        areas.append(t.area)
        (x0, y0), (x1, y1), (x2, y2), _ = t.exterior.coords
        transforms.append([x1 - x0, x2 - x0, y2 - y0, y1 - y0, x0, y0])

    for transform in random.choices(transforms, weights=areas, k=1):
        x, y = [random.random() for _ in range(2)]
        if x + y > 1:
            p = Point(1 - x, 1 - y)
        else:
            p = Point(x, y)
        return affine_transform(p, transform)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(config.port))
