# file_name:   model_api_uipath.py
# created_on:  2023-0X-0X ; vicente.diaz ; juanpablo.mena
# modified_on: 2024-05-20 ; vicente.diaz

import datetime
from dataclasses import dataclass
from typing import Optional, List


@dataclass(frozen=False)
class Machine:
    id: int
    name: str
    folder_id: int
    status: Optional[str]
    is_licensed: Optional[bool]
    key: Optional[str]


@dataclass(frozen=True)
class License:
    key: str
    user_name: str
    is_licensed: bool
    machines_count: int


@dataclass
class Folder:
    id: int
    display_name: str
    machine: Optional[Machine]


@dataclass
class JobSchedule:
    id: int
    name: str
    next_start: datetime.datetime
    folder_id: int
    machine_id: str
    state: str


@dataclass
class Job:
    state: str
    process_name: str
    folder_id: int
    machine_id: Optional[int]
    creation_time: datetime.datetime

@dataclass
class Schedule:
    id: int
    next_start_at: datetime.datetime
    folder_id: int
    name: str
    enabled: bool
    runtime_type: str

@dataclass
class ScheduleRaaS:
    process_name: str
    schedule_name: Optional[str]                  = None
    schedule_id: Optional[int]                    = None
    process_id: Optional[int]                     = None
    process_cron: Optional[str]                   = None
    timezone: Optional[str]                       = None
    eta_mins: Optional[int]                       = None
    next_executions: Optional[List]               = None
    next_executions_in_time_range: Optional[List] = None
    folder_id: Optional[int]                      = None
    priority: Optional[int]                       = None