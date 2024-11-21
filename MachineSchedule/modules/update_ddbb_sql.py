# Created by:  Maria Jose Lira ; 2024-06-27
# Modified by: Maria Jose Lira ; 2024-07-01


import os
import sys
import pyodbc
import pandas as pd
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utilities.utilities import *


class UpdateDDBB:
    def __init__(self, df_input):
        # configuration          = read_json()
        # self.param             = configuration["PARAMETERS"]
        # self.general_param     = self.param["GENERAL"]
        self.df_input = df_input
        self.cnxn     = None
        self.cursor   = None
        self.ddbb_conection()

    def ddbb_conection(self):
        config = (
            r'driver={SQL Server};'
            r'server=(local);'
            r'database=DevOps_Main;'
            r'trusted_connection=yes;'
            )
        # Database conection
        self.cnxn = pyodbc.connect(config)
        # Create new cursor conection
        self.cursor = self.cnxn.cursor()
        return (0)
    
    def commit_and_close_conection(self):
        self.cnxn.commit()
        self.cursor.close()
        print("Query executed...")
        return (0)
        
    def merge_datarow_uipath_ddbb(self):
        # Create query to merge uipath data to ddbb
        insert_query = """
        MERGE INTO schedule_machines_uipath AS target
        USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)) AS source (run_id, folder_id, folder_path, package_name, realease_name, trigger_name, run_date, kill_process_expresion, stop_date, machine_name, machine_id, rpa, tenant)
        ON target.run_id = source.run_id
        
        WHEN MATCHED THEN
            UPDATE SET        
                target.run_id = source.run_id,
                target.folder_id = source.folder_id,
                target.folder_path = source.folder_path,
                target.package_name = source.package_name,
                target.realease_name = source.realease_name,
                target.trigger_name = source.trigger_name,
                target.run_date = source.run_date,
                target.kill_process_expresion = source.kill_process_expresion,
                target.stop_date = source.stop_date,
                target.machine_name = source.machine_name,
                target.machine_id = source.machine_id,
                target.rpa = source.rpa,
                target.tenant = source.tenant
        WHEN NOT MATCHED BY TARGET THEN 
            INSERT (run_id, folder_id, folder_path, package_name, realease_name, trigger_name, run_date, kill_process_expresion, stop_date, machine_name, machine_id, rpa, tenant)
            VALUES (source.run_id, source.folder_id, source.folder_path, source.package_name, source.realease_name, source.trigger_name, source.run_date, source.kill_process_expresion, source.stop_date, source.machine_name, source.machine_id, source.rpa, source.tenant);
        """
        # Insert Dataframe into SQL Server:
        for index, row in self.df_input.iterrows():
            data = row.run_id,row.folder_id,row.folder_path,row.package_name,row.realease_name,row.trigger_name,row.run_date,row.kill_process_expresion,row.stop_date,row.machine_name,row.machine_id,row.rpa,row.tenant
            self.cursor.execute(insert_query, data)
        # Commit and close conection
        self.commit_and_close_conection()
        return (0)
    
    def delete_datarow_uipath_ddbb(self):
        # Create query to DELETE a row with a specific run_id
        delete_query = "DELETE FROM schedule_machines_uipath WHERE run_id = ?"
        # Ejecutar la consulta DELETE para cada run_id en el DataFrame
        for index, row in self.df_input.iterrows():
            self.cursor.execute(delete_query, row.run_id)
        # Commit and close conection
        self.commit_and_close_conection()
        return (0)

    def merge_datarow_uipath_graphs(self):
        # Create query to merge uipath data graphs to ddbb
        insert_query = """
        MERGE INTO machine_graphs_uipath  AS target
        USING (VALUES (?, ?, ?, ?, ?, ?, ?)) AS source (schedule_id, machine_id, date, week_day, busy, rpa, tenant)
        ON target.schedule_id = source.schedule_id
        
        WHEN MATCHED THEN
            UPDATE SET        
                target.schedule_id = source.schedule_id,
                target.machine_id = source.machine_id,
                target.date = source.date,
                target.week_day = source.week_day,
                target.busy = source.busy,
                target.rpa = source.rpa,
                target.tenant = source.tenant
        WHEN NOT MATCHED BY TARGET THEN 
            INSERT (schedule_id, machine_id, date, week_day, busy, rpa, tenant)
            VALUES (source.schedule_id, source.machine_id, source.date, source.week_day, source.busy, source.rpa, source.tenant);
        """
        # Insert Dataframe into SQL Server:
        for index, row in self.df_input.iterrows():
            data = row.schedule_id,row.machine_id,row.date,row.week_day,row.busy,row.rpa,row.tenant
            self.cursor.execute(insert_query, data)
        # Commit and close conection
        self.commit_and_close_conection()
        return (0)

    def delete_datarow_uipath_graphs(self):
        # Create query to DELETE a row with a specific run_id
        delete_query = f"DELETE FROM machine_graphs_uipath  WHERE schedule_id = ?"
        # Ejecutar la consulta DELETE para cada run_id en el DataFrame
        for index, row in self.df_input.iterrows():
            self.cursor.execute(delete_query, row.schedule_id)
        # Commit and close conection
        self.commit_and_close_conection()
        return (0)



if __name__ == "__main__":
    # Read excel
    df = pd.read_excel("process_data\\ddbb_graphs_uipath.xlsx") 
    print(df.head(100))
    state = UpdateDDBB(df_input=df)
    state.merge_datarow_uipath_ddbb()

