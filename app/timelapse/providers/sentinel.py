from __future__ import annotations

from datetime import date, datetime, time, timezone
import hashlib
import logging
from pathlib import Path
import struct
from typing import Any
from uuid import UUID, uuid4
import zlib

import httpx

from app.config import settings
from app.timelapse.schemas import AssetResponse, NdviMetrics, TimelapseFrame, TimelapseSource

logger = logging.getLogger(__name__)

RGB = '''//VERSION=3
function setup(){return {input:[{bands:["B02","B03","B04","SCL","dataMask"]}],output:{bands:4}};}
function evaluatePixel(s){let v=s.dataMask&&[4,5,6].includes(s.SCL);return v?[2.5*s.B04,2.5*s.B03,2.5*s.B02,1]:[0,0,0,0];}'''
NDVI = '''//VERSION=3
function setup(){return {input:[{bands:["B04","B08","SCL","dataMask"]}],output:{bands:4}};}
function evaluatePixel(s){let v=s.dataMask&&[4,5,6].includes(s.SCL)&&s.B08+s.B04!==0;if(!v)return [0,0,0,0];let n=(s.B08-s.B04)/(s.B08+s.B04);let t=Math.max(0,Math.min(1,(n+.2)/1.1));return [1-t,t,.15,1];}'''
STATS = '''//VERSION=3
function setup(){return {input:[{bands:["B04","B08","SCL","dataMask"]}],output:[{id:"default",bands:1},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){let v=s.dataMask&&[4,5,6].includes(s.SCL)&&s.B08+s.B04!==0;return {default:[v?(s.B08-s.B04)/(s.B08+s.B04):0],dataMask:[v?1:0]};}'''


