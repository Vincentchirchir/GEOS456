import arcpy
import os
import datetime


def _get_input_extent(input_line_fc):
    """Return the extent of input_line_fc, respecting any active selection.

    If the layer has selected features (i.e. the tool was run with
    'Use the selected records' enabled), only those features contribute
    to the extent.  Falls back to Describe().extent if no geometry is found.
    """
    xmin = xmax = ymin = ymax = None
    sr = None

    try:
        with arcpy.da.SearchCursor(input_line_fc, ["SHAPE@"]) as cursor:
            for (geom,) in cursor:
                if geom is None:
                    continue
                ext = geom.extent
                if sr is None:
                    sr = ext.spatialReference
                xmin = ext.XMin if xmin is None else min(xmin, ext.XMin)
                ymin = ext.YMin if ymin is None else min(ymin, ext.YMin)
                xmax = ext.XMax if xmax is None else max(xmax, ext.XMax)
                ymax = ext.YMax if ymax is None else max(ymax, ext.YMax)
    except Exception:
        pass

    if xmin is not None:
        return arcpy.Extent(xmin, ymin, xmax, ymax, spatial_reference=sr)

    # Fallback: no cursor results — use full dataset extent
    desc = arcpy.Describe(input_line_fc)
    return desc.extent


def _format_location_from_xy(x_value, y_value, is_latlon=False):
    """
    Formats a fallback location string for the sheet title.

    Geographic coordinates are rendered with hemisphere suffixes; projected or
    unknown coordinates fall back to plain X/Y values so the title still carries
    a useful locator even when geocoding cannot run.
    """
    if is_latlon:
        ns = "N" if y_value >= 0 else "S"
        ew = "E" if x_value >= 0 else "W"
        return f"{abs(y_value):.2f}°{ns} {abs(x_value):.2f}°{ew}"

    return f"X {x_value:.2f}, Y {y_value:.2f}"


def _get_input_reference_point(input_line_fc):
    """
    Returns a representative point for title geocoding.

    A midpoint along the first visible line geometry is preferred because it
    better reflects the route than the center of the feature extent. If no
    usable line geometry is found, the function falls back to the selected
    feature extent center.
    """
    spatial_ref = None

    try:
        with arcpy.da.SearchCursor(input_line_fc, ["SHAPE@"]) as cursor:
            for (geom,) in cursor:
                if geom is None:
                    continue

                spatial_ref = geom.spatialReference or spatial_ref

                try:
                    midpoint = geom.positionAlongLine(0.5, True)
                    if midpoint and midpoint.centroid:
                        return midpoint.centroid.X, midpoint.centroid.Y, spatial_ref
                except Exception:
                    centroid = getattr(geom, "centroid", None)
                    if centroid:
                        return centroid.X, centroid.Y, spatial_ref
    except Exception:
        pass

    extent = _get_input_extent(input_line_fc)
    if extent:
        spatial_ref = spatial_ref or extent.spatialReference
        return (
            (extent.XMin + extent.XMax) / 2.0,
            (extent.YMin + extent.YMax) / 2.0,
            spatial_ref,
        )

    raise ValueError("Could not derive a representative point from the input feature.")


# Country names broad enough to be useless as a sheet-title location.
_COUNTRY_NAME_DENYLIST = frozenset({
    "canada",
    "united states",
    "usa",
})

# Common road/route address prefixes found in geocoder label fields.
_ADDRESS_PREFIXES = (
    "highway ",
    "hwy ",
    "range road ",
    "township road ",
    "twp rd ",
    "rr ",
    "po box ",
    "county road ",
    "cr ",
)


def _looks_like_address_token(text):
    """
    Returns True when text looks like a street or road address fragment
    rather than a place name.

    Catches things like "123 Main St", "Highway 1", "Range Road 25",
    "Township Road 240", "RR 5", and "PO Box 12" that sometimes appear
    as the leading token of a geocoder label field.
    """
    if not text:
        return False
    if text[0].isdigit():
        return True
    lower = text.lower()
    return any(lower.startswith(prefix) for prefix in _ADDRESS_PREFIXES)


