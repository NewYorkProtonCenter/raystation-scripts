# encoding: utf8

# Import system libraries:
from connect import get_current  # type: ignore
import clr
# import System.Array
# clr.AddReference("Office")
# clr.AddReference("Microsoft.Office.Interop.Excel")
# from Microsoft.Office.Interop.Excel import *

# Import local files:
from settings import def_choices as DC
from rt_classes import def_site as DS
from functions import gui_functions as GUIF, patient_model_functions as PMF, structure_set_functions as SSF
from gui_classes import radio_button as RB
from ts_classes import ts_case as TS_C


class Definition(object):
  def __init__(self, patient, case):
    self.patient = patient
    self.case = case


    pm = case.PatientModel
    examination = get_current("Examination")
    ss = PMF.get_structure_set(pm, examination)

    # Check if the last CT has been set as primary, and display a warning if not.
    success = TS_C.TSCase(case).last_examination_used_test()
    if not success:
      GUIF.handle_primary_is_not_most_recent_ct()

    # Check if any ROIs exist, and if they have a contour in the current Structure Set.
    # If there is, ask to delete rois.
    if SSF.has_roi_with_contours(ss):
      delete = RB.RadioButton('Existing ROIs discovered', 'Select', DC.delete)
      delete_choice = GUIF.collect_delete_choice(delete)
      # If the delete all rois choice was selected, delete rois.
      if not delete_choice:
        raise ValueError()
      if delete_choice.value == 'yes':
        PMF.delete_all_rois(pm)
      elif delete_choice.value == 'some':
        PMF.delete_rois_except_manually_contoured(pm, ss)


    # Create initial radiobutton object, then recursively iterate it to collect all user choices:
    regions = RB.RadioButton('Treatment region', 'Select treatment region:', DC.regions)
    choices = GUIF.collect_choices(regions)


    # Create site:
    site = DS.DefSite(pm, examination, ss, choices, targets = [], oars = [])


    # Choice 1: Which region is going to be treated?
    region = choices[0].value


    if region == 'brain':
      from def_regions import def_brain as DEF_BRAIN
      DEF_BRAIN.DefBrain(pm, examination, ss, choices, site)
    elif region == 'lung':
      from def_regions import def_lung as DEF_LUNG
      DEF_LUNG.DefLung(pm, examination, ss, choices, site)
    elif region == 'breast':
      from def_regions import def_breast as DEF_BREAST
      DEF_BREAST.DefBreast(pm, examination, ss, choices, site)
    elif region == 'bladder':
      from def_regions import def_bladder as DEF_BLADDER
      DEF_BLADDER.DefBladder(pm, examination, ss, choices, site)
    elif region == 'prostate':
      from def_regions import def_prostate as DEF_PROSTATE
      DEF_PROSTATE.DefProstate(pm, examination, ss, choices, site)
    elif region == 'rectum':
      from def_regions import def_rectum as DEF_RECTUM
      DEF_RECTUM.DefRectum(pm, examination, ss, choices, site)
    elif region == 'other':
      from def_regions import def_palliative as DEF_PALLIATIVE
      DEF_PALLIATIVE.DefPalliative(pm, examination, ss, choices, site)


    # Changes OrganType to "Other" for all ROIs in the given patient model which are of type "Undefined" or "Marker".
    PMF.set_all_undefined_to_organ_type_other(pm)
