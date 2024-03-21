# encoding: utf8

# Import system libraries:
from connect import *
import clr, sys
clr.AddReference("System.Windows.Forms")
clr.AddReference("PresentationFramework")
from System.Windows import MessageBox, MessageBoxImage, MessageBoxButton
from System.Windows.Forms import DialogResult

# Import local files:
from settings import plan_choices as PC, region_codes as RC, rois as ROIS
from gui_classes import radio_button as RB, radio_button_form as FORM, region_code_form as REGION_FORM
from functions import plan_functions as PF, structure_set_functions as SSF


# Lists of which number of fractions and fraction dose are allowed for a given region code, i.e treatment site. If the given values does not match the values in the list, an error is raised.
# FIXME: This function has an inherent weakness (or the error() fuction actually), that it does not
# check the pair of fraction dose and nr of fractions, it only checks the values separately.
# Furthermore, it probably shouldnt stop execution on an uknown fractionation scheme, it should just warn
# and allow the user to continue.
def check_input(ss, region_code, nr_fractions, fraction_dose):
  if region_code in RC.brain_codes:
    if region_code in RC.brain_whole_codes:
      error(nr_fractions, fraction_dose, [5, 10], [2.5, 3, 4])
    else:
      if fraction_dose > 6:
        error(nr_fractions, fraction_dose, [1, 3], [7, 8, 9, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
      else:
        error(nr_fractions, fraction_dose, [15, 17, 13, 30, 33,10], [1.8, 2, 2.67, 3, 3.4])
  elif region_code in RC.lung_codes:
    if nr_fractions in [3, 5, 8]:
      error(nr_fractions, fraction_dose, [3, 5, 8], [15, 11, 7])
    else:
      error(nr_fractions, fraction_dose, [2, 10, 11, 12, 13, 15, 16, 17, 25, 30, 33, 35], [1.5, 1.8, 2, 2.8, 3, 8.5])
  elif region_code in RC.breast_codes:
    if SSF.has_roi_with_shape(ss, ROIS.ctv_p.name):
      error(nr_fractions, fraction_dose, [15], [2.67])
    else:
      error(nr_fractions, fraction_dose, [25, 15], [2, 2.67])
  elif region_code in RC.bladder_codes:
    error(nr_fractions, fraction_dose, [3, 5, 6, 7, 10, 11, 12, 13, 25, 32], [2, 3, 3.5, 4, 7])
  elif region_code in RC.prostate_codes:
    if region_code in RC.prostate_bed_codes:
      error(nr_fractions, fraction_dose, [35], [2])
    elif SSF.has_roi_with_shape(ss, ROIS.ptv_77.name):
      error(nr_fractions, fraction_dose, [35], [2.2])
    else:
      error(nr_fractions, fraction_dose, [20, 13], [3])
  elif region_code in RC.rectum_codes:
    if SSF.has_roi_with_shape(ss, ROIS.ctv_50.name):
      error(nr_fractions, fraction_dose, [25], [2])
    else:
      error(nr_fractions, fraction_dose, [30, 5], [1.5, 5]) # Added 1.5 Gy*30, which was used in a rectum case.
  elif region_code in RC.palliative_codes:
    if fraction_dose > 8:
      error(nr_fractions, fraction_dose, [1, 3], [9, 16])


# Checks if the given region code and region code list contain only unique codes.
# If a duplicate exists, an error is raised.
def check_region_codes(region_code, region_codes):
  codes = list(region_codes)
  codes.extend([str(region_code)])
  if len(list(set(codes))) != len(codes):
    title = "Invalid region code"
    text = "Invalid region code. The same region code cannot be used multiple times!"
    MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)
    sys.exit(0)



# Collects the selected choices from the user
def collect_choices(options):
  choices = []
  r_form = FORM.RadioButtonForm(options)
  r_form.DialogResult
  # Extract and verify choices:
  if r_form.DialogResult == DialogResult.OK:
      selection = r_form.SelectedButton
  elif r_form.DialogResult == DialogResult.Cancel:
      print ("Script execution cancelled by user...")
      sys.exit(0)
  else:
      raise IOError("Unknown event occured. Exiting...")
  assert selection in options.elements

  choices.append(selection)

  if selection and selection.children:
    next_options = RB.RadioButton(selection.next_category.capitalize(), 'Select ' + selection.next_category +':' , selection.children)
    choices.extend(collect_choices(next_options))
  return choices


# Extract information from the users's input in the GUI,
def collect_delete_choice(options):
  # Setup and run GUI:
  form_r = FORM.RadioButtonForm(options)
  form_r.DialogResult

  # Extract information from the users's selections in the GUI:
  if form_r.DialogResult == DialogResult.OK:
    selection = form_r.SelectedButton
  elif form_r.DialogResult == DialogResult.Cancel:
    print ("Script execution cancelled by user...")
    sys.exit(0)
  else:
    raise IOError("Unexpected error (selection).")
  return selection


# Determines what list of technique possibilities will be given for different region codes:
def determine_choices(region_code, nr_fractions, fraction_dose):
  if region_code in RC.breast_tang_codes:
    # Chosen technique value, 'VMAT' or 'Conformal'
    technique = 'Conformal'
    # Chosen technique name, 'VMAT' or '3D-CRT'
    technique_name = '3D-CRT'
    # Chosen optimization value
    optimization = RB.RadioButton('Optimization ', 'Select optimization: ', PC.optimization)
    # Collects the selected choices from the user
    choices = collect_choices(optimization)
    opt = choices[0].value
  elif region_code in RC.conventional_and_vmat_site_codes:
    # Determine which technique choices which will appear in the form
    techniques = RB.RadioButton('Plan layout ', 'Select floor plan: ', PC.techniques)
    # Collects the selected choices from the user
    choices = collect_choices(techniques)
    # Chosen technique value, 'VMAT' or 'Conformal'
    technique = choices[0].value
    # Chosen technique name, 'VMAT' or '3D-CRT'
    technique_name = choices[0].name
    # Chosen optimization value
    opt = choices[1].value
  else:
    # Chosen technique value, 'VMAT' or 'Conformal'
    technique = 'VMAT'
    # Chosen technique name, 'VMAT' or '3D-CRT'
    technique_name = 'VMAT'
    if region_code in RC.palliative_codes and nr_fractions*fraction_dose < 55 and not PF.is_stereotactic(nr_fractions, fraction_dose) or region_code in RC.bladder_codes:
      optimization = RB.RadioButton('Optimization ', 'Select optimization: ', PC.optimization)
    else:
      optimization = RB.RadioButton('Optimization ', 'Select optimization: ', PC.optimization_simple)
    # Collects the selected choices from the user
    choices = collect_choices(optimization)
    # Chosen optimization value
    opt = choices[0].value

  results = [choices, technique, technique_name, opt]
  return results


# Gives an error if the given number of fractions and fraction dose is not in the given list of possible values
def error(nr_fractions, fraction_dose, nr_fractions_list, fraction_dose_list):
  if nr_fractions not in nr_fractions_list:
    title = ""
    text = "Invalid number of fractions."
    MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)
    sys.exit(0)
  if fraction_dose not in fraction_dose_list:
    title = ""
    text = "Invalid fraction dose."
    MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)
    sys.exit(0)

