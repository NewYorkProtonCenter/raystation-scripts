#Auto QACT Evaluation for RayStation Ver. 9A and 10B
#Developed by Jun Zhou, PhD, DABR
#jun.zhou@emory.edu
#jzhou995@gmail.com

#Change Log
#Version 1.0 7/16/2021
#Version 1.1 10/24/2021: add waiting for use check rigid restration on line 151, 152
#            11/14/2021: add line 43: from connect import *. It is needed for line 152 for add waiting for user interrupt
#            add the last parameter 'Check_Rigid_Reg' for function evaluate_QACT. If it is true, check rigid registation
#Version 1.2 12/6/2021: after upgrade to 10B, the RayVersion at 10.1.0.*, which is not the same as the 10B DTK 10.1.100.*.
#            The pm.CreateHybridDeformableRegistrationGroup() function is the same as that in 9A with less parameters. So I changed line 227-235 to try except, not test the version
#Version 1.3 12/16/2021: for MapRoiGeometriesDeformably and CopyRoiGeometries, the ROI list shouldn't be empty, otherwise crashes. Corrected this issue, not clinically released yet
#Version 1.4 12/22/2021: add remove additional override roi exclusions, say add override_ROIs_excluded= z_Contrast, then override_ROIs = list(set(override_ROIs)-set(override_ROIs_excluded)), not clinically released yet
#            02/10/2022: add override_ROIs_excluded to evaluate_QACT argument list
#Version 1.5 1/16/2022: 'Body' or 'BODY' is not added from 'additional_control_roi' anymore. Replace line 100: control_roi.extend(target_roi), with line 100 and 101: ROI_Body   = SSF.find_body(case.PatientModel.StructureSets[TPCT_name]), control_roi = list(set(ROI_Body + target_roi)). Not clinically released yet
#clinically updated on 5/31/2023

#line 143: 'if reg is None':not updated here is for 11B, will add when move to 11B
#the registration is differantiated with FoR and rigid registration. You can only have 1 FoR, but can have multiple rigid registation. FoR is needed
#on 5/31/2023, this has been updated

#Version 2.0 5/31/2023: upgrade for RayStation 12A_sp1. All previous clinically not implemented have been implemented.
#Add 'CopyRoiGeometries_ver11' to the end to solve the version incompatibility for CopyRoiGeometries, changed line 208 with CopyRoiGeometries_ver11
#Version 3.0 9/13/2023: upgrade for RayStation 2023B. On line 156: Changed from ComputeRigidImageRegistration (ver11), ComputeFoRRegistration (ver12a), to ComputeGrayLevelBasedRigidRegistration
#                       add parameter 'RayVersion' to calculateDoseOnAdditionalSetFixingHolesIfNeeded() function at lines 225 and 264
#                       new version change for ComputeDoseOnAdditionalSets and ComputePerturbedDose on Line 275-279:












#Actual code start from line 40, so all line number reference before are fixed
import patient_model_functions as PMF
import structure_set_functions as SSF
import rois as ROIS
from connect import *

def say_hello_to(name):
    print("Hello %s!" % name)


def find_TPCT_name(case, TPname, log_filename):
    TPCT_name = ''
    #if TPname == '', find the TPnmae, other wise, just need to find the TPCT name
    if TPname == '':
        #find the approved plan and its associated exam
        infopl = case.QueryPlanInfo(Filter = {'ApprovalStatus':'Approved'})
        # if infopl.Count == 0:
        if len(infopl) == 0:
            print('No Plans available')
            with open(log_filename, 'a') as f:
                f.write('\n' + 'ERROR: ' + 'No Plans available' + ', Case = ' + case.CaseName)
                f.close()
        else:
            earlist_approved_plan = infopl[0]
            if len(infopl) > 1:#find the earlist approved plan only for now
                for p in infopl:
                    if p['LastModified'] < earlist_approved_plan['LastModified']:
                        earlist_approved_plan = p
                print('More than one approved plans, the earlist approved plan is exported')

            #current_plan = case.LoadPlan(PlanInfo = p)
            #infobs = current_plan.QueryBeamSetInfo(Filter = {})
            TPname = case.TreatmentPlans[earlist_approved_plan['Name']].Name
            infobs = case.TreatmentPlans[earlist_approved_plan['Name']].QueryBeamSetInfo(Filter = {})
            if len(infobs) > 1:
                print(f'Plan {TPname} has more than 1 beamset, not supported now')
                # continue
            oldBeamSet = case.TreatmentPlans[earlist_approved_plan['Name']].BeamSets[0]
            examination = oldBeamSet.GetPlanningExamination()

            TPCT_name = examination.Name
    else:
        try:
            TPCT_name = case.TreatmentPlans[TPname].BeamSets[0].GetPlanningExamination().Name
        except:
            TPCT_name = ''
    with open(log_filename, 'a') as f:
        f.write('\n' + 'Case = ' + case.CaseName + ', Plan Name = ' + TPname + ', Exam Name = ' + TPCT_name)
        f.close()
    return TPname, TPCT_name


