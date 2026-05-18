"""Real-time commute train data via NRE OpenLDBWS (Live Departure Boards Web Service).

One HTTP SOAP call per direction returns the next departures with real-time
delays, cancellations, and calling-point arrival times — no persistent
connection required.

Register for a free token at:
  https://realtime.nationalrail.co.uk/OpenLDBWSRegistration/
Add to .env:  NR_API_TOKEN=<your-token>
"""

import logging
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, time as dtime, timedelta

log = logging.getLogger(__name__)

_LDB_TOKEN = os.environ.get("NR_API_TOKEN", "")
_LDB_URL = "https://lite.realtime.nationalrail.co.uk/OpenLDBWS/ldb11.asmx"
_SOAP_ACTION = "http://thalesgroup.com/RTTI/2015-05-14/ldb/GetDepBoardWithDetails"
_TIME_WINDOW_MINS = 120  # minutes ahead to look for departures


def credentials_configured() -> bool:
    return bool(_LDB_TOKEN)


# ---------------------------------------------------------------------------
# SOAP request
# ---------------------------------------------------------------------------


def _soap_payload(from_crs: str, to_crs: str, num_rows: int = 10) -> bytes:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:ldb="http://thalesgroup.com/RTTI/2017-10-01/ldb/"
               xmlns:tok="http://thalesgroup.com/RTTI/2013-11-28/Token/types">
  <soap:Header>
    <tok:AccessToken><tok:TokenValue>{_LDB_TOKEN}</tok:TokenValue></tok:AccessToken>
  </soap:Header>
  <soap:Body>
    <ldb:GetDepBoardWithDetailsRequest>
      <ldb:numRows>{num_rows}</ldb:numRows>
      <ldb:crs>{from_crs}</ldb:crs>
      <ldb:filterCrs>{to_crs}</ldb:filterCrs>
      <ldb:filterType>to</ldb:filterType>
      <ldb:timeOffset>0</ldb:timeOffset>
      <ldb:timeWindow>{_TIME_WINDOW_MINS}</ldb:timeWindow>
    </ldb:GetDepBoardWithDetailsRequest>
  </soap:Body>