def _extract_place_candidate(value, field_name=""):
    """
    Extracts a usable place name from a single reverse-geocode field value.

    Returns None when the value is absent, empty, or looks like an ISO code,
    postal code, country name, or address fragment rather than a human-readable
    place name.

    For label-style fields (REV_LongLabel, REV_ShortLabel, REV_Match_addr)
    the most specific comma-delimited token is chosen:

    - "123 Main St, Calgary, AB, CAN"  → "Calgary"        (first token is a street number)
    - "Highway 1, Calgary, AB, CAN"    → "Calgary"        (first token is a road prefix)
    - "Calgary, Alberta, CAN"          → "Calgary"        (first token is the place)
    - "Wheatland County, Alberta, CAN" → "Wheatland County"
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    fn = (field_name or "").lower()
    if fn in {"rev_longlabel", "rev_shortlabel", "rev_match_addr"}:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if not parts:
            return None
        # If the first token looks like an address fragment, the place name
        # is the next token; otherwise the first token is the place name.
        text = parts[1] if (_looks_like_address_token(parts[0]) and len(parts) >= 2) else parts[0]

    # Reject 2–3 char all-uppercase alphabetic codes (AB, CAN, US, etc.)
    if len(text) <= 3 and text.isalpha() and text == text.upper():
        return None

    # Reject pure-digit strings (numeric postal codes like "90210")
    if text.replace(" ", "").isdigit():
        return None

    # Reject signed decimal coordinate strings like "-113.954856682" or "53.5461".
    # These appear in REV_X / REV_Y string fields from some geocoder responses and
    # slip past the digit check because they contain "." and "-".
    try:
        float(text)
        return None
    except ValueError:
        pass

    # Reject short alphanumeric postal codes like "T2E 0A1" or "SW1A 1AA"
    stripped = text.replace(" ", "")
    if len(stripped) <= 7 and stripped.isalnum() and any(c.isdigit() for c in stripped):
        return None

    # Reject country-name-only results that are too broad to be useful
    if text.lower() in _COUNTRY_NAME_DENYLIST:
        return None

    return " ".join(text.split())


# Higher score → preferred as the sheet-title location.
# Label fields score lower because they may embed address strings that need
# extra parsing and are less reliable than dedicated administrative fields.
_GEOCODE_FIELD_PRIORITY = {
    "rev_city": 60,
    "rev_placename": 60,
    "rev_neighborhood": 50,
    "rev_district": 40,
    "rev_subregion": 30,
    "rev_region": 20,
    "rev_longlabel": 10,
    "rev_shortlabel": 10,
    "rev_match_addr": 10,
}


def _best_geocode_place(field_value_pairs):
    """
    Selects the best place name from a collection of (field_name, value) pairs
    returned by a reverse geocode operation.

    Every pair is passed through _extract_place_candidate to filter junk.
    Survivors are scored with _GEOCODE_FIELD_PRIORITY; ties are broken by text
    length (longer text is typically more descriptive).  The highest-scoring
    result is returned, or None when no usable place name is found.
    """
    candidates = []
    for field_name, value in field_value_pairs:
        text = _extract_place_candidate(value, field_name)
        if text:
            score = _GEOCODE_FIELD_PRIORITY.get((field_name or "").lower(), 0)
            candidates.append((score, len(text), text))

    if not candidates:
        return None

    return max(candidates, key=lambda x: (x[0], x[1]))[2]


def _select_preferred_reverse_geocoder(geocoders):
    """
    Prefers the ArcGIS World Geocoding Service when it is registered on the
    active portal, otherwise falls back to the first available geocoder.
    """
    if not geocoders:
        raise RuntimeError("No geocoders are registered with the active portal.")

    for geocoder in geocoders:
        url = str(getattr(geocoder, "url", "") or "")
        lower_url = url.lower()

        try:
            description = str(
                getattr(getattr(geocoder, "properties", None), "serviceDescription", "")
                or ""
            )
        except Exception:
            description = ""

        combined = f"{url} {description}".lower()
        if (
            "geocode.arcgis.com" in lower_url
            or "arcgis world geocoding service" in combined
        ):
            return geocoder

    return geocoders[0]


def _reverse_geocode_city(map_x, map_y, spatial_ref):
    """
    Resolves a map coordinate to the nearest city or locality name using
    ArcGIS Pro's built-in ArcGIS API for Python integration.

    Credit usage
    ------------
    This call can consume credits depending on the active portal's geocode
    service and licensing. It requires an active ArcGIS Pro portal sign-in.
    Authentication is delegated to GIS("pro"), which uses the active Pro
    session rather than manually assembling tokens and REST requests.

    Failure handling
    ----------------
    Any failure (no sign-in, network error, quota exceeded, service error)
    falls back gracefully to a decimal coordinate string so the sheet title
    still renders rather than leaving the field blank or crashing the tool.

    Parameters
    ----------
    map_x, map_y : float
        Coordinate pair in the spatial reference of the input feature class.
    spatial_ref : arcpy.SpatialReference
        Spatial reference of the input coordinates. Projected automatically
        to WGS84 (WKID 4326) before the request is sent.

    Returns
    -------
    str
        City name (e.g. "Calgary"), or a decimal coordinate fallback string
        (e.g. "51.05°N 114.07°W") if geocoding fails for any reason.
    """
    lon = lat = None

    # The World Geocoding Service expects geographic coordinates (lon, lat), so
    # convert to WGS84 first and cache that conversion for both the request and
    # any later fallback string.
    try:
        wgs84 = arcpy.SpatialReference(4326)
        if spatial_ref and spatial_ref.factoryCode == 4326:
            lon = map_x
            lat = map_y
        elif spatial_ref:
            point_geom = arcpy.PointGeometry(arcpy.Point(map_x, map_y), spatial_ref)
            point_wgs84 = point_geom.projectAs(wgs84)
            lon = point_wgs84.centroid.X
            lat = point_wgs84.centroid.Y
        else:
            raise ValueError("Input feature has no spatial reference defined.")
    except Exception as e:
        arcpy.AddWarning(f"Could not project coordinates to WGS84 for geocoding: {e}")
        return _format_location_from_xy(map_x, map_y, is_latlon=False)

    try:
        # arcgis.geocoding.reverse_geocode uses the active ArcGIS Pro portal
        # session (GIS("pro")), so authentication and credit handling are
        # automatic — no URL assembly or token management needed.
        from arcgis.gis import GIS
        from arcgis.geocoding import reverse_geocode as _arcgis_reverse_geocode
        from arcgis.geocoding import get_geocoders

        gis = GIS("pro")
        geocoders = get_geocoders(gis)
        geocoder = _select_preferred_reverse_geocoder(geocoders)
        geocoder_url = str(getattr(geocoder, "url", "") or "")
        if geocoder_url:
            arcpy.AddMessage(f"Reverse geocode service: {geocoder_url}")
        else:
            arcpy.AddMessage(
                "Reverse geocode service selected from GIS('pro') geocoder registry."
            )

        result = _arcgis_reverse_geocode(
            location={"x": lon, "y": lat, "spatialReference": {"wkid": 4326}},
            geocoder=geocoder,
        )

        address = (result or {}).get("address", {})

        non_empty_values = [
            f"{k}={v}" for k, v in address.items() if v not in (None, "")
        ]

        # Prefix keys with REV_ so the existing candidate-scoring pipeline
        # (_GEOCODE_FIELD_PRIORITY, _extract_place_candidate) works unchanged.
        field_value_pairs = [(f"REV_{k}", v) for k, v in address.items()]
        city = _best_geocode_place(field_value_pairs)

        if city:
            arcpy.AddMessage(f"Reverse geocoded sheet location: {city}")
            return city

        if non_empty_values:
            arcpy.AddWarning(
                "Reverse geocode: fields had values but none yielded a usable place name. "
                f"Raw values: {', '.join(non_empty_values)}"
            )
        else:
            arcpy.AddWarning(
                "Reverse geocode: the selected geocoder returned no address data."
            )

        raise RuntimeError(
            "reverse_geocode returned no usable place name for this location."
        )

    except Exception as e:
        arcpy.AddWarning(
            f"Reverse geocoding request failed: {e}. "
            "Falling back to coordinate string in sheet title."
        )

    return _format_location_from_xy(lon, lat, is_latlon=True)


def _clean_sheet_name(input_line_fc):
    """
    Builds a readable sheet name from the input dataset name.

    Tool-generated suffixes are stripped and acronym-like tokens are preserved
    instead of being forced to title case.
    """
    raw_name = os.path.splitext(os.path.basename(str(input_line_fc)))[0]

    suffix_tokens = {"route", "line", "fc", "copy"}
    tokens = [
        token for token in raw_name.replace("_", " ").replace("-", " ").split() if token
    ]

    while len(tokens) > 1 and tokens[-1].lower() in suffix_tokens:
        tokens.pop()

    cleaned_tokens = []
    for token in tokens:
        if token.isupper() or any(char.isdigit() for char in token):
            cleaned_tokens.append(token)
        else:
            cleaned_tokens.append(token.capitalize())

    return " ".join(cleaned_tokens) or "Pipeline"


def _build_sheet_title(input_line_fc):
    """
    Derives the project-title block values from the input feature class.

    Project Name format
    -------------------
        {Clean Name} Alignment Sheet

    Where:
        Clean Name  — input FC basename, underscores replaced, title-cased,
                      common generated suffixes stripped (_Route, _Line, etc.)

    Location format
    ---------------
        {City}, {Year}

    Where:
        City        — reverse geocoded from a representative point on the input
                      feature or a coordinate fallback
        Year        — current calendar year at time of tool execution

    Parameters
    ----------
    input_line_fc : str
        Path to the input line feature class.

    Returns
    -------
    tuple of (str, str)
        (project_name_value, location_value)
    """
    clean_name = _clean_sheet_name(input_line_fc)

    try:
        ref_x, ref_y, spatial_ref = _get_input_reference_point(input_line_fc)
        city = _reverse_geocode_city(ref_x, ref_y, spatial_ref)
    except Exception as e:
        arcpy.AddWarning(f"Could not compute title location from input feature: {e}")
        city = "Unknown Location"

    year = datetime.datetime.now().year
    title = f"{clean_name} Alignment Sheet"
    subtitle = f"{city}, {year}"

    arcpy.AddMessage(f"Project title block: {title} | {subtitle}")
    return title, subtitle