class Sentinel2Provider:
    def __init__(self) -> None:
        self.client_id = settings.cdse_client_id
        self.client_secret = settings.cdse_client_secret

    def has_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_auth_token(self) -> str | None:
        if not self.has_credentials():
            return None
        try:
            with httpx.Client(timeout=15) as client:
                response = client.post(settings.cdse_token_url, data={
                    "grant_type": "client_credentials", "client_id": self.client_id,
                    "client_secret": self.client_secret,
                })
                response.raise_for_status()
                return response.json().get("access_token")
        except httpx.HTTPError as exc:
            logger.warning("CDSE token retrieval failed: %s", exc)
            return None

    @staticmethod
    def _bbox(coords: list[list[list[float]]]) -> list[float]:
        points = [point for ring in coords for point in ring]
        return [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]

    @classmethod
    def _polygon_fraction_of_bbox(cls, coords: list[list[list[float]]]) -> float:
        """Approximate the polygon share of its bbox for alpha-mask normalization.

        The Process API returns alpha=0 outside `bounds.geometry`; valid coverage must therefore
        be measured against the parcel area, not the enclosing rectangle used by the PNG grid.
        """
        ring = coords[0]
        twice_area = abs(sum(
            ring[index][0] * ring[index + 1][1] - ring[index + 1][0] * ring[index][1]
            for index in range(len(ring) - 1)
        ))
        west, south, east, north = cls._bbox(coords)
        bbox_twice_area = 2 * (east - west) * (north - south)
        return twice_area / bbox_twice_area if bbox_twice_area else 1.0

    @staticmethod
    def _day_range(observed_at: datetime) -> tuple[str, str]:
        day = observed_at.astimezone(timezone.utc).date()
        start = datetime.combine(day, time.min, tzinfo=timezone.utc)
        end = datetime.combine(day, time.max, tzinfo=timezone.utc)
        return start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")

    @staticmethod
    def _bounds(coords: list[list[list[float]]]) -> dict[str, Any]:
        return {"geometry": {"type": "Polygon", "coordinates": coords}, "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}}

    def _process_png(self, client: httpx.Client, token: str, coords: list[list[list[float]]], observed_at: datetime, evalscript: str) -> bytes:
        from_time, to_time = self._day_range(observed_at)
        payload = {"input": {"bounds": self._bounds(coords), "data": [{"type": "sentinel-2-l2a", "dataFilter": {"timeRange": {"from": from_time, "to": to_time}, "mosaickingOrder": "leastCC"}}]}, "output": {"width": 256, "height": 256, "responses": [{"identifier": "default", "format": {"type": "image/png"}}]}, "evalscript": evalscript}
        response = client.post(settings.cdse_process_url, json=payload, headers={"Authorization": f"Bearer {token}", "Accept": "image/png"})
        response.raise_for_status()
        if not response.content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Process API did not return PNG")
        return response.content

    @staticmethod
    def _ndvi_metrics_from_png(png: bytes) -> tuple[NdviMetrics, float, int]:
        """Extracts metrics from our lossless RGBA NDVI preview.

        The NDVI evalscript maps `ndvi` to green with `t=(ndvi+0.2)/1.1` and uses alpha as
        the SCL/dataMask result. This keeps display and metrics on exactly the same usable pixels.
        It is quantized to 8-bit; a future Statistics API integration can replace it for analytics.
        """
        if not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Expected PNG raster")
        index, width, height, color_type, idat = 8, 0, 0, -1, bytearray()
        while index < len(png):
            size = struct.unpack(">I", png[index:index + 4])[0]
            tag = png[index + 4:index + 8]
            chunk = png[index + 8:index + 8 + size]
            index += size + 12
            if tag == b"IHDR":
                width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk)
                if bit_depth != 8 or color_type != 6:
                    raise ValueError("Expected 8-bit RGBA PNG")
            elif tag == b"IDAT":
                idat.extend(chunk)
            elif tag == b"IEND":
                break
        if not width or not height:
            raise ValueError("PNG has no image header")
        raw, stride, previous = zlib.decompress(bytes(idat)), width * 4, bytearray(width * 4)
        rows: list[bytearray] = []
        cursor = 0
        for _ in range(height):
            filter_type = raw[cursor]
            cursor += 1
            row = bytearray(raw[cursor:cursor + stride])
            cursor += stride
            for x in range(stride):
                left = row[x - 4] if x >= 4 else 0
                up = previous[x]
                up_left = previous[x - 4] if x >= 4 else 0
                if filter_type == 1:
                    row[x] = (row[x] + left) & 255
                elif filter_type == 2:
                    row[x] = (row[x] + up) & 255
                elif filter_type == 3:
                    row[x] = (row[x] + ((left + up) // 2)) & 255
                elif filter_type == 4:
                    p, pa, pb, pc = left + up - up_left, 0, 0, 0
                    pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
                    predictor = left if pa <= pb and pa <= pc else (up if pb <= pc else up_left)
                    row[x] = (row[x] + predictor) & 255
                elif filter_type != 0:
                    raise ValueError("Unsupported PNG filter")
            rows.append(row)
            previous = row
        values = [row[x + 1] / 255 * 1.1 - 0.2 for row in rows for x in range(0, stride, 4) if row[x + 3] > 0]
        if not values:
            return NdviMetrics(), 0.0, 0
        values.sort()
        def percentile(p: float) -> float:
            return values[min(len(values) - 1, round((len(values) - 1) * p))]

        pct = percentile
        return NdviMetrics(mean=round(sum(values) / len(values), 4), p10=round(pct(.10), 4), p90=round(pct(.90), 4)), round(len(values) / (width * height), 4), len(values)

    def _search_catalogue(self, client: httpx.Client, token: str, search: dict[str, Any]) -> list[dict[str, Any]]:
        """Recorre el catálogo STAC del CDSE siguiendo el token `next` de paginación.

        Sin esto, un único `limit` recortaba la campaña a las primeras escenas.
        """
        items: list[dict[str, Any]] = []
        body = dict(search)
        while True:
            response = client.post(
                settings.cdse_catalogue_url,
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            data = response.json()
            items.extend(data.get("features", []))
            if len(items) >= settings.cdse_max_scenes:
                break
            next_link = next(
                (link for link in data.get("links", []) if link.get("rel") == "next"), None
            )
            if not next_link or not next_link.get("body"):
                break
            body = next_link["body"]
        return items[: settings.cdse_max_scenes]

    def fetch_frames(self, field_id: UUID, dataset_id: UUID, boundary_coords: list[list[list[float]]], start_date: date, end_date: date) -> tuple[list[TimelapseFrame], list[TimelapseSource], list[str]]:
        if not self.has_credentials():
            return [], [], ["SATELLITE_CREDENTIALS_MISSING: Configure CDSE_CLIENT_ID and CDSE_CLIENT_SECRET."]
        token = self.get_auth_token()
        if not token:
            return [], [], ["SATELLITE_AUTH_FAILED: Failed to obtain a CDSE access token."]
        source = TimelapseSource(id="copernicus-sentinel-2-l2a", provider="Copernicus Data Space Ecosystem (CDSE)", dataset="Sentinel-2 MSI Level-2A (Surface Reflectance)", model="L2A Bottom-Of-Atmosphere", resolution="10m (B02, B03, B04, B08); 20m SCL", retrieved_at=datetime.now(timezone.utc), documentation_url="https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html", attribution="Copernicus Sentinel data processed by TERRIA")
        search = {"collections": ["sentinel-2-l2a"], "intersects": {"type": "Polygon", "coordinates": boundary_coords}, "datetime": f"{start_date.isoformat()}T00:00:00Z/{end_date.isoformat()}T23:59:59Z", "query": {"eo:cloud_cover": {"lte": 70}}, "sortby": [{"field": "datetime", "direction": "asc"}], "limit": min(settings.cdse_page_size, settings.cdse_max_scenes)}
        try:
            with httpx.Client(timeout=90) as client:
                items = self._search_catalogue(client, token, search)
                frames: list[TimelapseFrame] = []
                reasons: list[str] = []
                seen_days: set[date] = set()
                for item in items:
                    properties = item.get("properties", {})
                    stamp = properties.get("datetime") or item.get("datetime")
                    if not stamp:
                        continue
                    observed_at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                    local_date = observed_at.astimezone(timezone.utc).date()
                    if local_date in seen_days:
                        continue
                    seen_days.add(local_date)
                    frame_id = uuid4()
                    try:
                        ndvi_png = self._process_png(client, token, boundary_coords, observed_at, NDVI)
                        ndvi, valid_fraction, valid_count = self._ndvi_metrics_from_png(ndvi_png)
                        parcel_fraction = self._polygon_fraction_of_bbox(boundary_coords)
                        valid_fraction = min(1.0, valid_fraction / parcel_fraction) if parcel_fraction else 0.0
                        usable = valid_fraction >= 0.70
                        assets: list[AssetResponse] = []
                        if usable:
                            for layer, png in (("rgb", self._process_png(client, token, boundary_coords, observed_at, RGB)), ("ndvi", ndvi_png)):
                                (Path(settings.assets_dir) / f"{frame_id}_{layer}.png").write_bytes(png)
                                assets.append(AssetResponse(id=uuid4(), layer=layer, url=f"/v1/fields/{field_id}/timelapses/{dataset_id}/frames/{frame_id}/assets/{layer}", width=256, height=256, bbox=self._bbox(boundary_coords), crs="EPSG:4326", sha256=hashlib.sha256(png).hexdigest()))
                        frames.append(TimelapseFrame(id=frame_id, observed_at=observed_at, local_date=local_date, source_item_ids=[item.get("id", "unknown")], usable=usable, valid_area_fraction=valid_fraction, valid_pixel_count=valid_count, ndvi=ndvi if usable else NdviMetrics(), missing_reason=None if usable else "INSUFFICIENT_VALID_AREA", available_layers=[asset.layer for asset in assets], assets=assets))
                    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                        logger.warning("Could not process Sentinel-2 scene %s: %s", item.get("id"), exc)
                        reasons.append(f"SATELLITE_FRAME_ERROR: {item.get('id', 'unknown')}: {exc}")
                if not frames:
                    reasons.append("SATELLITE_NO_USABLE_SCENES: No Sentinel-2 scenes were processed.")
                return frames, [source], reasons
        except httpx.HTTPError as exc:
            logger.warning("CDSE STAC search failed: %s", exc)
            return [], [source], [f"SATELLITE_CATALOG_ERROR: {exc}"]


sentinel_provider = Sentinel2Provider()
