#********************************************************************************

# Title:   AutoQACT.py

# Author:  Jun Zhou, PhD
#          Emory University Radiation Oncology
#          Emory Proton Therapy Center

# Email:   jun.zhou@emory.edu
#          jzhou995@gmail.com

# Date:
# Ver. 1a  2021.06.16   Initial version
# Ver. 1b  2021.11.14   Add opition for checking rigid registration
#                       Changed BackRestore.pyx, structure_set_functions.pyx
# Ver. 1c  2021.12.22   Add override_ROIs_excluded = ['z_Contrast'] to excldue some other ROIs in the override list. Not clinically released yet
#          2022.02.10   add override_ROIs_excluded to evaluate_QACT argument list
# Ver. 1d  2022.01.16   Removed 'Body' from additional_control_roi in line 120. The body contour is auto find now. Not clinically released yet
#          2022.02.10   Add station_name variable for future 11B in line 107
# Ver. 1e  2023.01.24   Set check registration by default. On line 161, self.var = IntVar(value = 1)

# Purpose: Perform QACT evaluation with 1 button click

# Notes:   Tested in RS9A and RS10B.
#          Please save the patient and load the plan before running the script
#          Not working for 4D evaluation yet. Can only evalute the average CT
























#Start from line 50
#********************************************************************************

from connect import *
from System.Windows import *
import sys, time, os, re
from datetime import datetime, timedelta
from random import choice
from string import ascii_uppercase
import platform
from tkinter import *
from tkinter import ttk
from time import sleep

sys.path.append(r'\\euh\\ehc\\shares\\RadOnc\\Documents\\RO PHYSICS\\ProtonPhysics\\Scripts_DoNotMove\\RaystationLibraries\\EPTC\\')
from BackRestore import *

























from System.Drawing import (Color, ContentAlignment, Font, FontStyle, Point)
# from System.Windows.Forms import (Application, BorderStyle, Button, CheckBox, DialogResult, Form, FormBorderStyle, Label, Panel, RadioButton, TextBox)
import math

import patient_model_functions as PMF
import structure_set_functions as SSF
import rois as ROIS
error_message_header = "Missing information / setup"

if platform.python_implementation() == "IronPython":
    print("please use CPython 3.6")
    exit(0)
print (sys.version)

ui = get_current('ui')
RayVersion = int(ui.GetApplicationVersion().split('.')[0])
station_name = 'StationName' if RayVersion < 11 else 'Station Name'

log_filename = r'\\euh\\ehc\\shares\\RadOnc\\Documents\\RO PHYSICS\\ProtonPhysics\\Scripts_DoNotMove\\FinalReviewsOutput\\Process logfile1.txt'

root_dir = r"\\prd-ray-sql1\DicomImageStorage"

current_patient = True

DAYs_Earlier = 0    #import the data that exported * days earlier. As all system use date in the folder name when export Dicom images. Default should be 0, means today

additional_CTV = [] #don't use [''], since when extend a list with [''], it add the '' to the end. While extend '' won't.
# additional_CTV = ['CTV45pp_NEW', 'CTV37.5pp_NEW', 'GTV_NEW']

additional_control_roi = ['']

#to exclude these ROIs in the override_roi
override_ROIs_excluded = []
override_ROIs_excluded = ['z_Contrast']

csv_name = ''
SYNGOVIA_Import_AEname = '__EHCSYNGOVIA__'  #Transferred from Aria
QACT_Import_AEname = '__AN_CTAWP83695__'

