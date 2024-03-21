# ********************************************************************************

# Title:   AutoQACT.py

# Author:  Jun Zhou, PhD
#          Emory University Radiation Oncology
#          Emory Proton Therapy Center

# Email:   jun.zhou@emory.edu
#          jzhou995@gmail.com

from BackRestore import find_TPCT_name, evaluate_QACT
import sys
import os
from datetime import datetime, timedelta
import platform
from tkinter import Tk, ttk, IntVar, Checkbutton, Label, Button, StringVar, W
from time import sleep
from pathlib import Path
import logging

from connect import get_current, await_user_input  # type: ignore -- The connect library is supplied by Raystation

current_directory = Path('W:/Users/Milo/raystation-scripts/AutoQACT')
sys.path.append(str(current_directory))

# Set up a logger and handlers.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))

file_handler = logging.FileHandler(current_directory / 'log.txt')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger.addHandler(stream_handler)
logger.addHandler(file_handler)

if platform.python_implementation() == 'IronPython':
    logger.debug('please use CPython 3.6')
    exit(0)
logger.debug(sys.version)

ui = get_current('ui')
RayVersion = int(ui.GetApplicationVersion().split('.')[0])

log_filename = current_directory / 'logs.txt'

# DICOM image storage
root_dir = current_directory / 'img'

days_earlier = 0  # import the data that exported * days earlier. As all system use date in the folder name when export Dicom images. Default should be 0, means today

additional_CTV = []
additional_control_roi = []

# to exclude these ROIs in the override_roi
override_ROIs_excluded = ['z_Contrast']


class GUI:
    def __init__(self, pid: int, patient_db, patient, caseName: str, delta_day: int) -> None:
        today = datetime.now() - timedelta(days=delta_day)  # get yesterday or before
        SYNGOVIA_Import_AEname = '__EHCSYNGOVIA__'  # Transferred from Aria
        QACT_Import_AEname = '__AN_CTAWP83695__'
        AEname_list = [SYNGOVIA_Import_AEname, QACT_Import_AEname]
        self.patient = patient
        self.series = []
        self.image_paths = []
        self.caseName = caseName

        for AEname in AEname_list:
            # AEname is in the folder name that indicate where the images coming from
            image_path = os.path.join(root_dir, today.strftime('%Y%m%d') + AEname + str(pid))
            self.image_paths.append(image_path)
            if os.path.exists(image_path):
                query = patient_db.QueryPatientsFromPath(Path=image_path, SearchCriterias={'PatientID': pid})
                logger.debug(query)
                if len(query) != 1:
                    raise ValueError(f'Did not find a unique patient with ID {pid}: found {len(query)}')
                for matching_patients in query:
                    logger.debug(f'Matching patients {matching_patients}')
                    # matching_patients = query[0]
                    studies = patient_db.QueryStudiesFromPath(Path=image_path, SearchCriterias=matching_patients)

                    for study in studies:
                        self.series += patient_db.QuerySeriesFromPath(Path=image_path, SearchCriterias=study)
                    # seriesToImport = [s for s in series if s['Modality'] == 'CT']

        mr_exam_names = [se['SeriesDescription'] for se in self.series]

        self.top = Tk()
        # Use IntVar after Tk(). Otherwise, _root error. Added for Ver 1b, used in the TK interface for check rigid registration
        self.var = IntVar(value=1)

        self.checkbox_reg = Checkbutton(self.top, text='Check Rigid Registration', variable=self.var)
        self.checkbox_reg.grid(row=1, column=2, columnspan=2)

        self.top.title('Choose the QACT examination')
        self.image_lbl = Label(self.top, text='Series to choose')
        self.image_lbl.grid(row=2, column=1, columnspan=2)
        # self.image_lbl = Label(self.top, text='Target image')
        # self.image_lbl.grid(row=2,column=1,columnspan=2)
        self.images_combobox = ttk.Combobox(self.top, values=mr_exam_names, state='readonly', width=50)
        self.images_combobox.grid(row=2, column=3, columnspan=2, sticky=W)
        # self.images_combobox2 = ttk.Combobox(self.top, values=mr_exam_names,state='readonly')
        # self.images_combobox2.grid(row=2,column=3,columnspan=3,sticky=W)

        self.button_generate = Button(self.top, text='Continue')
        self.button_generate.bind('<ButtonPress-1>', lambda event: self.status_text(event, 'started'))
        self.button_generate.bind('<ButtonRelease-1>', self.start_generate)
        self.button_generate.grid(row=6, column=5)

        self.status = StringVar()
        self.label_status = Label(self.top, textvariable=self.status)
        self.label_status.grid(row=7, column=1, columnspan=4, sticky=W)
        self.top.mainloop()

    def start_generate(self, event):
        if len(self.images_combobox.get()) == 0:
            self.status.set('Please choose series to import')
        else:
            for path in self.image_paths:
                try:
                    logger.debug(self.images_combobox.current())
                    warnings = self.patient.ImportDataFromPath(Path=path, SeriesOrInstances=[
                                                               self.series[self.images_combobox.current()]], CaseName=self.caseName)
                    logger.debug(warnings)
                    # patient.Save()
                except Exception as e:
                    logger.debug(f'Could not import patient: {e}')
                    continue
        sleep(1)
        self.top.destroy()

    def status_text(self, event, invar):
        if invar == 'started':
            self.status.set(f'Import QACT images for event {event}, please wait')

logger.info(f'Start processing patients at {datetime.now()}')

# Import current patient and current case
patient_db = get_current('PatientDB')
patient = get_current('Patient')
case = get_current('Case')

pid = patient.PatientID

logger.info(' ID = ' + pid + ' Name = ' + patient.Name + 'Case = ' + case.CaseName)

try:
    current_plan_name = get_current('Plan').Name
except:
    await_user_input('Please choose the plan you want to evaluate on and continue')
    current_plan_name = get_current('Plan').Name

TPname, TPCT_name = find_TPCT_name(case, current_plan_name, logger)

if TPCT_name:
    start_time = datetime.now()
    logger.debug(f'Start processing patient {pid} at {start_time}')

    myGUI = GUI(pid, patient_db, patient, case.CaseName, days_earlier)
    evaluate_QACT(case, TPCT_name, TPname, log_filename, RayVersion, additional_CTV, additional_control_roi,
                override_ROIs_excluded, myGUI.var.get())  # the actural plan name is the copy one with the new machine

    logger.debug(f'Done QACT analysis, time elapsed: {(datetime.now() - start_time).total_seconds()} seconds')

logger.info(f'End processing patients at {datetime.now()}')
