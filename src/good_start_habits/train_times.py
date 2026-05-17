"""Real-time commute train data via Darwin Push Port (National Rail)."""

import gzip
import os
import socket
import time
import xml.etree.ElementTree as ET
from datetime import datetime, time as dtime, timedelta

_STOMP_HOST = os.environ.get("NR_STOMP_HOST", "darwin-dist-44ae45.nationalrail.co.uk")
_STOMP_PORT = int(os.environ.get("NR_STOMP_PORT", "61613"))
_ACCESS_KEY = os.environ.get("NR_ACCESS_KEY", "")
_SECRET_KEY = os.environ.get("NR_SECRET_KEY", "")
_TOPIC = "/topic/darwin.pushport-v16"


def credentials_configured() -> bool:
    return bool(_ACCESS_KEY and _SECRET_KEY)


# ---------------------------------------------------------------------------
# Raw STOMP client (avoids stomp.py's UTF-8 decode corrupting gzip bodies)
# ---------------------------------------------------------------------------


def _send_frame(sock: socket.socket, cmd: str, headers: dict | None = None) -> None:
    frame = f"{cmd}\n"
    for k, v in (headers or {}).items():
        frame += f"{k}:{v}\n"
    frame += "\n\x00"
    sock.sendall(frame.encode("ascii"))