def evaluate_QACT(case, TPCT_name, TPname, log_filename, RayVersion, additional_CTV, additional_control_roi, override_ROIs_excluded, Check_Rigid_Reg):
    control_roi = []
    target_roi=[]
    target_roi = SSF.find_CTVs(case.PatientModel.StructureSets[TPCT_name])
    for ctv in additional_CTV:
        if ctv in target_roi:
            continue
        if SSF.has_named_roi_with_contours(case.PatientModel.StructureSets[TPCT_name], ctv):
            target_roi.append(ctv)
    ROI_Body   = SSF.find_body(case.PatientModel.StructureSets[TPCT_name])
    control_roi = list(set(ROI_Body + target_roi))
    for oar in additional_control_roi:
        if oar in control_roi:
            continue
        if SSF.has_named_roi_with_contours(case.PatientModel.StructureSets[TPCT_name], oar):
            control_roi.append(oar)

    #Process each CBCT images imported
    #**********************CBCT_images has all the newly imported CBCTs***********************
    QACT_images = []
    for examination in case.Examinations:
        # if examination.Name.find('CBCT') == -1: #new CBCT scan
        if examination.Name.startswith('CT'): #new CBCT scan
            try:
                station = examination.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x1010)
            except:
                print('DICOM has no station tag')
                continue
            # if station['StationName'] == 'CTAWP83695': #from the SIM CT ####### in 9A, the dictionary key is Station Name, while in 10B, it's StationName
            if next(iter(station.items()))[1] == 'CTAWP83695': #from the SIM CT
                exam_date = examination.GetExaminationDateTime().ToString('yyyy.MM.dd')
                try:
                    examination.Name = 'QACT ' + exam_date
                except:
                    print('Could not change CBCT name, name already exists: CBCT '+ exam_date)

                if examination.EquipmentInfo.ImagingSystemReference == None:
                    print ("Setting CT-to-density table")
                    examination.EquipmentInfo.SetImagingSystemReference(ImagingSystemName="EPTC CT Sim")

                #1.a Create external for CBCT images
                PMF.create_external_geometry(case.PatientModel, examination, case.PatientModel.StructureSets[examination.Name])
                #1.b create FOV ROI for CBCT images
                # create_CBCT_FOV(CBCT_scan_FOV, examination, case.PatientModel, 0)

                QACT_images.append(examination.Name)  #CBCT_images has all the CBCT exam names

                reg = case.GetTransformForExaminations(
                    FromExamination = TPCT_name,
                    ToExamination = examination.Name
                )
                print (f'Regid registration is {reg}')
                if reg is None:
                    # Changed on 5/31/2023 for update to 12A
                    # case.ComputeRigidImageRegistration(FloatingExaminationName = examination.Name, ReferenceExaminationName = TPCT_name,
                    #     UseOnlyTranslations=False, HighWeightOnBones=True, InitializeImages=True, FocusRoisNames=target_roi, RegistrationName=None)

                    if RayVersion < 11:# in version 11, the registration is differantiated with FoR and rigid registration. You can only have 1 FoR, but can have multiple rigid registation. FoR is needed
                        case.ComputeRigidImageRegistration(FloatingExaminationName = examination.Name, ReferenceExaminationName = TPCT_name,
                            UseOnlyTranslations=False, HighWeightOnBones=True, InitializeImages=True, FocusRoisNames=target_roi, RegistrationName=None)
                    elif RayVersion < 14:# 11 to 12A
                        case.ComputeFoRRegistration(FloatingExaminationName = examination.Name, ReferenceExaminationName = TPCT_name,
                            UseOnlyTranslations=False, HighWeightOnBones=True, InitializeImages=True, FocusRoisNames=target_roi, RegistrationName=None)
                    else:#for 2023B
                        case.ComputeGrayLevelBasedRigidRegistration(FloatingExaminationName = examination.Name, ReferenceExaminationName = TPCT_name,
                            RegistrationName=None, UseOnlyTranslations=False, HighWeightOnBones=True, InitializeImages=True, FocusRoisNames=target_roi)
                    with open(log_filename, 'a') as f:
                        f.write('\n' + 'New rigid registration is created')
                        f.close()
                if Check_Rigid_Reg:
                    await_user_input('Please double check the rigid registration before continue')

    #4. Create a new defreg between the pCT and cCBCT1 (with the pCT as the reference) and use this to map the pCT ROISs (except external)
    # deformably to cCBCT1. These ROSs will be used for dosimetric evaluation on the images.
    # assume each CBCT has a newly created cCBCT1

    for i, qact_name in enumerate(QACT_images):
        #check if name has QACT
        if qact_name.find('QACT') == -1:
            continue
        for examination in case.Examinations:
            print(f'examination name is {examination.Name}, QACT name is {qact_name}')
            exam_name = examination.Name
            if exam_name == qact_name:   #the exam is newly imported QACT
                print(f'\nfind all CTVs {target_roi} is done')
                # reg_groups = create_hybrid_deformable_reg_group(case.PatientModel, TPCT_name, [exam_name], [], target_roi)
                reg_groups = create_hybrid_deformable_reg_group(case.PatientModel, TPCT_name, [exam_name], [], control_roi, log_filename, RayVersion)
                if len(reg_groups) == 1:
                    print(f'the returned reg name is {reg_groups[0]}')

                    #V1a 6/21/21 map targets
                    # roi_to_map = target_roi
                    # OARs = SSF.find_OARs(case.PatientModel.StructureSets[TPCT_name])
                    # roi_to_map.extend(OARs)
                    # override_ROIs, support_ROIs = SSF.find_override_ROI(case.PatientModel.StructureSets[TPCT_name])#override ROIs includes support ROIs
                    # roi_to_map.extend(override_ROIs)
                    # print(f'\nMap all the targes, organ OARs, and ROIs with density override {roi_to_map}')
                    # #copy the external and table from the TPCT to the cCBCT1
                    # external = SSF.find_External(case.PatientModel.StructureSets[TPCT_name])
                    # case.PatientModel.CopyRoiGeometries(SourceExamination = case.Examinations[TPCT_name], TargetExaminationNames=[exam_name], RoiNames=[external])
                    # case.MapRoiGeometriesDeformably(RoiGeometryNames = roi_to_map, CreateNewRois=False, StructureRegistrationGroupNames=reg_groups,
                    #     ReferenceExaminationNames=[TPCT_name], TargetExaminationNames=[exam_name], ReverseMapping=False, AbortWhenBadDisplacementField=False)
                    # # case.MapRoiGeometriesDeformably(RoiGeometryNames=["CTV_5412", "CTV_6006", "CTV_6600"], CreateNewRois=False,
                    # #     StructureRegistrationGroupNames=["DIR_TPCT 2020.06.22_cCBCT1 2020.08.12"], ReferenceExaminationNames=["TPCT 2020.06.22"], TargetExaminationNames=["cCBCT1 2020.08.12"], ReverseMapping=False, AbortWhenBadDisplacementField=False)

                    #V2a 7/14/21: rigid copy target to their original name, map target to different name, like we used to do QACT
                    roi_to_copy = []
                    roi_to_copy.extend(target_roi)
                    OARs = SSF.find_OARs(case.PatientModel.StructureSets[TPCT_name])
                    roi_to_map = OARs
                    override_ROIs, support_ROIs = SSF.find_override_ROI(case.PatientModel.StructureSets[TPCT_name])#override ROIs includes support ROIs
                    override_ROIs = list(set(override_ROIs)-set(override_ROIs_excluded))
                    roi_to_map.extend(override_ROIs)
                    print(f'\nMap all the targes, organ OARs, and ROIs with density override {roi_to_map}')
                    #copy the external and table from the TPCT to the cCBCT1
                    external = SSF.find_External(case.PatientModel.StructureSets[TPCT_name])
                    roi_to_copy.extend([external])
                    if len(roi_to_copy) > 0:
                        # case.PatientModel.CopyRoiGeometries(SourceExamination = case.Examinations[TPCT_name], TargetExaminationNames=[exam_name], RoiNames=roi_to_copy)
                        CopyRoiGeometries_ver11(case, case.Examinations[TPCT_name], [exam_name], roi_to_copy, RayVersion)
                    if len(roi_to_map) > 0:
                        case.MapRoiGeometriesDeformably(RoiGeometryNames = list(set(roi_to_map)), CreateNewRois=False, StructureRegistrationGroupNames=reg_groups,
                            ReferenceExaminationNames=[TPCT_name], TargetExaminationNames=[exam_name], ReverseMapping=False, AbortWhenBadDisplacementField=False)
                    if len(target_roi) > 0:
                        case.MapRoiGeometriesDeformably(RoiGeometryNames = target_roi, CreateNewRois=True, StructureRegistrationGroupNames=reg_groups,
                            ReferenceExaminationNames=[TPCT_name], TargetExaminationNames=[exam_name], ReverseMapping=False, AbortWhenBadDisplacementField=False)

                else:
                    print('Reg_group return none')


    #7.  Used the ‘Compute on additional set’ to calculate the plan dose on the two Corrected CBCT, two Virtual CT and deformed QACT.
    for i, qact_name in enumerate(QACT_images):
        calculateDoseOnAdditionalSetFixingHolesIfNeeded(case, TPname, qact_name, [], log_filename, RayVersion)