# Handles the situation of a missing target.
def handle_missing_ctv_or_ptv():
  title = "Missing ROI"
  text = "Neither CTV nor PTV is defined."
  MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)
  sys.exit(0)

# Handles the situation of a missing target.
def handle_missing_external():
  title = "Missing ROI"
  text = "No 'External' or 'Body' found."
  MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)
  sys.exit(0)

# Handles the situation of a crashed attempt to perform model based segmentation.
def handle_failed_model_based_segmentation(roi_name):
  title = "Failed model-based segmentation"
  text = "Failed to do model-based segmentation for the following ROI:" + "\n" + roi_name + "\n\n" + "The reason is that the CT images do not contain the ROI or that the program did not find it."
  MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)


# Handles the situation of a crashed attempt to move a roi that takes part of a structure set which has already been approved
def handle_failed_translation_of_roi(roi_name):
  title = "Wrong move of: " + roi_name
  text = "Failed to move " + roi_name + "\n\n" + "The reason is that a structure with the same name has been approved in a previous plan." + "\n\n" + "Check that location of " + roi_name + " makes sense!"
  MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)


# Handles the sitsuation of a missing ROI when trying to create a clinical goal.
def handle_missing_roi_for_clinical_goal(roi_name):
  title = "Missing ROI"
  text = "Failed to create 'Clinical Goal' for the following ROI:" + "\n" + roi_name + "\n\n" + "The reason is that the ROI is missing (or that the name has changed)"
  MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)


# Handles the situation of a missing ROI when trying to create a derived ROI.
def handle_missing_roi_for_derived_rois(target_name, source_names):
  title = "Missing ROI"
  text = "Failed to create the following derived ROI:" + "\n" + target_name + "\n\n" + "The reason is that the following source ROI is missing (or has changed its name):" + "\n" + str(source_names)
  MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)


# Handles the situation of a missing (or empty) ROI when trying to create an optimization objective.
def handle_missing_roi_for_objective(roi_name):
  title = "Missing ROI"
  text = "Failed to create 'Objective' for the following ROI:" + "\n" + roi_name + "\n\n" + "The reason is that the ROI is missing, the name has changed or it has not defined a volume."
  MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)

# Handles the situation of a missing target.
def handle_missing_target():
  title = "Missing target volume"
  text = "Failed to recognize target volume for this case." + "\n\n" + "The reason is probably that the naming of the target volumes deviates from the expected nomenclature."
  MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)
  sys.exit(0)

# Handles the situation where the CT selected as primary is not the most recent CT in the case.
def handle_primary_is_not_most_recent_ct():
  title = "Primary image set"
  text = "The CT series selected as the primary is not the last CT series in this case." + "\n\n" + "Check that drawing is not done on the wrong CT series."
  MessageBox.Show(text, title, MessageBoxButton.OK, MessageBoxImage.Information)

# Extract information from the users's input in the GUI, in this case, the region code of additional stereotactic targets:
def multiple_beamset_form(ss):
  # Setup and run GUI:
  form_r = REGION_FORM.RegionCodeForm(ss)
  form_r.DialogResult
  # Extract information from the users's selections in the GUI:
  if form_r.DialogResult == DialogResult.OK:
    region_codes = form_r.SelectedRegionCodes
  elif form_r.DialogResult == DialogResult.Cancel:
    print ("Script execution cancelled by user...")
    sys.exit(0)
  else:
    raise IOError("Unexpected error (selection).")
  return region_codes


def palliative_beamset_form(ss):

  beam_set = RB.RadioButton('Multiple target volumes detected', 'Select the desired layout for plan / beam set: ', PC.beam_set_choices(ss))

  choices = collect_choices(beam_set)
  return choices

