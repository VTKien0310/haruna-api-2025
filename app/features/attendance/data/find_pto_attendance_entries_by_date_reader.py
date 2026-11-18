from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import (
    CheckInEntryRecord,
    LeaveWorkEntryRecord,
    PtoAffectEntryRecord,
    RemoteWorkEntryRecord,
    TimeOffEntryRecord,
    WorkTimeEntryRecord,
)
from app.features.attendance.entities import (
    CheckInEntry,
    LeaveWorkEntry,
    RemoteWorkEntry,
    TimeOffEntry,
    WorkTimeEntry,
)
from app.features.pto.entities import PtoAffectEntry, PtoAffectEntryType


class FindPtoAttendanceEntriesByDateReader:
    async def handle(
        self, session: AsyncSession, day: date
    ) -> list[
        tuple[
            PtoAffectEntry,
            CheckInEntry
            | TimeOffEntry
            | RemoteWorkEntry
            | WorkTimeEntry
            | LeaveWorkEntry,
        ]
    ]:
        entries: list[
            tuple[
                PtoAffectEntry,
                CheckInEntry
                | TimeOffEntry
                | RemoteWorkEntry
                | WorkTimeEntry
                | LeaveWorkEntry,
            ]
        ] = []
        check_ins = await session.exec(
            select(PtoAffectEntryRecord, CheckInEntryRecord)
            .join(
                CheckInEntryRecord,
                PtoAffectEntryRecord.entry_id == CheckInEntryRecord.id,
            )
            .where(
                PtoAffectEntryRecord.entry_type == PtoAffectEntryType.CHECK_IN.value,
                CheckInEntryRecord.date == day,
            )
        )
        entries.extend(
            (PtoAffectEntry.from_db_record(affect), CheckInEntry.from_db_record(entry))
            for affect, entry in check_ins.all()
        )
        time_offs = await session.exec(
            select(PtoAffectEntryRecord, TimeOffEntryRecord)
            .join(
                TimeOffEntryRecord,
                PtoAffectEntryRecord.entry_id == TimeOffEntryRecord.id,
            )
            .where(
                PtoAffectEntryRecord.entry_type == PtoAffectEntryType.TIME_OFF.value,
                TimeOffEntryRecord.date == day,
            )
        )
        entries.extend(
            (PtoAffectEntry.from_db_record(affect), TimeOffEntry.from_db_record(entry))
            for affect, entry in time_offs.all()
        )
        remote_works = await session.exec(
            select(PtoAffectEntryRecord, RemoteWorkEntryRecord)
            .join(
                RemoteWorkEntryRecord,
                PtoAffectEntryRecord.entry_id == RemoteWorkEntryRecord.id,
            )
            .where(
                PtoAffectEntryRecord.entry_type == PtoAffectEntryType.REMOTE_WORK.value,
                RemoteWorkEntryRecord.date == day,
            )
        )
        entries.extend(
            (
                PtoAffectEntry.from_db_record(affect),
                RemoteWorkEntry.from_db_record(entry),
            )
            for affect, entry in remote_works.all()
        )
        work_times = await session.exec(
            select(PtoAffectEntryRecord, WorkTimeEntryRecord)
            .join(
                WorkTimeEntryRecord,
                PtoAffectEntryRecord.entry_id == WorkTimeEntryRecord.id,
            )
            .where(
                PtoAffectEntryRecord.entry_type == PtoAffectEntryType.WORK_TIME.value,
                WorkTimeEntryRecord.date == day,
            )
        )
        entries.extend(
            (PtoAffectEntry.from_db_record(affect), WorkTimeEntry.from_db_record(entry))
            for affect, entry in work_times.all()
        )
        leave_works = await session.exec(
            select(PtoAffectEntryRecord, LeaveWorkEntryRecord)
            .join(
                LeaveWorkEntryRecord,
                PtoAffectEntryRecord.entry_id == LeaveWorkEntryRecord.id,
            )
            .where(
                PtoAffectEntryRecord.entry_type == PtoAffectEntryType.LEAVE_WORK.value,
                LeaveWorkEntryRecord.date == day,
            )
        )
        entries.extend(
            (
                PtoAffectEntry.from_db_record(affect),
                LeaveWorkEntry.from_db_record(entry),
            )
            for affect, entry in leave_works.all()
        )
        return entries


FindPtoAttendanceEntriesByDateReaderDep = Annotated[
    FindPtoAttendanceEntriesByDateReader, Depends()
]
