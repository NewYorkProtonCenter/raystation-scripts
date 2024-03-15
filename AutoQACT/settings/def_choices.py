# encoding: utf8

# Import local files:
import property as P

# Regions:
brain = P.Property('Brain', 'brain', next_category='scope', default = True)
lung = P.Property('Lung', 'lung', next_category = 'intention')
breast = P.Property('Breast', 'breast', next_category = 'scope')
bladder = P.Property('Bladder', 'bladder')
prostate = P.Property('Prostate', 'prostate', next_category = 'scope')
rectum = P.Property('Rectum', 'rectum', next_category = 'fractionation')
other = P.Property('Palliative/Skeleton - other', 'other', next_category = '')


# Brain: Scope:
brain_whole = P.Property('Whole brain', 'whole', parent=brain, default = True)
brain_partial = P.Property('Partial brain', 'part', parent=brain, next_category='diagnose')
brain_stereotactic = P.Property('Stereotactic','stereotactic', parent = brain, next_category ='number of target volumes')

# Brain: Partial: Diagnosis:
brain_partial_diag1 = P.Property('Glioblastoma WHO grade IV', 'glio', parent=brain_partial, default = True)
brain_partial_diag2 = P.Property('Anaplastic astrocytoma WHO grade III', 'astro', parent=brain_partial)
brain_partial_diag3 = P.Property('Atypical and anaplastic meningioma', 'meningioma', parent=brain_partial)

# Brain: Stereotactic
brain_stereo_nr1 = P.Property('1','one', parent = brain_stereotactic, default = True)
brain_stereo_nr2 = P.Property('2','two', parent = brain_stereotactic)
brain_stereo_nr3 = P.Property('3','three', parent = brain_stereotactic)
brain_stereo_nr4 = P.Property('4','four', parent = brain_stereotactic)


# Lung
lung_curative = P.Property('Curative', 'curative', parent = lung, next_category = 'diagnose', default = True)
lung_palliative = P.Property('Palliative','palliative', parent = lung, next_category = '')
lung_stereotactic = P.Property('Stereotactic', 'stereotactic', parent = lung, next_category ='side')

# Lung curative:
lung_nsclc = P.Property('Non-small cell lung cancer / Small cell lung cancer (with 4DCT)','4dct', parent = lung_curative, default = True)
lung_sclc = P.Property('Small cell lung cancer (without 4DCT)','sclc', parent = lung_curative)
lung_pancoast =P.Property('Pancoast', 'pancoast', parent = lung_curative)
lung_postop =P.Property('Postoperative', 'postop', parent = lung_curative)

# Lung stereotactic:
stereo_lung_right = P.Property('Right','right', parent = lung_stereotactic, next_category ='number of target volumes', default = True)
stereo_lung_left = P.Property('Left','left', parent = lung_stereotactic, next_category ='number of target volumes')

for side in [stereo_lung_right, stereo_lung_left]:
  lung_stereo_nr1 = P.Property('1','one', parent = side, default = True)
  lung_stereo_nr2 = P.Property('2','two', parent = side)
  lung_stereo_nr3 = P.Property('3','three', parent = side)


# Lung palliative:
lung_with_4dct = P.Property('With 4DCT', True, parent = lung_palliative, default = True)
lung_without_4dct = P.Property('Without 4DCT', False, parent = lung_palliative)


#Breast:
breast_partial = P.Property('Partial breast', 'part', parent = breast, next_category = '')
breast_tangential = P.Property('tangential/chest wall', 'tang', parent = breast, next_category = '', default = True)
breast_locoregional = P.Property('Chest / chest wall and regional lymph nodes', 'reg', parent = breast, next_category ='side')
breast_imn = P.Property('Chest / chest wall, regional lymph nodes and parasternal glands', 'imn', parent = breast, next_category = 'side')


# Breast tangential: Side:
breast_right_tang = P.Property('Right','right', parent = breast_tangential, next_category = '', default = True)
breast_left_tang = P.Property('Left','left', parent = breast_tangential, next_category = '')


breast_right_part = P.Property('Right','right', parent = breast_partial, default = True)
breast_left_part = P.Property('Left','left', parent = breast_partial)


# Breast youth boost:
for side in [breast_right_tang, breast_left_tang]:
  breast_with_boost_tang = P.Property('With youth boost',True, parent = side)
  breast_without_boost_tang = P.Property('Without youth boost', False, parent = side, default = True)