def create_hybrid_deformable_reg_group(pm, ref_exam_name, target_exam_names, ctrl_roi_names, focus_roi_names, log_filename, RayVersion):
    print('deform from reference exam ' + ref_exam_name + 'to target exams ' + ''.join(target_exam_names))
    deformable_registration_group_names = []
    regName = ''
    #check if the deformable registation already exist or not
    for to_name in target_exam_names:
        matching_groups = [group.Name for group in pm.StructureRegistrationGroups
                if len([reg for reg in group.DeformableStructureRegistrations if (reg.FromExamination.Name == ref_exam_name and reg.ToExamination.Name == to_name)]) > 0]
        if len(matching_groups) == 0:#not find the deformable registration, create one
            regName = ref_exam_name + '_' + to_name
            # print('FocusRoiNames is ' + ', '.join(focus_roi_names))
            try:
                pm.CreateHybridDeformableRegistrationGroup(RegistrationGroupName = regName, ReferenceExaminationName = ref_exam_name,
                    TargetExaminationNames = [to_name], ControllingRoiNames = ctrl_roi_names, ControllingPoiNames=[], FocusRoiNames = focus_roi_names,
                    AlgorithmSettings={ 'NumberOfResolutionLevels': 3, 'InitialResolution': { 'x': 0.5, 'y': 0.5, 'z': 0.5 },
                    'FinalResolution': { 'x': 0.25, 'y': 0.25, 'z': 0.25 }, 'InitialGaussianSmoothingSigma': 2, 'FinalGaussianSmoothingSigma': 0.333333333333333,
                    'InitialGridRegularizationWeight': 400, 'FinalGridRegularizationWeight': 400, 'ControllingRoiWeight': 0.5, 'ControllingPoiWeight': 0.1,
                    'MaxNumberOfIterationsPerResolutionLevel': 1000, 'ImageSimilarityMeasure': "CorrelationCoefficient", 'DeformationStrategy': "Default", 'ConvergenceTolerance': 1E-05 })

            except:
                pm.CreateHybridDeformableRegistrationGroup(RegistrationGroupName = regName, ReferenceExaminationName = ref_exam_name,
                    TargetExaminationNames = [to_name], ControllingRoiNames = ctrl_roi_names, ControllingPoiNames=[], FocusRoiNames = focus_roi_names, ReferencePointList=[],
                    TargetPointLists=[], AlgorithmSettings={ 'NumberOfResolutionLevels': 3, 'InitialResolution': { 'x': 0.5, 'y': 0.5, 'z': 0.5 },
                    'FinalResolution': { 'x': 0.25, 'y': 0.25, 'z': 0.25 }, 'InitialGaussianSmoothingSigma': 2, 'FinalGaussianSmoothingSigma': 0.333333333333333,
                    'InitialGridRegularizationWeight': 400, 'FinalGridRegularizationWeight': 400, 'ControllingRoiWeight': 0.5, 'ControllingPoiWeight': 0.1,
                    'MaxNumberOfIterationsPerResolutionLevel': 1000, 'ImageSimilarityMeasure': "CorrelationCoefficient", 'DeformationStrategy': "Default", 'ConvergenceTolerance': 1E-05 })
            deformable_registration_group_names.append(regName)
        else: #the deformable registration already exist
            print('Deformable registration from the ref exam ' + ref_exam_name + 'to ' + to_name + ' already exists')
            deformable_registration_group_names.extend(matching_groups)
    with open(log_filename, 'a') as f:
        # f.write('\n' + 'deform from reference exam ' + ref_exam_name + ' to target exams ' + ' to target exams '+ ' are:' + ','join(deformable_registration_group_names))
        f.write('\n' + 'deform from reference exam ' + ref_exam_name + ' to target exams ' + ','.join(target_exam_names) + ' are:' + ','.join(deformable_registration_group_names))
        f.close()
    # if the deformable registration already exist, return ''
    return deformable_registration_group_names

