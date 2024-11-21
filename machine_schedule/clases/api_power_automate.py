
# Created by:  Maria Jose Lira ; 2024-06-11
# Modified by: Maria Jose Lira ; 2024-06-25

import os
import requests
import pandas as pd
from datetime import datetime


class ApiPowerAutomate:
    def __init__(self, tenant_id:str, client_id:str, client_secret:str, token_filepath:str='token_pad.txt', tenant_name:str="Produccion"):
        self.tenant_id = tenant_id     
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_name = tenant_name
        self.token_filepath = token_filepath
        self.token = None
        self.payload = None
        self.resource = 'https://service.flow.microsoft.com/'
        # self.resource = 'https://graph.microsoft.com/'
        self.environment = 'Produccion RPA'  # Nombre del ambiente específico
        # self.subscription_id = '00efe957-57e6-4483-ac3b-a7ee44c70a75'
        # self.resource_group_name = 'your_resource_group_name'
        # self.azure_url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}/providers/Microsoft.Logic/workflows?api-version=2016-06-01"
    
    def get_token(self):
        # Url get token
        url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/token'
        # Build payload with token bearer
        self.payload = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'resource': self.resource
        }
        # Headers
        headers ={
            'Content-Type': 'application/x-www-form-urlencoded'
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
            print(f'Leyendo token desde archivo: {self.token}')
        else:
            # Request token
            response = requests.post(url, data=self.payload, headers=headers) 
            if response.status_code == 200:
                self.token = response.json()['access_token']
                with open(self.token_filepath, 'w') as file:
                    file.write(self.token)
                    print(self.token)
                    print(f'Token guardado exitosamente en {self.token_filepath}')
            else:
                print('No se pudo obtener el token. Código de estado:', response.status_code)
                print(response.text)
        return (0)
        
    def get_response(self, request_url:str=""):
        """ Get the api response """
        # Get token
        self.get_token()
        # Token bearer
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }       
        # Get response
        response = requests.get(self.azure_url+request_url, headers=headers) #, data=self.payload
        # Validate result
        if response.status_code == 200:
            data = response.json()
            print(data)
            return(data)
        else:
            error = f"Error: Unable to fetch data from the API. Status code: {response.status_code}"
            print(error)
            print(response.text)
            return(error)
        
    def get_flows(self):
        self.get_response()
        pass
        
    

if __name__ == "__main__":
    # Get token
    filepath = "process_data/token_pad.txt"
    # Api creds 
    
    tenant_id = 'a5603b60-3a2f-4d5d-9f2d-1ec213aa643e'
    client_id = 'c7182fca-44ef-4349-aca7-71e71a9566cd'
    client_secret = 'tK18Q~6KV97t1CNIgR0XYVp14OnzxWY-H762ja6v'
    
    # Initialize api class
    api_pad = ApiPowerAutomate(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret, token_filepath=filepath)
    # Get folders
    api_pad.get_flows()


