from datetime import date, time

from pydantic import BaseModel


class CreateCheckInRequest(BaseModel):
    date: date
    time: time