def calculateDoseOnAdditionalSetFixingHolesIfNeeded(case, TPname, imageSetName, rangeUncertainty, log_filename, RayVersion):
    try:
        crop_external(case, imageSetName)
        for plan in case.TreatmentPlans:
            if plan.Name == TPname:
                for beamset in plan.BeamSets:
                    if RayVersion < 14:# in version 14, the ComputeDoseOnAdditionalSets and ComputePerturbedDose have changed
                        beamset.ComputeDoseOnAdditionalSets(OnlyOneDosePerImageSet=False, AllowGridExpansion=False, ExaminationNames=[imageSetName], FractionNumbers=[0], ComputeBeamDoses=True)
                        for ru in rangeUncertainty:
                            beamset.ComputePerturbedDose(DensityPerturbation = ru, PatientShift = { 'x': 0.0, 'y': 0.0, 'z': 0.0 }, OnlyOneDosePerImageSet = False,
                                AllowGridExpansion = True, ExaminationNames = [imageSetName], FractionNumbers = [0], ComputeBeamDoses = True)
                    else:#for version 2023B
                        beamset.ComputeDoseOnAdditionalSets(Examinations=[case.Examinations[imageSetName]], Fractions=None, ComputeBeamDoses=True, AllowGridExpansion=True)
                        for ru in rangeUncertainty:
                            beamset.ComputePerturbedDose(DensityPerturbation = ru, PatientShift = { 'x': 0.0, 'y': 0.0, 'z': 0.0 }, RotationPoint=None, YawDegrees=0.0, PitchDegrees=0.0, RollDegrees=0.0,
                                Examinations = [imageSetName], Fractions=None, ComputeBeamDoses = True, AllowGridExpansion = True)

                print(f'Calculated dose on case {case.CaseName}, plan {plan.Name}, beamset {beamset.DicomPlanLabel} for generated exams {imageSetName}')
                with open(log_filename, 'a') as f:
                    f.write(f'\nDose calculated on case {case.CaseName}, plan {plan.Name}, beamset {beamset.DicomPlanLabel} for generated exams {imageSetName}')
                    f.close()
    except:
        print(f'*** Calculate dose on case {case.CaseName}, plan {plan.Name}, beamset {beamset.DicomPlanLabel} for generated exams {imageSetName} failed')
        with open(log_filename, 'a') as f:
            f.write(f'\n*** Calculate dose on case {case.CaseName}, plan {plan.Name}, beamset {beamset.DicomPlanLabel} for generated exams {imageSetName} failed')
            f.close()

