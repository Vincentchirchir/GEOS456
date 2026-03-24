import arcpy
import os


def build_band_records(point_event_tables, line_event_tables):
    records = []

    for table in point_event_tables:
        with arcpy.da.SearchCursor(table, ["MEAS", "Chainage"]) as cursor:
            for meas, chainage in cursor:
                records.append(
                    {
                        "type": "POINT",
                        "meas": meas,
                        "chainage": chainage,
                        "source_table": os.path.basename(table),
                    }
                )

    for table in line_event_tables:
        with arcpy.da.SearchCursor(
            table, ["FMEAS", "TMEAS", "ChainageRange"]
        ) as cursor:
            for fmeas, tmeas, chainage_range in cursor:
                start = min(fmeas, tmeas)
                end = max(fmeas, tmeas)

                records.append(
                    {
                        "type": "LINE",
                        "fmeas": start,
                        "tmeas": end,
                        "range": chainage_range,
                        "source_table": os.path.basename(table),
                    }
                )

    return records