</soap:Envelope>""".encode("utf-8")


def _fetch_ldb(from_crs: str, to_crs: str) -> bytes:
    req = urllib.request.Request(
        _LDB_URL,
        data=_soap_payload(from_crs, to_crs),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": _SOAP_ACTION,
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------


def _tag(el: ET.Element) -> str:
    t = el.tag
    return t.split("}", 1)[-1] if "}" in t else t


def _parse_hhmm(t: str) -> tuple[int, int] | None:
    if not t or len(t) < 5:
        return None
    try:
        return int(t[:2]), int(t[3:5])
    except ValueError:
        return None


def _resolve_estimate(estimated: str | None, scheduled: str) -> tuple[str, bool]:
    """
    Return (HH:MM, is_delayed) from an LDB etd/eta field.

    LDB values: "On time", "Cancelled", "Delayed", "No report", or "HH:MM".
    "Delayed" means late but no revised time yet — return scheduled as best guess.
    """
    if not estimated or estimated in ("No report", ""):
        return scheduled, False
    if estimated == "On time":
        return scheduled, False
    if estimated in ("Cancelled", "Delayed"):
        return scheduled, estimated == "Delayed"
    # Actual revised time
    return estimated, estimated != scheduled


def _parse_ldb_xml(xml_bytes: bytes, dest_crs: str) -> list[dict]:
    """Parse GetDepBoardWithDetails response into a flat list of service dicts."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        log.error("LDB XML parse error: %s", exc)
        return []

    services = []

    for el in root.iter():
        if _tag(el) != "service":
            continue

        std = etd = platform = None
        is_cancelled = False
        cancel_reason = None
        calling_points: list[dict] = []

        for child in el:
            ct = _tag(child)
            if ct == "std":
                std = child.text
            elif ct == "etd":
                etd = child.text
            elif ct == "platform":
                platform = child.text
            elif ct == "isCancelled" and child.text == "true":
                is_cancelled = True
            elif ct == "cancelReason":
                cancel_reason = child.text
            elif ct == "subsequentCallingPoints":
                for cplist in child:
                    if _tag(cplist) != "callingPointList":
                        continue
                    for cp in cplist:
                        if _tag(cp) != "callingPoint":
                            continue
                        cp_crs = cp_st = cp_et = None
                        cp_cancelled = False
                        for field in cp:
                            ft = _tag(field)
                            if ft == "crs":
                                cp_crs = field.text
                            elif ft == "st":
                                cp_st = field.text
                            elif ft == "et":
                                cp_et = field.text
                            elif ft == "isCancelled" and field.text == "true":
                                cp_cancelled = True
                        calling_points.append(
                            {
                                "crs": cp_crs,
                                "st": cp_st,
                                "et": cp_et,
                                "cancelled": cp_cancelled,
                            }
                        )

        if not std:
            continue

        # Must call at the requested destination
        dest_cp = next((cp for cp in calling_points if cp["crs"] == dest_crs), None)
        if dest_cp is None:
            continue

        est_dep, dep_delayed = _resolve_estimate(etd, std)
        dest_st = dest_cp.get("st") or ""
        dest_et = dest_cp.get("et") or dest_st
        est_arr, arr_delayed = _resolve_estimate(dest_et, dest_st)

        if not est_dep or not est_arr:
            continue

        services.append(
            {
                "scheduled_dep": std,
                "estimated_dep": est_dep,
                "scheduled_arr": dest_st,
                "estimated_arr": est_arr,
                "platform": platform,
                "dep_delayed": dep_delayed,
                "arr_delayed": arr_delayed,
                "cancelled": is_cancelled or dest_cp.get("cancelled", False),
                "cancel_reason": cancel_reason,
            }
        )

    return services


# ---------------------------------------------------------------------------
# Train list builder
# ---------------------------------------------------------------------------


