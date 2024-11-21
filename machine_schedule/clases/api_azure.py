
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
        self.resource = 'https://management.azure.com/'
        self.scope = 'https://management.azure.com/'
        # self.environment = 'Produccion-RPA'  # Nombre del ambiente específico
        self.environment ='Default-a5603b60-3a2f-4d5d-9f2d-1ec213aa643e'
        self.azure_url = f"https://southamerica.api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/{self.environment}/flows?api-version=2016-11-01"
        "https://graph.microsoft.com/v1.0/me/insights/used?$filter=resourceReference/type eq 'microsoft.flow/flow'"
    
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
            print(f'Leyendo token desde archivo: {self.token_filepath}')
            # print(self.token)
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
            "Content-Type": "application/json",
            'x-ms-client-scope': self.scope
        }       
        # Get response
        response = requests.get(request_url, headers=headers) #, data=self.payload
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
        self.get_response(request_url=self.azure_url)
        environments = self.get_response(request_url='https://southamerica.api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments?api-version=2016-11-01')
        # for env in environments['value']:
        #     print(">>>>> ",env['name'], env['properties']['displayName'])
        return (0)
        
    

if __name__ == "__main__":
    # Get token
    filepath = "process_data/token_pad.txt"
    # Api creds 
     
    client_id = 'eadeb856-64e1-43ec-9ca0-e5ed9b601dad' # EDSA
    client_secret = 'Jeo8Q~ip6Ya7qbItIZd65mCVJOmLQdg6u6PrzbgZ' # EDSA
    
    tenant_id = 'a5603b60-3a2f-4d5d-9f2d-1ec213aa643e'
    # client_id = 'c7182fca-44ef-4349-aca7-71e71a9566cd'
    # client_secret = 'tK18Q~6KV97t1CNIgR0XYVp14OnzxWY-H762ja6v'

    
    # Initialize api class
    api_pad = ApiPowerAutomate(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret, token_filepath=filepath)
    # Get folders
    api_pad.get_flows()




