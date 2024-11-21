# file_name:   api_uipath.py
# created_on:  2023-0X-0X ; vicente.diaz ; juanpablo.mena
# modified_on: 2024-05-20 ; vicente.diaz

import json
import datetime
import logging
import requests
from requests.adapters import HTTPAdapter
from typing import Optional, List
from model_api_uipath import Folder, License, Machine, Job, Schedule, ScheduleRaaS

# Based on UiPath API spec
MACHINE_STATUS_IDLE = "IDLE"
MACHINE_STATUS_PENDING = "PENDING"
MACHINE_STATUS_RUNNING = "RUNNING"
JOB_STATE_RUNNING = "Running"
JOB_STATE_PENDING = "Pending"

# ReadMe
#   - API model initiates only with credentials
#   - For On-premises Orch, username and password is required.
#   - For Cloud Orch, user_key, client_id and username is required.
#   - Token expires every 30 minutes


class UiPathApi:
    def __init__(self, orch_org_url, tenant_name, username="", password="", user_key="", client_id=""):
        self.base_url     = orch_org_url
        self.tenant_name  = tenant_name
        self.username     = username
        self.__password   = password
        self.user_key     = user_key
        self.client_id    = client_id
        self.bearer_token = None
        self.folders      = list()
        self.cloud_orch = True if "cloud.uipath.com" in self.base_url else False
        self.init_session()
        # Get API authentication
        self.authenticate()

    def init_session(self):
        adapter = HTTPAdapter()
        self.session = requests.Session()
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def authenticate(self):
        """
        Authenticates to the orchestrator API and saves the authentication (bearer) token.
        Token must be updated every 30 minutes.
        Raises: UiPathApiAuthenticationError if authentication fails
        """
        logging.warning(f"Using UiPath Cloud Orch: {self.cloud_orch}")
        head = {"Content-Type": "application/json"}
        if self.cloud_orch:
            logging.info("Retrieving auth token from: https://account.uipath.com/oauth/token")
            data = {"grant_type": "refresh_token",
                    "client_id":  self.client_id,
                    "refresh_token": self.user_key}
            resp = requests.post("https://account.uipath.com/oauth/token", json.dumps(data), headers=head)
        else:
            logging.info("Retrieving auth token from: " + self.base_url + "/api/Account/Authenticate")
            data = {"tenancyName": self.tenant_name,
                    "usernameOrEmailAddress": self.username,
                    "password": self.__password}
            resp = requests.post(self.base_url + "/api/Account/Authenticate", json.dumps(data), headers=head)
        if resp.status_code != 200:
            raise UiPathApiAuthenticationError(f"Could not authenticate. Status: {resp.status_code}. {resp.text}")
        res_json = resp.json()
        self.bearer_token = res_json["access_token"] if self.cloud_orch else res_json["result"]
        logging.debug(f"Auth token: {self.bearer_token}")
        logging.info('Auth token retrieved')

    def orch_request(self, request_url, request_type="GET", folder_id="", params={}, data={}, headers=None):
        if self.cloud_orch:
            url = f"{self.base_url}/{self.tenant_name}/{request_url}"
        else:
            url = f"{self.base_url}/{request_url}"
        payload = json.dumps(data)
        if not headers:
            headers = {
            'Content-Type': 'application/json',
            'X-UIPATH-TenantName': self.tenant_name,
            "Authorization": "Bearer " + self.bearer_token,
            'X-UIPATH-OrganizationUnitId': f"{folder_id}"
            }
        logging.debug(f"URL: {url}")
        #response    = requests.request(request_type, url, headers=headers, data=payload, params=params)
        response    = self.session.request(request_type, url, headers=headers, data=payload, params=params)
        status_code = response.status_code
        logging.debug(f"Status code: {status_code}")
        logging.debug(response)
        if response.text:
            if status_code not in [200, 201]:
                logging.error(json.loads(response.text)["message"])
            return [response.json(), status_code]
        else:
            return [None, status_code]

    def get_all_folders(self) -> List[Folder]:
        """
        Returns the list of folders, parsed through roles
        """
        logging.info("Getting folders ...")
        folders  = list()
        req_url  = "orchestrator_/odata/Folders" if self.cloud_orch else "odata/Folders"
        res_json,_ = self.orch_request(req_url, request_type="GET")
        for folder in res_json["value"]:
            folder_json = folder
            folder      = Folder(id=folder_json["Id"], display_name=folder_json["FullyQualifiedName"], machine=None)
            folders.append(folder)
            logging.debug(folder)
        logging.info(f"Folders retrieved: {len(folders)}")
        self.folders = folders
        return self.folders

    def get_user_folders(self) -> List[Folder]:
            """
            Returns the list of folders, parsed through roles
            """
            res_json,_ = self.orch_request(
                "/odata/Folders/UiPath.Server.Configuration.OData.GetAllRolesForUser(username='"
                f"{self.username}',skip=0,take=0)"
            )
            res = []
            for page_item in res_json["PageItems"]:
                folder_json = page_item["Folder"]
                folder = Folder(folder_json["Id"], folder_json["FullyQualifiedName"], None)
                res.append(folder)
                logging.debug(folder)
            return res
    
    def get_folder_assets(self, folder_id: int):
        logging.info(f"Getting assets from folder {folder_id}...")
        res_json,_    = self.orch_request("odata/Assets", folder_id=folder_id, request_type="GET")
        assets_dict = res_json["value"]
        logging.debug(f"Assets from folder: {assets_dict}")
        logging.info(f"Assets retrieved: {len(assets_dict)}")
        return assets_dict
    
    def create_asset(self, asset_name="", value_scope="Global", value_type="", string_value="", bool_value=False, int_value=10, 
                     cred_user="", cred_pass="", description="", folder_id=10):
            logging.info(f"Creating asset {asset_name} in folder {folder_id}")
            data = {"Name": asset_name, "ValueScope": value_scope, "ValueType": value_type, "StringValue": string_value, "BoolValue": bool_value, "IntValue": int_value,
                    "CredentialUsername": cred_user, "CredentialPassword": cred_pass, "Description": description}
            resp, status_code=self.orch_request("odata/Assets", request_type="POST", folder_id=folder_id, data=data)
            if status_code in [200,201]:
                logging.info("Asset created successfully")
            else:
                raise CannotCreateAsset(
                f"Could not create asset {asset_name}. Status: {status_code}. {resp}")

    def get_named_user_licenses(self, robot_type: str) -> List[License]:
        """Retrieve unattended robots to obtain their respective machine info"""
        res_json,_ = self.orch_request(
            f"/odata/LicensesNamedUser/UiPath.Server.Configuration.OData.GetLicensesNamedUser(robotType='{robot_type}')"
        )
        logging.debug('Unattended robots retrieved')
        resp_arr = res_json["value"]
        licenses = [License(d["Key"], d["UserName"], d["IsLicensed"], d["MachinesCount"]) for d in resp_arr]
        logging.debug("Licenses:")
        for lic in licenses:
            logging.debug(f"- {lic}")
        return licenses

    def get_machine_of_folder(self, folder_id: int, license_type: str) -> Optional[Machine]:
        """
        Returns the machine assigned to a folder, or None if no machine has been set up.

        Note that the switcher assumes that there are either 0 or 1 machines set up per folder.
        If there is no machine, the processes in this folder won't run of course.

        https://orch.sisuadigital.com/swagger/index.html#/Folders/Folders_GetMachinesForFolderByKey

        Parameters
        ----------

        folder: the folder whose machines are to be returned
        license_type: the license type, e.g. 'Unattended'

        Returns
        -------
        the machine assigned to a folder

        Raises UiPathApiUnexpectedResponseError if multiple machines have been set up for folder.
        """
        res_json,_ = self.orch_request(
            f"/odata/Folders/UiPath.Server.Configuration.OData.GetMachinesForFolder(key={folder_id})?$filter=IsAssignedToFolder")
        all_machines = res_json["value"]
        slot_field_name = license_type + "Slots"  # e.g. UnattendedSlots
        assigned_machines = [m for m in all_machines if (m["IsAssignedToFolder"] and m[slot_field_name] > 0)]
        logging.debug(f"Assigned machines: {assigned_machines}")
        if len(assigned_machines) > 1:
            raise UiPathApiUnexpectedResponseError(
                f"Expected exactly 1 machine assigned for folder {folder_id}, got {len(assigned_machines)}. "
                f"{assigned_machines}")
        if len(assigned_machines) == 0:
            return None
        m = assigned_machines[0]
        return Machine(m["Id"], m["Name"], folder_id, None, None, None)

    def get_schedules(self, folder_id: int):
        """
        Retrieves a sorted scheduler_info list with all the jobs already scheduled and enabled
        in the folders to which the user has access.

        Returns
        -------
        Scheduled jobs
        """
        req_url="/odata/ProcessSchedules?$filter=Enabled"
        res_json,_ = self.orch_request(request_url=req_url, folder_id=folder_id)
        value = res_json["value"]
        schedules = []
        for s in value:
            schedule = Schedule(
                int(s["Id"]),
                datetime.datetime.fromisoformat(s["StartProcessNextOccurrence"].replace("Z", "")),
                folder_id,
                s["Name"],
                s["Enabled"],
                s["RuntimeType"]
            )
            logging.debug(f"- {schedule}")
            schedules.append(schedule)
            # TODO warn if folder with schedules has no machines
        return schedules

    def get_jobs(self, state: str) -> List[Job]:
        """
        Parameters
        ----------
        state : Either "Successful", "Pending", "Faulted" or "Stopped".

        Returns
        -------
        res : list of jobs objects with the given state, ordered by creation time ascending (from oldest to newest).
        """
        # TODO add sort by CreationTime
        req_url=f"/odata/Jobs?$filter=State eq '{state}'"
        res_json,_ = self.orch_request(request_url=req_url)
        res = []
        for jobs in res_json['value']:
            job = Job(
                jobs['State'],
                jobs['ReleaseName'],
                jobs['OrganizationUnitId'],
                None,
                datetime.datetime.fromisoformat((jobs["CreationTime"].split(".")[0]).replace("Z",""))  # 2021-07-20T19:41:00.86Z
            )
            logging.debug(job)
            res.append(job)
        return res

    def get_active_jobs_from_machine(self, machine_id: int, machine_folder_id: int) -> List[Job]:
        """
        Parameters
        ----------
        machine: the machine whose jobs are to be returned
        job_state : the Job state; either "Successful", "Pending","Faulted" or "Stopped".

        Returns
        -------
        list of Jobs with all states from the same folder as the machine specified
        """
        res_json,_ = self.orch_request(f"/odata/Jobs?$filter=State eq '{JOB_STATE_PENDING}' or State eq '{JOB_STATE_RUNNING}'", folder_id=machine_folder_id)
        res = []
        for jobs in res_json['value']:
            job = Job(
                jobs['State'],
                jobs['ReleaseName'],
                machine_folder_id,
                machine_id,
                datetime.datetime.fromisoformat((jobs["CreationTime"].split(".")[0]).replace("Z",""))  # 2021-07-20T19:41:00.86Z
            )
            logging.debug(job)
            res.append(job)
        return res

    def get_machine_status(self, machine_id: int, machine_folder_id: int) -> str:
        """Get the status of the machine depending if it has running jobs"""
        jobs_machine=self.get_active_jobs_from_machine(machine_id, machine_folder_id)
        if next((job for job in jobs_machine if job.state==JOB_STATE_RUNNING),None)!=None:
            logging.debug(f"Machine {machine_id} is running")
            return MACHINE_STATUS_RUNNING
        elif next((job for job in jobs_machine if job.state==JOB_STATE_PENDING),None)!=None:
            logging.debug(f"Machine {machine_id} is pending")
            return MACHINE_STATUS_PENDING
        else:
            logging.debug(f"Machine {machine_id} is IDLE")
            return MACHINE_STATUS_IDLE

    def get_machine_key_and_license_status(self, machines: List[Machine], robot_type: str) -> List[Machine]:
        """
        Get the machine key and status of the license assigned to the specific machine

        Parameters
        ----------
        machines: list of machines
        robot_type: the robot type (e.g. 'Unattended') of the licence being queried

        Returns
        -------
        machines: the same list of machines recieved but with the is_licensed and key fields filled.
        """
        res_json,_ = self.orch_request(
            f"/odata/LicensesRuntime/UiPath.Server.Configuration.OData.GetLicensesRuntime(robotType='{robot_type}')")
        all_machines = res_json['value']
        for machine in machines:
            try:
                is_licensed = next((m['IsLicensed'] for m in all_machines if m['MachineId'] == machine.id), None)
                key = next((m['Key'] for m in all_machines if m['MachineId'] == machine.id), None)
                if key is None:
                    raise UiPathApiReturnedNoLicenseForMachine(f"Could not fetch licenses runtime for {machine}")
                logging.debug('Machine license status retrieved')
                machine.is_licensed=is_licensed
                machine.key=key
            except Exception as e:
                logging.warning(f"{machine} has caused an error: {e}")
                machines.remove(machine)
        return machines

    def get_machine_license_status(self, machine_id: int, robot_type: str) -> bool:
        """Get the status of the license assigned to the specific machine"""
        res_json,_ = self.orch_request(
            f"/odata/LicensesRuntime/UiPath.Server.Configuration.OData.GetLicensesRuntime(robotType='{robot_type}')")
        all_machines = res_json['value']
        is_licensed = next((m['Key'] for m in all_machines if m['MachineId'] == machine_id), None)
        if is_licensed is None:
            raise UiPathApiReturnedNoLicenseForMachine(f"Could not fetch licenses runtime for {machine_id}")
        logging.debug(f'Machine license status retrieved: {is_licensed}')
        return is_licensed

    def get_machine_key(self, machine_id: int, robot_type: str) -> bool:
        """Get the key assigned to the specific machine"""
        res_json,_ = self.orch_request(
            f"/odata/LicensesRuntime/UiPath.Server.Configuration.OData.GetLicensesRuntime(robotType='{robot_type}')")
        all_machines = res_json['value']
        key = next((m['Key'] for m in all_machines if m['MachineId'] == machine_id), None)
        if key is None:
            raise UiPathApiReturnedNoLicenseForMachine(f"Could not fetch licenses runtime for {machine_id}")
        logging.debug(f'Machine key retrieved: {key}')
        return key

    def get_licenses(self):
        """Retrieve unattended robots to obtain their respective machine info"""
        res_json,_ = self.orch_request("/odata/Settings/UiPath.Server.Configuration.OData.GetLicense")
        logging.debug(f'Licenses retrieved: {res_json}')
        return res_json

    def get_licenses_used_by_type(self, license_type: str) -> int:
        used_licenses_by_type = self.get_licenses()["Used"]
        logging.debug(f"Used licenses: {used_licenses_by_type}")
        return int(used_licenses_by_type[license_type])

    def get_licenses_allowed_by_type(self, license_type: str) -> int:
        allowed_licenses_by_type = self.get_licenses()["Allowed"]
        logging.debug(f"Allowed licenses: {allowed_licenses_by_type}")
        return int(allowed_licenses_by_type[license_type])

    def toggle_machine(self, machine_id: int, machine_name: str, machine_key: str, enabled: bool, robot_type: str):
        """
        Enables or disables a machine in order to free or allow it a capture available licenses

        Parameters
        ----------
        robot_type: the type of license runtime to enable/disable (e.g. "Unattended")
        machine: the machine to enable or disable
        enabled: True to enable machine, or False to disable it

        Raises
        -------
        CannotToggleMachineError if toggling machine fails
        """
        head = {"Content-Type": "application/json",
                "Authorization": "Bearer " + self.bearer_token,
                'X-UIPATH-TenantName': self.tenant_name
                }
        data = {
            "key": machine_key,
            "robotType": robot_type,
            "enabled": enabled
        }
        url = f"odata/LicensesRuntime('{machine_name}')/UiPath.Server.Configuration.OData.ToggleEnabled"
        logging.info(f"Toggling {'on' if enabled else 'off'} machine {machine_name} ({machine_id})")
        resp,status_code = self.orch_request(url, request_type="POST", data=data, headers=head)
        if status_code != 200:
            raise CannotToggleMachineError(
                f"Could not toggle {'on' if enabled else 'off'} machine {machine_name}. Status: {status_code}. {resp}")
        logging.info(f"Toggled machine {machine_name} {'on' if enabled else 'off'}")

    def get_robots(self):
        logging.info("Getting robots ...")
        req_url = "odata/Sessions/UiPath.Server.Configuration.OData.GetGlobalSessions?$expand=Robot($expand=License)"
        robots  = list()
        res_json,_ = self.orch_request(req_url, request_type="GET")
        for robot in res_json["value"]:
            robots.append(robot)
            logging.debug(robot)
        logging.info(f"Robots retrieved: {len(robots)}")
        return robots

    def api_delete_schedule(self, schedule_id: int):
        """ Makes the API request to delete a previously scheduled process"""
        head = {"Content-Type": "application/json",
                "Authorization": "Bearer " + self.bearer_token,
                'X-UIPATH-TenantName': self.tenant_name}
        req_url="odata/ProcessSchedules("+str(schedule_id)+")"
        #req = requests.delete(self.base_url + "/odata/ProcessSchedules("+str(schedule_id)+")", headers=head)
        req, status_code = self.orch_request(req_url,request_type="DELETE",headers=head)
        if status_code in [200,201]:
            logging.info(f'Schedule {schedule_id} removed')
        else:
            logging.info(f'Schedule {schedule_id} could not be removed')

    def get_process_id(self, process_name: str):
        res_json,_ = self.orch_request("/odata/Releases?$filter=%20Name%20eq%20'"+process_name+"'")
        logging.debug('Licenses retrieved')
        resJson = res_json['value']
        if len(resJson) > 1:
            logging.warning("Two or more processes with the same name")
            return None, None
        elif len(resJson) == 1:
            return resJson[0]['Id'], resJson[0]['OrganizationUnitId']
        else:
            logging.error("No process found")
            return None, None

    def get_process_description(self):  # return dict(process_name[str]: exe_time[int])
        releases,_         = self.orch_request(request_url="/odata/Releases")
        process2exe_time = {prc["Name"]: prc["Description"] for prc in releases["value"]}
        return process2exe_time

    def schedule_in_utc(self, schedule_name: str, process_id: int, process_name: str, process_cron: str, folder_id: int) -> bool:
        """ Makes the API request to schedule a specifc process"""
        head = {"Content-Type": "application/json",
                "Authorization": "Bearer " + self.bearer_token,
                'X-UIPATH-TenantName': self.tenant_name,
                'X-UIPATH-OrganizationUnitId': str(folder_id)}
        data = {"Enabled": True,
                "Name": schedule_name, "ReleaseId": process_id, "ReleaseName": process_name,
                "StartProcessCron": process_cron, "StartProcessCronDetails": "{}",
                "StartStrategy": 1, "ExecutorRobots": [], "StopProcessExpression": "",
                "StopStrategy": None, "TimeZoneId": 'UTC'}
        req_url="/odata/ProcessSchedules"
        req, status_code = self.orch_request(request_url=req_url,request_type="POST", data=data, headers=head)
        if status_code not in [200,201]:
            if status_code == 409:
                logging.error("Schedule conflict or process already scheduled")
                return False
            else:
                logging.error(f"Error scheduling process {process_name}. Msg: {req}")
                return False
        else:
            logging.info(f"Process {process_name} successfully scheduled")
            return True

    def retrieve_scheduled_jobs_by_folder(self, only_enabled: bool, folder_id: int) -> List[ScheduleRaaS]:
        scheduled_info = []
        res_json,_     = self.orch_request("/odata/ProcessSchedules", folder_id=folder_id)
        resJson        = res_json['value']
        for i in range(len(resJson)):
            schedule = ScheduleRaaS(schedule_name=resJson[i]['Name'], schedule_id=resJson[i]['Id'],
                                    process_name=resJson[i]['ReleaseName'], process_id=resJson[i]['ReleaseId'],
                                    process_cron=resJson[i]['StartProcessCron'], timezone=resJson[i]['TimeZoneId'],
                                    eta_mins=None, next_executions=None, next_executions_in_time_range=None,
                                    folder_id=folder_id, priority=None)
            if only_enabled and resJson[i]['Enabled']:
                scheduled_info.append(schedule)
                logging.debug(schedule)
            elif not only_enabled:
                scheduled_info.append(schedule)
                logging.debug(schedule)
        logging.debug(f"Folder id  {folder_id}: retrieved {len(scheduled_info)} scheduled jobs")
        return scheduled_info

    def delete_schedule(self, schedule_id: int, folder_id: int):
        """ Makes the API request to delete a previously specifc schedule"""
        head = {"Content-Type": "application/json",
                "Authorization": "Bearer " + self.bearer_token,
                'X-UIPATH-TenantName': self.tenant_name,
                'X-UIPATH-OrganizationUnitId': str(folder_id)}
        req_url=f"odata/ProcessSchedules({schedule_id})"
        req, status_code = self.orch_request(request_url=req_url,request_type="DELETE",headers=head)
        if status_code == 204:
            logging.info(f"Schedule {schedule_id} successfully deleted")
            return True
        else:
            logging.error(f"Error deleting schedule {schedule_id}. Msg: {req}")
            return False

    def get_latest_job_by_schedule_id(self, schedule_id: str):
        """
        Fetches latest job of a schedule from UiPath API

        Parameters
        ----------
        schedule_id: the schedule ID which was starting this job

        Returns
        -------
        """
        req_url=f"odata/Jobs?$top=1&$filter=StartingScheduleId eq {schedule_id}&$orderby=StartTime desc"
        res_json,_ = self.orch_request(req_url)
        if len(res_json) > 1:
            raise UiPathApiUnexpectedResponseError(
                f"API job should return only one job for schedule {schedule_id}. Received {len(res_json)}")
        if len(res_json) == 1:
            return res_json[0]
        return None


class UiPathApiError(Exception):
    pass

class UiPathApiAuthenticationError(UiPathApiError):
    pass

class UiPathApiHttpGetError(UiPathApiError):
    pass

class UiPathApiReturnedNoLicenseForMachine(UiPathApiHttpGetError):
    pass

class UiPathApiUnexpectedResponseError(UiPathApiError):
    pass

class CannotCreateAsset(UiPathApiError):
    pass

class UiPathApiHttpPostError(UiPathApiError):
    pass

class CannotToggleMachineError(UiPathApiHttpPostError):
    pass