def _build_train_list(
    services: list[dict],
    walk_a_mins: int,
    walk_b_mins: int,
    now: datetime,
    direction: str,
    target_time: str,
) -> list[dict]:
    """
    Convert parsed LDB services into the train dict format used by the widget.

    direction='outbound': walk_a = home→station, walk_b = station→work.
        on_schedule = work_arrival <= target. Recommended = latest on-schedule.
    direction='return': walk_a = work→station, walk_b = station→home.
        on_schedule = dep >= target + walk_a. Recommended = first on-schedule.
    """
    target_hhmm = _parse_hhmm(target_time)
    target_dt = (
        datetime.combine(now.date(), dtime(*target_hhmm)) if target_hhmm else None
    )
    catch_from_dt = (
        target_dt + timedelta(minutes=walk_a_mins)
        if target_dt is not None and direction == "return"
        else None
    )

    trains: list[dict] = []

    for svc in services:
        dep_hhmm = _parse_hhmm(svc["estimated_dep"])
        arr_hhmm = _parse_hhmm(svc["estimated_arr"])
        if not dep_hhmm or not arr_hhmm:
            continue

        dep_dt = datetime.combine(now.date(), dtime(*dep_hhmm))
        arr_dt = datetime.combine(now.date(), dtime(*arr_hhmm))
        if arr_dt < dep_dt:
            arr_dt += timedelta(days=1)
        if dep_dt < now + timedelta(minutes=walk_a_mins):
            continue

        leave_a_dt = dep_dt - timedelta(minutes=walk_a_mins)
        arrive_b_dt = arr_dt + timedelta(minutes=walk_b_mins)
        journey_mins = int((arr_dt - dep_dt).total_seconds() / 60)

        if direction == "outbound":
            on_schedule = target_dt is not None and arrive_b_dt <= target_dt
        else:
            on_schedule = catch_from_dt is not None and dep_dt >= catch_from_dt

        trains.append(
            {
                "rid": svc["scheduled_dep"],
                "uid": svc["scheduled_dep"],
                "scheduled_dep": svc["scheduled_dep"],
                "estimated_dep": svc["estimated_dep"],
                "scheduled_arr": svc["scheduled_arr"],
                "estimated_arr": svc["estimated_arr"],
                "dep_delayed": svc["dep_delayed"],
                "arr_delayed": svc["arr_delayed"],
                "cancelled": svc["cancelled"],
                "platform": svc["platform"],
                "leave_home_by": leave_a_dt.strftime("%H:%M"),
                "work_arrival": arrive_b_dt.strftime("%H:%M"),
                "arrives_on_time": on_schedule,
                "journey_mins": journey_mins,
                "is_express": journey_mins <= 28,
                "recommended": False,
                "_dep_dt": dep_dt,
            }
        )

    trains.sort(key=lambda t: t["_dep_dt"])
    for t in trains:
        del t["_dep_dt"]

    if direction == "outbound":
        for t in reversed(trains):
            if t["arrives_on_time"] and not t["cancelled"]:
                t["recommended"] = True
                break
    else:
        for t in trains:
            if t["arrives_on_time"] and not t["cancelled"]:
                t["recommended"] = True
                break

    return trains


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_all_commute_trains(
    from_crs: str,
    to_crs: str,
    home_walk_mins: int,
    work_walk_mins: int,
    target_work_arrival: str,
    target_work_departure: str,
    **_kwargs: object,
) -> dict:
    """
    Fetch outbound and return departure boards via OpenLDBWS and return
    the enriched train list for both directions.
    """
    now = datetime.now()
    error = None

    try:
        out_xml = _fetch_ldb(from_crs, to_crs)
        out_services = _parse_ldb_xml(out_xml, to_crs)
    except Exception as exc:
        log.exception("LDB outbound fetch failed")
        out_services = []
        error = str(exc)

    try:
        ret_xml = _fetch_ldb(to_crs, from_crs)
        ret_services = _parse_ldb_xml(ret_xml, from_crs)
    except Exception as exc:
        log.exception("LDB return fetch failed")
        ret_services = []
        if error is None:
            error = str(exc)

    outbound = _build_train_list(
        out_services,
        walk_a_mins=home_walk_mins,
        walk_b_mins=work_walk_mins,
        now=now,
        direction="outbound",
        target_time=target_work_arrival,
    )
    return_trains = _build_train_list(
        ret_services,
        walk_a_mins=work_walk_mins,
        walk_b_mins=home_walk_mins,
        now=now,
        direction="return",
        target_time=target_work_departure,
    )

    return {
        "outbound": {"trains": outbound, "target": target_work_arrival},
        "return": {"trains": return_trains, "target": target_work_departure},
        "fetched_at": now.strftime("%H:%M"),
        "error": error,
    }


def start_listener() -> None:
    """No-op — kept so app.py startup code doesn't need changing."""


def find_commute_trains(
    from_crs: str,
    to_crs: str,
    home_walk_mins: int,
    work_walk_mins: int,
    target_work_arrival: str,
    **_kwargs: object,
) -> dict:
    """Outbound-only wrapper kept for backward compatibility."""
    now = datetime.now()
    try:
        xml_bytes = _fetch_ldb(from_crs, to_crs)
        services = _parse_ldb_xml(xml_bytes, to_crs)
    except Exception as exc:
        log.exception("LDB fetch failed")
        return {
            "trains": [],
            "target_work_arrival": target_work_arrival,
            "fetched_at": now.strftime("%H:%M"),
            "error": str(exc),
        }

    trains = _build_train_list(
        services,
        walk_a_mins=home_walk_mins,
        walk_b_mins=work_walk_mins,
        now=now,
        direction="outbound",
        target_time=target_work_arrival,
    )
    return {
        "trains": trains,
        "target_work_arrival": target_work_arrival,
        "fetched_at": now.strftime("%H:%M"),
    }