def crop_external(case, exam_name):
    exam = case.Examinations[exam_name]
    box = exam.Series[0].ImageStack.GetBoundingBox()
    x_dist = abs(box[0].x - box[1].x)
    y_dist = abs(box[0].y - box[1].y)
    z_dist = abs(box[0].z - box[1].z)

    if box[0].x > box[1].x:
        mid_x = box[0].x - x_dist/2.0
    else:
        mid_x = box[1].x - x_dist/2.0
    if box[0].y > box[1].y:
        mid_y = box[0].y - y_dist/2.0
    else:
        mid_y = box[1].y - y_dist/2.0
    if box[0].z > box[1].z:
        mid_z = box[0].z - z_dist/2.0
    else:
        mid_z = box[1].z - z_dist/2.0

    fov_exists = False
    for rois in case.PatientModel.StructureSets[exam_name].RoiGeometries:
        if rois.OfRoi.Name == "CT_FOV":
            fov_exists = True
            break
    if not fov_exists:
        case.PatientModel.CreateRoi(Name=r"CT_FOV", Color="Red", Type="Undefined", TissueName=None, RbeCellTypeName=None, RoiMaterial=None)

    case.PatientModel.StructureSets[exam_name].RoiGeometries[r"CT_FOV"].OfRoi.CreateBoxGeometry(Size={ 'x': x_dist, 'y': y_dist, 'z': z_dist },
            Examination=exam, Center={ 'x': mid_x, 'y': mid_y, 'z': mid_z }, Representation="TriangleMesh", VoxelSize=None)

    override_ROIs, support_ROIs = SSF.find_override_ROI(case.PatientModel.StructureSets[exam_name])
    for rois in case.PatientModel.StructureSets[exam_name].RoiGeometries:
        if rois.OfRoi.Type == 'External':
            try:
                case.PatientModel.StructureSets[exam_name].RoiGeometries[rois.OfRoi.Name].OfRoi.CreateAlgebraGeometry(Examination=exam, Algorithm="Auto",
                  ExpressionA={'Operation': "Union", 'SourceRoiNames': [rois.OfRoi.Name], 'MarginSettings': {'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0}},
                  ExpressionB={'Operation': "Union", 'SourceRoiNames': [r"CT_FOV"], 'MarginSettings': {'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0}},
                  ResultOperation="Intersection", ResultMarginSettings={'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0})

                case.PatientModel.StructureSets[exam_name].SimplifyContours(RoiNames=[rois.OfRoi.Name], RemoveHoles3D=True, RemoveSmallContours=True,
                    AreaThreshold=0.1, ReduceMaxNumberOfPointsInContours=True, MaxNumberOfPoints=1000, CreateCopyOfRoi=False, ResolveOverlappingContours=True)
                #crop all override ROIs outside of external
                for override_rois in override_ROIs:
                    if override_rois in support_ROIs:#don't crop support ROIs
                        continue
                    case.PatientModel.StructureSets[exam_name].RoiGeometries[override_rois].OfRoi.CreateAlgebraGeometry(Examination=exam, Algorithm="Auto",
                      ExpressionA={'Operation': "Union", 'SourceRoiNames': [override_rois], 'MarginSettings': {'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0}},
                      ExpressionB={'Operation': "Union", 'SourceRoiNames': [rois.OfRoi.Name], 'MarginSettings': {'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0}},
                      ResultOperation="Intersection", ResultMarginSettings={'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0})

            except:
                print ("Crop failed. Is External an approved structure?")
                return False
            break


    return True

def CopyRoiGeometries_ver11(the_case, source_examination, target_examinationNames, roi_names, RayVersion):
    if RayVersion < 11:
        the_case.PatientModel.CopyRoiGeometries(SourceExamination = source_examination, TargetExaminationNames = target_examinationNames, RoiNames = roi_names)
    elif RayVersion < 12:
        the_case.PatientModel.CopyRoiGeometries(SourceExamination = source_examination, TargetExaminationNames = target_examinationNames, RoiNames = roi_names, ImageRegistrationNames=[])
    else:
        the_case.PatientModel.CopyRoiGeometries(SourceExamination = source_examination, TargetExaminationNames = target_examinationNames, RoiNames = roi_names, ImageRegistrationNames=[], TargetExaminationNamesToSkipAddedReg=[])