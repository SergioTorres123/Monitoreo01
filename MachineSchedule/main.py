# Created by:  Maria Jose Lira ; 2024-07-05
# Modified by: Maria Jose Lira ; 2024-07-05

import os
import sys
import logging
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from modules.get_schedule_machine_uipath import GetScheduleMachineUipath

 
def main():
    state = GetScheduleMachineUipath()
    state.run_workflow()
    return 0

    
if __name__ == "__main__":
    logging.info("--- Start runing ---")
    main()
    logging.info("--- Finish runing ---")