def _read_exactly(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed")
        buf += chunk
    return buf


def _read_frame(sock: socket.socket) -> tuple[str, dict, bytes] | None:
    """Read one STOMP frame, returning (command, headers, body_bytes)."""
    header_lines: list[str] = []
    while True:
        line = b""
        while True:
            ch = sock.recv(1)
            if not ch:
                return None
            if ch == b"\n":
                break
            if ch != b"\r":
                line += ch
        decoded = line.decode("ascii", errors="replace").strip("\x00")
        if decoded == "":
            if header_lines:
                break
            continue  # heartbeat — skip blank lines until we see a command
        header_lines.append(decoded)

    if not header_lines:
        return None

    cmd = header_lines[0]
    headers: dict[str, str] = {}
    for h in header_lines[1:]:
        if ":" in h:
            k, _, v = h.partition(":")
            headers[k.strip()] = v.strip()

    # Use content-length when present — gzip bodies contain \x00 bytes that
    # must not be treated as frame terminators.
    if "content-length" in headers:
        n = int(headers["content-length"])
        body = _read_exactly(sock, n)
        sock.recv(1)  # consume trailing \x00
    else:
        body = b""
        while True:
            ch = sock.recv(1)
            if not ch or ch == b"\x00":
                break
            body += ch

    return cmd, headers, body


def _collect(seconds: int) -> list[bytes]:
    """Connect, subscribe, collect decompressed XML payloads for `seconds`."""
    if not _ACCESS_KEY or not _SECRET_KEY:
        raise ValueError("NR_ACCESS_KEY and NR_SECRET_KEY must be set")

    sock = socket.create_connection((_STOMP_HOST, _STOMP_PORT), timeout=15)
    _send_frame(
        sock,
        "CONNECT",
        {
            "accept-version": "1.1",
            "login": _ACCESS_KEY,
            "passcode": _SECRET_KEY,
            "heart-beat": "0,0",
        },
    )

    sock.settimeout(10)
    frame = _read_frame(sock)
    if frame is None or frame[0] != "CONNECTED":
        raise ConnectionError(f"Expected CONNECTED, got: {frame and frame[0]}")

    _send_frame(sock, "SUBSCRIBE", {"destination": _TOPIC, "id": "1", "ack": "auto"})

    payloads: list[bytes] = []
    sock.settimeout(2.0)
    deadline = time.time() + seconds

    while time.time() < deadline:
        try:
            frame = _read_frame(sock)
        except socket.timeout:
            continue
        except Exception:
            break

        if frame is None:
            continue
        cmd, _, body = frame
        if cmd == "MESSAGE":
            try:
                payloads.append(gzip.decompress(body))
            except Exception:
                payloads.append(body)
        elif cmd == "ERROR":
            raise ConnectionError(
                f"STOMP ERROR: {body.decode('utf-8', errors='replace')}"
            )

    try:
        sock.close()
    except Exception:
        pass

    return payloads


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------


def _tag(el: ET.Element) -> str:
    t = el.tag
    return t.split("}", 1)[-1] if "}" in t else t


def _attr(el: ET.Element, name: str, default: str = "") -> str:
    return el.get(name, default)


def _el_time(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return _attr(el, "et") or _attr(el, "at")


def _parse_schedule(sched: ET.Element) -> dict:
    calling = []
    for loc in sched:
        loc_tag = _tag(loc)
        if loc_tag not in ("OR", "IP", "DT", "OPOR", "OPIP", "OPDT", "PP"):
            continue
        plat = None
        for child in loc:
            if _tag(child) == "plat":
                plat = child.text
                break
        calling.append(
            {
                "type": loc_tag,
                "tiploc": _attr(loc, "tpl"),
                "pta": _attr(loc, "pta"),
                "ptd": _attr(loc, "ptd"),
                "platform": plat,
            }
        )
    return {
        "rid": _attr(sched, "rid"),
        "uid": _attr(sched, "uid"),
        "ssd": _attr(sched, "ssd"),
        "toc": _attr(sched, "toc"),
        "calling_points": calling,
    }


def _parse_ts(ts: ET.Element) -> dict:
    locations = []
    for loc in ts:
        # Darwin v16 uses <Location> (Forecasts/v3 namespace); older: <LT>/<OPLT>
        if _tag(loc) not in ("Location", "LT", "OPLT"):
            continue
        arr_el = dep_el = plat_el = None
        for child in loc:
            child_tag = _tag(child)
            if child_tag == "arr":
                arr_el = child
            elif child_tag == "dep":
                dep_el = child
            elif child_tag == "plat":
                plat_el = child
        locations.append(
            {
                "tiploc": _attr(loc, "tpl"),
                "arr_et": _el_time(arr_el),
                "dep_et": _el_time(dep_el),
                "arr_delayed": _attr(arr_el, "delayed") == "true"
                if arr_el is not None
                else False,
                "dep_delayed": _attr(dep_el, "delayed") == "true"
                if dep_el is not None
                else False,
                "platform": plat_el.text if plat_el is not None else None,
            }
        )
    return {
        "rid": _attr(ts, "rid"),
        "toc": _attr(ts, "toc"),
        "ssd": _attr(ts, "ssd"),
        "locations": locations,
    }


def _parse_all(raw_messages: list[bytes], toc: str) -> tuple[dict, dict]:
    """Returns (schedules_by_rid, ts_updates_by_rid)."""
    schedules: dict[str, dict] = {}
    ts_updates: dict[str, dict] = {}

    for raw in raw_messages:
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            continue
        for ur in root:
            if _tag(ur) != "uR":
                continue
            for child in ur:
                child_tag = _tag(child)
                if child_tag == "schedule":
                    s = _parse_schedule(child)
                    if not toc or s["toc"] == toc:
                        schedules[s["rid"]] = s
                elif child_tag == "TS":
                    ts_data = _parse_ts(child)
                    ts_updates[ts_data["rid"]] = ts_data

    return schedules, ts_updates


def _parse_hhmm(t: str) -> tuple[int, int] | None:
    if not t or len(t) < 5:
        return None
    try:
        return int(t[:2]), int(t[3:5])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_commute_trains(
    from_tiploc: str,
    to_tiploc: str,
    toc: str,
    home_walk_mins: int,
    work_walk_mins: int,
    target_work_arrival: str,
    listen_seconds: int = 20,
) -> dict:
    """
    Listen to Darwin for `listen_seconds`, then return upcoming trains from
    `from_tiploc` to `to_tiploc` for operator `toc`, with commute timing.

    Each returned train dict includes:
      - scheduled_dep / estimated_dep  (HH:MM at from_tiploc)
      - scheduled_arr / estimated_arr  (HH:MM at to_tiploc)
      - dep_delayed / arr_delayed       (bool)
      - platform                        (str or None)
      - leave_home_by                   (HH:MM = estimated_dep - home_walk_mins)
      - work_arrival                    (HH:MM = estimated_arr + work_walk_mins)
      - arrives_on_time                 (bool, True if work_arrival <= target)
      - recommended                     (bool, latest on-time train)
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    raw = _collect(listen_seconds)
    schedules, ts_updates = _parse_all(raw, toc)

    target_hhmm = _parse_hhmm(target_work_arrival)
    target_dt = (
        datetime.combine(now.date(), dtime(*target_hhmm)) if target_hhmm else None
    )

    trains = []
    for rid, sched in schedules.items():
        if sched["ssd"] != today_str:
            continue

        calling = sched["calling_points"]
        from_idx = next(
            (i for i, cp in enumerate(calling) if cp["tiploc"] == from_tiploc), None
        )
        to_idx = next(
            (i for i, cp in enumerate(calling) if cp["tiploc"] == to_tiploc), None
        )
        if from_idx is None or to_idx is None or from_idx >= to_idx:
            continue

        from_cp = dict(calling[from_idx])
        to_cp = dict(calling[to_idx])

        # Overlay real-time estimates and platform from TS updates
        if rid in ts_updates:
            ts_by_tpl = {loc["tiploc"]: loc for loc in ts_updates[rid]["locations"]}
            for tpl, cp in ((from_tiploc, from_cp), (to_tiploc, to_cp)):
                if tpl in ts_by_tpl:
                    upd = ts_by_tpl[tpl]
                    cp.update(
                        {
                            "arr_et": upd["arr_et"],
                            "dep_et": upd["dep_et"],
                            "arr_delayed": upd["arr_delayed"],
                            "dep_delayed": upd["dep_delayed"],
                        }
                    )
                    if upd["platform"]:
                        cp["platform"] = upd["platform"]

        sched_dep = from_cp.get("ptd") or from_cp.get("pta", "")
        sched_arr = to_cp.get("pta") or to_cp.get("ptd", "")
        if not sched_dep or not sched_arr:
            continue

        est_dep = from_cp.get("dep_et") or from_cp.get("arr_et") or sched_dep
        est_arr = to_cp.get("arr_et") or to_cp.get("dep_et") or sched_arr

        dep_hhmm = _parse_hhmm(est_dep)
        arr_hhmm = _parse_hhmm(est_arr)
        if not dep_hhmm or not arr_hhmm:
            continue

        dep_dt = datetime.combine(now.date(), dtime(*dep_hhmm))
        arr_dt = datetime.combine(now.date(), dtime(*arr_hhmm))
        if arr_dt < dep_dt:  # midnight crossing
            arr_dt += timedelta(days=1)

        if dep_dt < now - timedelta(minutes=1):
            continue  # already departed

        leave_home_dt = dep_dt - timedelta(minutes=home_walk_mins)
        work_arrival_dt = arr_dt + timedelta(minutes=work_walk_mins)

        trains.append(
            {
                "uid": sched["uid"],
                "rid": rid,
                "scheduled_dep": sched_dep,
                "estimated_dep": est_dep,
                "scheduled_arr": sched_arr,
                "estimated_arr": est_arr,
                "dep_delayed": from_cp.get("dep_delayed", False),
                "arr_delayed": to_cp.get("arr_delayed", False),
                "platform": from_cp.get("platform"),
                "leave_home_by": leave_home_dt.strftime("%H:%M"),
                "work_arrival": work_arrival_dt.strftime("%H:%M"),
                "arrives_on_time": target_dt is not None
                and work_arrival_dt <= target_dt,
                "recommended": False,
                "_dep_dt": dep_dt,
            }
        )

    # Also process orphan TS updates: trains with real-time data but no schedule seen
    # in this window. Darwin only re-broadcasts schedules periodically; TS updates flow
    # continuously. If a TS includes both TIPLOCs in order, treat it as a valid train.
    seen_rids = {t["rid"] for t in trains}
    for rid, ts in ts_updates.items():
        if rid in seen_rids:
            continue
        if toc and ts.get("toc") and ts["toc"] != toc:
            continue
        if ts.get("ssd") and ts["ssd"] != today_str:
            continue

        locs = ts["locations"]
        from_idx = next(
            (i for i, loc in enumerate(locs) if loc["tiploc"] == from_tiploc), None
        )
        to_idx = next(
            (i for i, loc in enumerate(locs) if loc["tiploc"] == to_tiploc), None
        )
        if from_idx is None or to_idx is None or from_idx >= to_idx:
            continue

        from_loc = locs[from_idx]
        to_loc = locs[to_idx]

        est_dep = from_loc.get("dep_et") or from_loc.get("arr_et", "")
        est_arr = to_loc.get("arr_et") or to_loc.get("dep_et", "")
        if not est_dep or not est_arr:
            continue

        dep_hhmm = _parse_hhmm(est_dep)
        arr_hhmm = _parse_hhmm(est_arr)
        if not dep_hhmm or not arr_hhmm:
            continue

        dep_dt = datetime.combine(now.date(), dtime(*dep_hhmm))
        arr_dt = datetime.combine(now.date(), dtime(*arr_hhmm))
        if arr_dt < dep_dt:
            arr_dt += timedelta(days=1)
        if dep_dt < now - timedelta(minutes=1):
            continue

        leave_home_dt = dep_dt - timedelta(minutes=home_walk_mins)
        work_arrival_dt = arr_dt + timedelta(minutes=work_walk_mins)

        trains.append(
            {
                "uid": rid,
                "rid": rid,
                "scheduled_dep": "",  # no schedule in this window
                "estimated_dep": est_dep,
                "scheduled_arr": "",
                "estimated_arr": est_arr,
                "dep_delayed": from_loc.get("dep_delayed", False),
                "arr_delayed": to_loc.get("arr_delayed", False),
                "platform": from_loc.get("platform"),
                "leave_home_by": leave_home_dt.strftime("%H:%M"),
                "work_arrival": work_arrival_dt.strftime("%H:%M"),
                "arrives_on_time": target_dt is not None
                and work_arrival_dt <= target_dt,
                "recommended": False,
                "_dep_dt": dep_dt,
            }
        )

    trains.sort(key=lambda t: t["_dep_dt"])
    for t in trains:
        del t["_dep_dt"]

    # Mark the latest on-time train as recommended
    for t in reversed(trains):
        if t["arrives_on_time"]:
            t["recommended"] = True
            break

    return {
        "trains": trains,
        "target_work_arrival": target_work_arrival,
        "fetched_at": now.strftime("%H:%M"),
        "message_count": len(raw),
    }