class GUI:
    def __init__(self, pid, patient_db, patient, caseName, delta_day):
    # today=datetime.today()
        today=datetime.today()-timedelta(days=delta_day)#get yesterday or before
        AEname_list = [SYNGOVIA_Import_AEname, QACT_Import_AEname]
        self.patient = patient
        self.series=[]
        self.path = []
        self.caseName = caseName

        for AEname in AEname_list:
            current_path = os.path.join(root_dir, today.strftime('%Y%m%d') + AEname + pid)  #AEname is in the folder name that indicate where the images coming from
            self.path.append (current_path)
            if os.path.exists(current_path):
                query = patient_db.QueryPatientsFromPath(Path=current_path, SearchCriterias = {'PatientID' : pid})
                print(query)
                assert len(query) == 1, "Found more than 1 patient with ID{}".format(pid)
                for matching_patients in query:
                    print('ok2, matching patients{0}'.format(matching_patients))
                    # matching_patients = query[0]
                    studies = patient_db.QueryStudiesFromPath(Path=current_path, SearchCriterias = matching_patients)

                    for study in studies:
                        self.series += patient_db.QuerySeriesFromPath(Path = current_path, SearchCriterias = study)
                    #seriesToImport = [s for s in series if s['Modality'] == 'CT']

        mr_exam_names = [se['SeriesDescription'] for se in self.series]

        self.top = Tk()
        self.var = IntVar(value = 1)  #Use IntVar after Tk(). Otherwise, _root error. Added for Ver 1b, used in the TK interface for check rigid registration

        self.checkbox_reg = Checkbutton(self.top, text='Check Rigid Registration', variable = self.var)
        self.checkbox_reg.grid(row = 1, column = 2, columnspan =2)

        self.top.title('Choose the QACT examination')
        self.image_lbl = Label(self.top, text="Series to choose")
        self.image_lbl.grid(row=2,column=1,columnspan=2)
        # self.image_lbl = Label(self.top, text="Target image")
        # self.image_lbl.grid(row=2,column=1,columnspan=2)
        self.images_combobox = ttk.Combobox(self.top, values=mr_exam_names,state='readonly', width=50)
        self.images_combobox.grid(row=2,column=3,columnspan=2,sticky=W)
        # self.images_combobox2 = ttk.Combobox(self.top, values=mr_exam_names,state='readonly')
        # self.images_combobox2.grid(row=2,column=3,columnspan=3,sticky=W)

        self.button_generate=Button(self.top, text='Continue')
        self.button_generate.bind("<ButtonPress-1>",lambda event: self.status_text(event,'started'))
        self.button_generate.bind("<ButtonRelease-1>",self.start_generate)
        self.button_generate.grid(row=6,column=5)

        self.status=StringVar()
        self.label_status=Label(self.top,textvariable=self.status)
        self.label_status.grid(row=7,column=1,columnspan=4,sticky=W)
        self.top.mainloop()

    def start_generate(self,event):
        if len(self.images_combobox.get())==0:
            self.status.set('Please choose series to import')
        else:
            for path in self.path:
                try:
                    print(self.images_combobox.current())
                    warnings = self.patient.ImportDataFromPath(Path=path, SeriesOrInstances = [self.series[self.images_combobox.current()]], CaseName = self.caseName)
                    # patient.Save()
                except:
                    continue
                    # raise Exception('Could not import patient: {0}'.format(exception))
        sleep(1)
        self.top.destroy()
    def status_text(self,event,invar):
        if invar=='started':
            self.status.set('Import QACT images, please wait')

def import_QACT_entrance(current_patient, csv_file_name, delta_day): #current_patient: true or false, if false, get patients in the csv_file
    #use current patient and current case
    TPCT_name = ''
    patient_db = get_current('PatientDB')
    date_format = "%m/%d/%y"
    today=datetime.today()
    current_patient = True

    if current_patient:
        patient = None
        try:
            patient = get_current("Patient")
        except Exception as e:
            MessageBox.Show("No patient loaded.",error_message_header)
            sys.exit()

        #
        # Check that a case is loaded
        # In case no, the script will terminate
        #
        case = None
        try:
            case = get_current("Case")
        except Exception as e:
            MessageBox.Show("No case active.",error_message_header)
            sys.exit()

        pid = patient.PatientID
        with open(log_filename, 'a') as f:
            f.write('\n' + ' ID = ' + pid + ' Name = ' + patient.Name + 'Case = ' + case.CaseName)
            f.close()
        try:
            current_plan_name = get_current('Plan').Name

        except:
            await_user_input('Please choose the plan you want to evaluate on. Continue')
            current_plan_name = get_current('Plan').Name

        TPname, TPCT_name = find_TPCT_name(case, current_plan_name, log_filename)


        time1 = time.time()
        print ('Start processing patient ' + pid + ' at ' + str(datetime.today()))

        myGUI = GUI(pid, patient_db, patient, case.CaseName, delta_day)

        if TPCT_name != '':
            evaluate_QACT(case, TPCT_name, TPname, log_filename, RayVersion, additional_CTV, additional_control_roi, override_ROIs_excluded, myGUI.var.get())#the actural plan name is the copy one with the new machine

        time2 = time.time()
        print("Done QACT analysis, time elapsed: " + str(round(time2-time1, 1)) + " seconds.")
        # patient.Save()

with open(log_filename, 'a') as f:
    f.write('\n' + 'Start processing patients at ' + str(datetime.today()))
    f.close()

import_QACT_entrance(current_patient, csv_name, DAYs_Earlier) #True: current patient, false: csv file

with open(log_filename, 'a') as f:
    f.write('\n' + 'End processing patients at ' + str(datetime.today()))
    f.close()
