# Created by:  Maria Jose Lira ; 2024-06-11
# Modified by: Maria Jose Lira ; 2024-06-11

import logging
import json
from croniter import croniter
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import datetime
from babel.dates import format_date
import os
import time

def read_json(filepath="configuration.json"):
    with open(filepath, "r") as f:
        return json.load(f)
    
def datime_to_weeek_day(datetime:datetime, short:bool=True):
    # Spanish locale
    spanish_date = format_date(datetime, "EEEE", locale='es')
    # Short day
    spanish_date = spanish_date[0:3] if short==True else spanish_date
    return(spanish_date)
    
    
if __name__ == "__main__":
    configuration = read_json()
    date = datetime.now()
    id = int(str(89440)+date.strftime('%Y%m%d%H%M'))
    print(id)
    old = 1569
    new = 1878
    total_new = 2331
    total_required = 3447
    print(datetime(datetime.now().year, datetime.now().month, datetime.now().day))
    print(datetime.today())
    pass

    

    
    

