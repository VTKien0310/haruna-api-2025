from app.features.attendance.entities import (
    CheckInEntry,
    LeaveWorkEntry,
    RemoteWorkEntry,
    TimeOffEntry,
    WorkTimeEntry,
)
from app.features.pto.entities import PtoAffectEntry

type AttendanceEntry = (
    CheckInEntry | LeaveWorkEntry | RemoteWorkEntry | TimeOffEntry | WorkTimeEntry
)
type AttendanceEntryWithAffect = tuple[PtoAffectEntry, AttendanceEntry]
