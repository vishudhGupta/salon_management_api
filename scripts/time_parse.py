from datetime import datetime, time

def parse_time_str(t: str) -> time:
    return datetime.strptime(t, "%H:%M").time()

def deserialize_time_slots(day: dict) -> dict:
    for slot in day.get("time_slots", []):
        if isinstance(slot.get("start_time"), str):
            slot["start_time"] = parse_time_str(slot["start_time"])
        if isinstance(slot.get("end_time"), str):
            slot["end_time"] = parse_time_str(slot["end_time"])

    break_times = day.get("break_time", [])
    if break_times is None:
        break_times = []

    for bt in break_times:
        if isinstance(bt.get("start_time"), str):
            bt["start_time"] = parse_time_str(bt["start_time"])
        if isinstance(bt.get("end_time"), str):
            bt["end_time"] = parse_time_str(bt["end_time"])

    day["break_time"] = break_times  # assign it back just in case it was None
    return day