# Breast regional:
for b in [breast_locoregional, breast_imn]:
  breast_right = P.Property('Right','right', parent = b, next_category = '', default = True)
  breast_left = P.Property('Left','left', parent = b, next_category = '')
  for side in [breast_right, breast_left]:
    # Breast: Fractionation:
    breast_hypo = P.Property('Hypofractionation', 'hypo', parent = side, next_category ='', default = True)
    breast_normo = P.Property('Conventional fractionation', 'normo', parent = side, next_category ='')
    # Breast youth boost:
    for frac in [breast_hypo, breast_normo]:
      breast_with_boost = P.Property('With youth boost',True, parent = frac)
      breast_without_boost = P.Property('Without youth boost', False, parent = frac, default = True)


# Prostate:
prostate_normal = P.Property('Prostate', 'prostate', parent = prostate, next_category ='', default = True)
prostate_bed = P.Property('Prostate bed', 'bed', parent = prostate, next_category ='')

# Prostate: Fractionation:
prostate_hypo = P.Property('Hypofractionation', 'hypo', parent = prostate_normal, next_category ='', default = True)
prostate_normo = P.Property('Conventional fractionation', 'normo', parent = prostate_normal, next_category ='')


# Prosate/bed: Lymph nodes:
for p in [prostate_normo, prostate_bed]:
  prostate_without_ln =  P.Property('Without lymph nodes', 'without',  parent = p, next_category ='', default = True)
  prostate_with_ln =  P.Property('With lymph nodes', 'with', parent = p, next_category ='')
  prostate_with_ln_boost =  P.Property('With lymph nodes and boost to positive lymph node', 'with_node', parent = p, next_category ='')


# Rectum:
rectum_hypo = P.Property('Hypofractionation', 'hypo', parent = rectum, next_category ='')
rectum_normo = P.Property('Conventional fractionation with SIB', 'normo', parent = rectum, next_category ='scope', default = True)

# Rectum normo: Nodes:
rectum_with_nodes = P.Property('With pathologically enlarged lymph nodes in the groin', True, parent = rectum_normo)
rectum_without_nodes = P.Property('Without pathologically enlarged lymph nodes in the groin', False, parent = rectum_normo, default = True)


# Other (palliative): SBRT:
other_stereotactic = P.Property('Stereotactic', True, parent =other, next_category = 'region')
other_non_stereotactic = P.Property('Non Stereotactic', False, parent = other, next_category = 'region', default = True)

# Other non-SBRT: Region:
other_head = P.Property('Head', 'head', parent=other_non_stereotactic, next_category = 'number of target volumes')
other_neck = P.Property('Neck', 'neck', parent=other_non_stereotactic, next_category = 'number of target volumes')
other_thorax = P.Property('Thorax', 'thorax', parent=other_non_stereotactic, next_category = 'number of target volumes')
other_abdomen = P.Property('Abdomen', 'abdomen', parent=other_non_stereotactic, next_category = 'number of target volumes')
other_pelvis = P.Property('Pelvis', 'pelvis', parent=other_non_stereotactic, next_category = 'number of target volumes', default = True)
other_other = P.Property('Extremities / Other', 'other', parent=other_non_stereotactic, next_category = 'number of target volumes')

# Other SBRT: Region:
other_stereotactic_col_thorax =  P.Property('Column - thorax', 'col thorax', parent=other_stereotactic)
other_stereotactic_col_pelvis =  P.Property('Column - pelvis', 'col pelvis', parent=other_stereotactic)
other_stereotactic_pelvis  = P.Property('Pelvis', 'pelvis', parent=other_stereotactic, default = True)

# Other non-SBRT: Number of target volumes:
for region in [other_head, other_neck, other_thorax, other_abdomen, other_pelvis, other_other]:
  other_target_volume_one = P.Property('1','1', parent = region, next_category = '', default = True)
  other_target_volume_two = P.Property('2','2', parent = region, next_category = '')
  # With or without soft tissue component:
  for tv in [other_target_volume_one, other_target_volume_two]:
    other_with_gtv = P.Property('Soft tissue component (with GTV)', True, parent = tv)
    other_without_gtv = P.Property('Skeleton (without GTV)', False, parent = tv, default = True)


# Lists to be used with radiobutton objects:
regions = [brain, lung, breast, bladder, prostate, rectum, other]


# Radiobutton choices for deleting/keeping pre-existing ROIs:
p_delete = P.Property('Delete existing ROIs', 'yes')
p_delete_derived = P.Property('Delete all but plotted ROIs','some')
p_not_delete = P.Property('Do not delete existing ROIs','no', default = True)
delete = [p_delete, p_delete_derived, p_not_delete]
