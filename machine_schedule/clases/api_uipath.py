
# Created by:  Maria Jose Lira ; 2024-06-11
# Modified by: Maria Jose Lira ; 2024-06-25

import os
import requests
import pandas as pd
from datetime import datetime


class ApiUiPath:
    def __init__(self, client_id:str, client_secret:str, token_filepath:str='token_uipath.txt', tenant_name:str="Produccion", orch_url:str="https://cloud.uipath.com/clarochile/Produccion/orchestrator_/"):
        self.orch_url = orch_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_name = tenant_name
        self.token_filepath = token_filepath
        self.token = None
        self.payload = None
        self.scope = 'OR.Machines OR.Robots OR.Jobs OR.Monitoring OR.Folders'
    
    def get_token(self):
        # Url get token
        url = 'https://cloud.uipath.com/identity_/connect/token'
        # Build payload with token bearer
        self.payload = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope
        }
        # Verify if the token has to be reset
        if os.path.exists(self.token_filepath):
            # Get the time of last 30 minutes
            time_now = datetime.now().timestamp()
            last_30_min = time_now - (60*30)
            # Get the last time update of token file
            time_file = os.path.getmtime(filename=self.token_filepath)
            # Read token file if the time file is less than 30 minutes
            bool_read_file = True if (last_30_min) <= time_file else False
        else:
            bool_read_file = False
        # Verify if read file or request the token
        if bool_read_file:
            # Read file
            with open(self.token_filepath, 'r') as file:
                self.token = file.read().strip()
            # print(f'Leyendo token desde archivo {token_filepath}')
        else:
            # Request token
            response = requests.post(url, data=self.payload)
            if response.status_code == 200:
                self.token = response.json()['access_token']
                with open(self.token_filepath, 'w') as file:
                    file.write(self.token)
                    print(f'Token guardado exitosamente en {self.token_filepath}')
            else:
                print('No se pudo obtener el token. Código de estado:', response.status_code)
        return (0)
        
    def get_response(self, request_url:str, folder_id:str=""):
        """ Get the api response """
        # Get token
        self.get_token()
        # Token bearer
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-UIPATH-OrganizationUnitId": f"{folder_id}"
        }       
        # Get response
        response = requests.get(self.orch_url+request_url, data=self.payload, headers=headers)
        # Validate result
        if response.status_code == 200:
            data = response.json()
            # print(data)
            return(data)
        else:
            error = f"Error: Unable to fetch data from the API. Status code: {response.status_code}"
            print(error)
            return(error)
        
    def get_subfolders(self) -> pd.DataFrame:
        """Get all subfolders"""
        def valid_subfolder(folder_path:str, max_folder:int=3):
            """ Validate if the folder path belongs to Produccion and is the last subfolder (third)"""
            number_of_folders = len(folder_path.split("/"))
            if (self.tenant_name in folder_path) and (number_of_folders == max_folder):
                return True
        # Get data folders
        data = self.get_response(request_url="odata/Folders")
        dict = data["value"]
        # Add Id and FullyQualifiedName
        list_folder = []
        append_data = [list_folder.append({"folder_id": dict[inx]["Id"], "folder_path": dict[inx]["FullyQualifiedName"]}) for inx in range(len(dict)) if valid_subfolder(folder_path=dict[inx]["FullyQualifiedName"])]
        # Create DataFrame
        df_folders = pd.DataFrame(list_folder)
        return (df_folders)
    
    def get_schedule_subfolders(self):
        # Get all folders
        df_folders = self.get_subfolders()
        # Add Id, FullyQualifiedName, PackageName, ReleaseName, StartProcessCron, KillProcessExpression, MachineName and  MachineId
        list_schedule = []
        # Get data schedules
        for i in range(len(df_folders)):
            folder_path = df_folders.iloc[i]['folder_path']
            folder_id = df_folders.iloc[i]['folder_id']
            data = self.get_response(request_url=f"odata/ProcessSchedules", folder_id=folder_id)
            dict = data["value"]
            for inx in range(len(dict)):
                if dict[inx]["Enabled"] == True:
                    # Create dict
                    df_dict = {
                        "folder_id":folder_id,
                        "folder_path":folder_path,
                        "realease_id":dict[inx]["ReleaseId"],
                        "package_name":dict[inx]["PackageName"],
                        "realease_name":dict[inx]["ReleaseName"],
                        "trigger_name":dict[inx]["Name"],
                        "start_process_cron":dict[inx]["StartProcessCron"],
                        "kill_process_expresion":dict[inx]["StopProcessExpression"],
                        "machine_name":dict[inx]["MachineRobots"][0]["MachineName"],
                        "machine_id":dict[inx]["MachineRobots"][0]["MachineId"]
                    }
                    # Append dict to list
                    list_schedule.append(df_dict)
        # Create DataFrame
        df_schedule = pd.DataFrame(list_schedule)
        # print(df_schedule)
        return (df_schedule)

        

if __name__ == "__main__":
    # Get token
    filepath = "process_data/token.txt"
    # Api creds: api_credentials_mjlira
    client_id = '815b5b64-6845-4b9d-a7a8-0660e43c0d76'
    client_secret = 'O*xen!?k9ag1Z8ng'
    # Initialize api class
    api_uipath = ApiUiPath(client_id=client_id, client_secret=client_secret, token_filepath=filepath, tenant_name="MarchaBlanca")
    # Get folders
    api_uipath.get_subfolders()


