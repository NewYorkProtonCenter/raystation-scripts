# Auto QACT Evaluation for RayStation Ver. 9A and 10B
# Developed by Jun Zhou, PhD, DABR
# jun.zhou@emory.edu
# jzhou995@gmail.com

from functions import patient_model_functions as PMF, structure_set_functions as SSF
from logging import Logger
from typing import Tuple
from connect import *  # type: ignore
import statetree  # type: ignore


def find_TPCT_name(case, TPname: str, logger: Logger) -> Tuple[str, str]:
    TPCT_name = ''
    # if TPname == '', find the TPname, other wise, just need to find the TPCT name
    if TPname == '':
        # find the approved plan and its associated exam
        infopl = case.QueryPlanInfo(Filter={'ApprovalStatus': 'Approved'})
        if len(infopl) == 0:
            logger.error('No Plans available' + ', Case = ' + case.CaseName)
        else:
            earlist_approved_plan = infopl[0]
            if len(infopl) > 1:  # find the earlist approved plan only for now
                for p in infopl:
                    if p['LastModified'] < earlist_approved_plan['LastModified']:
                        earlist_approved_plan = p
                logger.debug('More than one approved plans, the earlist approved plan is exported')

            # current_plan = case.LoadPlan(PlanInfo = p)
            # infobs = current_plan.QueryBeamSetInfo(Filter = {})
            TPname = case.TreatmentPlans[earlist_approved_plan['Name']].Name
            infobs = case.TreatmentPlans[earlist_approved_plan['Name']].QueryBeamSetInfo(Filter={})
            if len(infobs) > 1:
                logger.warning(f'Plan {TPname} has more than 1 beamset, not supported now')
                # continue
            oldBeamSet = case.TreatmentPlans[earlist_approved_plan['Name']].BeamSets[0]
            examination = oldBeamSet.GetPlanningExamination()

            TPCT_name = examination.Name
    else:
        try:
            TPCT_name = case.TreatmentPlans[TPname].BeamSets[0].GetPlanningExamination().Name
        except:
            TPCT_name = ''
    logger.info(f'Case = {case.CaseName}, Plan Name = {TPname}, Exam Name = {TPCT_name}')
    return TPname, TPCT_name


def evaluate_QACT(case, TPCT_name, TPname, logger, RayVersion, additional_CTV, additional_control_roi, override_ROIs_excluded, Check_Rigid_Reg):
    control_roi = []
    target_roi = []
    target_roi = SSF.find_CTVs(case.PatientModel.StructureSets[TPCT_name])

    for ctv in additional_CTV:
        if ctv in target_roi:
            continue
        if SSF.has_named_roi_with_contours(case.PatientModel.StructureSets[TPCT_name], ctv):
            target_roi.append(ctv)
    ROI_Body = SSF.find_body(case.PatientModel.StructureSets[TPCT_name])
    control_roi = list(set(ROI_Body + target_roi))
    for oar in additional_control_roi:
        if oar in control_roi:
            continue
        if SSF.has_named_roi_with_contours(case.PatientModel.StructureSets[TPCT_name], oar):
            control_roi.append(oar)

    # Process each CBCT images imported
    # **********************CBCT_images has all the newly imported CBCTs***********************
    QACT_images = []
    for examination in case.Examinations:
        # if examination.Name.find('CBCT') == -1: #new CBCT scan
        if examination.Name.startswith('CBCT'):  # new CBCT scan
            try:
                station = examination.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x1010)
            except:
                logger.debug('DICOM has no station tag')
                continue
            # if station['StationName'] == 'CTAWP83695': #from the SIM CT ####### in 9A, the dictionary key is Station Name, while in 10B, it's StationName
            if next(iter(station.items()))[1] == 'CTAWP83695':  # from the SIM CT
                exam_date = examination.GetExaminationDateTime().ToString('yyyy.MM.dd')
                try:
                    examination.Name = 'QACT ' + exam_date
                except:
                    logger.debug('Could not change CBCT name, name already exists: CBCT ' + exam_date)

                if examination.EquipmentInfo.ImagingSystemReference == None:
                    logger.debug("Setting CT-to-density table")
                    examination.EquipmentInfo.SetImagingSystemReference(ImagingSystemName="EPTC CT Sim")

                # 1.a Create external for CBCT images
                PMF.create_external_geometry(case.PatientModel, examination, case.PatientModel.StructureSets[examination.Name])
                # 1.b create FOV ROI for CBCT images
                # create_CBCT_FOV(CBCT_scan_FOV, examination, case.PatientModel, 0)

                QACT_images.append(examination.Name)  # CBCT_images has all the CBCT exam names

                reg = case.GetTransformForExaminations(
                    FromExamination=TPCT_name,
                    ToExamination=examination.Name
                )
                logger.debug(f'Regid registration is {reg}')
                if reg is None:
                    # Changed on 5/31/2023 for update to 12A
                    # case.ComputeRigidImageRegistration(FloatingExaminationName = examination.Name, ReferenceExaminationName = TPCT_name,
                    #     UseOnlyTranslations=False, HighWeightOnBones=True, InitializeImages=True, FocusRoisNames=target_roi, RegistrationName=None)

                    if RayVersion < 11:  # in version 11, the registration is differantiated with FoR and rigid registration. You can only have 1 FoR, but can have multiple rigid registation. FoR is needed
                        case.ComputeRigidImageRegistration(FloatingExaminationName=examination.Name, ReferenceExaminationName=TPCT_name,
                                                           UseOnlyTranslations=False, HighWeightOnBones=True, InitializeImages=True, FocusRoisNames=target_roi, RegistrationName=None)
                    elif RayVersion < 14:  # 11 to 12A
                        case.ComputeFoRRegistration(FloatingExaminationName=examination.Name, ReferenceExaminationName=TPCT_name,
                                                    UseOnlyTranslations=False, HighWeightOnBones=True, InitializeImages=True, FocusRoisNames=target_roi, RegistrationName=None)
                    else:  # for 2023B
                        case.ComputeGrayLevelBasedRigidRegistration(FloatingExaminationName=examination.Name, ReferenceExaminationName=TPCT_name,
                                                                    RegistrationName=None, UseOnlyTranslations=False, HighWeightOnBones=True, InitializeImages=True, FocusRoisNames=target_roi)
                    logger.info('New rigid registration is created')
                if Check_Rigid_Reg:
                    input('Please double check the rigid registration before continue')

    # 4. Create a new defreg between the pCT and cCBCT1 (with the pCT as the reference) and use this to map the pCT ROISs (except external)
    # deformably to cCBCT1. These ROSs will be used for dosimetric evaluation on the images.
    # assume each CBCT has a newly created cCBCT1

    for qact_name in QACT_images:
        # check if name has QACT
        if qact_name.find('QACT') == -1:
            continue
        for examination in case.Examinations:
            logger.debug(f'examination name is {examination.Name}, QACT name is {qact_name}')
            exam_name = examination.Name
            if exam_name == qact_name:  # the exam is newly imported QACT
                logger.debug(f'\nfind all CTVs {target_roi} is done')
                # reg_groups = create_hybrid_deformable_reg_group(case.PatientModel, TPCT_name, [exam_name], [], target_roi)
                reg_groups = create_hybrid_deformable_reg_group(case.PatientModel, TPCT_name, [exam_name], [], control_roi, logger)
                if len(reg_groups) == 1:
                    logger.debug(f'the returned reg name is {reg_groups[0]}')

                    # V1a 6/21/21 map targets
                    # roi_to_map = target_roi
                    # OARs = SSF.find_OARs(case.PatientModel.StructureSets[TPCT_name])
                    # roi_to_map.extend(OARs)
                    # override_ROIs, support_ROIs = SSF.find_override_ROI(case.PatientModel.StructureSets[TPCT_name])#override ROIs includes support ROIs
                    # roi_to_map.extend(override_ROIs)
                    # logger.debug(f'\nMap all the targes, organ OARs, and ROIs with density override {roi_to_map}')
                    # #copy the external and table from the TPCT to the cCBCT1
                    # external = SSF.find_External(case.PatientModel.StructureSets[TPCT_name])
                    # case.PatientModel.CopyRoiGeometries(SourceExamination = case.Examinations[TPCT_name], TargetExaminationNames=[exam_name], RoiNames=[external])
                    # case.MapRoiGeometriesDeformably(RoiGeometryNames = roi_to_map, CreateNewRois=False, StructureRegistrationGroupNames=reg_groups,
                    #     ReferenceExaminationNames=[TPCT_name], TargetExaminationNames=[exam_name], ReverseMapping=False, AbortWhenBadDisplacementField=False)
                    # # case.MapRoiGeometriesDeformably(RoiGeometryNames=["CTV_5412", "CTV_6006", "CTV_6600"], CreateNewRois=False,
                    # #     StructureRegistrationGroupNames=["DIR_TPCT 2020.06.22_cCBCT1 2020.08.12"], ReferenceExaminationNames=["TPCT 2020.06.22"], TargetExaminationNames=["cCBCT1 2020.08.12"], ReverseMapping=False, AbortWhenBadDisplacementField=False)

                    # V2a 7/14/21: rigid copy target to their original name, map target to different name, like we used to do QACT
                    roi_to_copy = []
                    roi_to_copy.extend(target_roi)
                    OARs = SSF.find_OARs(case.PatientModel.StructureSets[TPCT_name])
                    roi_to_map = OARs
                    override_ROIs, support_ROIs = SSF.find_override_ROI(
                        case.PatientModel.StructureSets[TPCT_name])  # override ROIs includes support ROIs
                    override_ROIs = list(set(override_ROIs) - set(override_ROIs_excluded))
                    roi_to_map.extend(override_ROIs)
                    logger.debug(f'\nMap all the targes, organ OARs, and ROIs with density override {roi_to_map}')
                    # copy the external and table from the TPCT to the cCBCT1
                    external = SSF.find_External(case.PatientModel.StructureSets[TPCT_name])
                    roi_to_copy.extend([external])
                    if len(roi_to_copy) > 0:
                        # case.PatientModel.CopyRoiGeometries(SourceExamination = case.Examinations[TPCT_name], TargetExaminationNames=[exam_name], RoiNames=roi_to_copy)
                        CopyRoiGeometries_ver11(case, case.Examinations[TPCT_name], [exam_name], roi_to_copy, RayVersion)
                    if len(roi_to_map) > 0:
                        case.MapRoiGeometriesDeformably(RoiGeometryNames=list(set(roi_to_map)), CreateNewRois=False, StructureRegistrationGroupNames=reg_groups,
                                                        ReferenceExaminationNames=[TPCT_name], TargetExaminationNames=[exam_name], ReverseMapping=False, AbortWhenBadDisplacementField=False)
                    if len(target_roi) > 0:
                        case.MapRoiGeometriesDeformably(RoiGeometryNames=target_roi, CreateNewRois=True, StructureRegistrationGroupNames=reg_groups,
                                                        ReferenceExaminationNames=[TPCT_name], TargetExaminationNames=[exam_name], ReverseMapping=False, AbortWhenBadDisplacementField=False)

                else:
                    logger.debug('Reg_group return none')

    # 7.  Used the ‘Compute on additional set’ to calculate the plan dose on the two Corrected CBCT, two Virtual CT and deformed QACT.
    for i, qact_name in enumerate(QACT_images):
        calculateDoseOnAdditionalSetFixingHolesIfNeeded(case, TPname, qact_name, [], logger, RayVersion)


def create_hybrid_deformable_reg_group(pm, ref_exam_name, target_exam_names, ctrl_roi_names, focus_roi_names, logger):
    logger.debug('deform from reference exam ' + ref_exam_name + 'to target exams ' + ''.join(target_exam_names))
    deformable_registration_group_names = []
    regName = ''
    # check if the deformable registation already exist or not
    for to_name in target_exam_names:
        matching_groups = [group.Name for group in pm.StructureRegistrationGroups
                           if len([reg for reg in group.DeformableStructureRegistrations if (reg.FromExamination.Name == ref_exam_name and reg.ToExamination.Name == to_name)]) > 0]
        if len(matching_groups) == 0:  # not find the deformable registration, create one
            regName = ref_exam_name + '_' + to_name
            # logger.debug('FocusRoiNames is ' + ', '.join(focus_roi_names))
            try:
                pm.CreateHybridDeformableRegistrationGroup(
                    RegistrationGroupName=regName, ReferenceExaminationName=ref_exam_name,
                    TargetExaminationNames=[to_name], ControllingRoiNames=ctrl_roi_names, ControllingPoiNames=[],
                    FocusRoiNames=focus_roi_names,
                    AlgorithmSettings={
                        'NumberOfResolutionLevels': 3, 'InitialResolution': {'x': 0.5, 'y': 0.5, 'z': 0.5},
                        'FinalResolution': {'x': 0.25, 'y': 0.25, 'z': 0.25}, 'InitialGaussianSmoothingSigma': 2, 'FinalGaussianSmoothingSigma': 0.333333333333333,
                        'InitialGridRegularizationWeight': 400, 'FinalGridRegularizationWeight': 400, 'ControllingRoiWeight': 0.5, 'ControllingPoiWeight': 0.1,
                        'MaxNumberOfIterationsPerResolutionLevel': 1000, 'ImageSimilarityMeasure': "CorrelationCoefficient", 'DeformationStrategy': "Default", 'ConvergenceTolerance': 1E-05})

            except:
                pm.CreateHybridDeformableRegistrationGroup(
                    RegistrationGroupName=regName, ReferenceExaminationName=ref_exam_name,
                    TargetExaminationNames=[to_name], ControllingRoiNames=ctrl_roi_names, ControllingPoiNames=[],
                    FocusRoiNames=focus_roi_names, ReferencePointList=[],
                    TargetPointLists=[], AlgorithmSettings={
                        'NumberOfResolutionLevels': 3, 'InitialResolution': {'x': 0.5, 'y': 0.5, 'z': 0.5},
                        'FinalResolution': {'x': 0.25, 'y': 0.25, 'z': 0.25}, 'InitialGaussianSmoothingSigma': 2, 'FinalGaussianSmoothingSigma': 0.333333333333333,
                        'InitialGridRegularizationWeight': 400, 'FinalGridRegularizationWeight': 400, 'ControllingRoiWeight': 0.5, 'ControllingPoiWeight': 0.1,
                        'MaxNumberOfIterationsPerResolutionLevel': 1000, 'ImageSimilarityMeasure': "CorrelationCoefficient", 'DeformationStrategy': "Default", 'ConvergenceTolerance': 1E-05})
            deformable_registration_group_names.append(regName)
        else:  # the deformable registration already exist
            logger.debug('Deformable registration from the ref exam ' + ref_exam_name + 'to ' + to_name + ' already exists')
            deformable_registration_group_names.extend(matching_groups)
    logger.info(
        f'deform from reference exam {ref_exam_name} to target exams {",".join(target_exam_names)} are:{",".join(deformable_registration_group_names)}')
    # if the deformable registration already exist, return ''
    return deformable_registration_group_names


def calculateDoseOnAdditionalSetFixingHolesIfNeeded(case, TPname, imageSetName, rangeUncertainty, logger, RayVersion):
    plan = None
    beamset = None
    try:
        crop_external(case, imageSetName, logger)
        for plan in case.TreatmentPlans:
            if plan.Name == TPname:
                for beamset in plan.BeamSets:
                    if RayVersion < 14:  # in version 14, the ComputeDoseOnAdditionalSets and ComputePerturbedDose have changed
                        beamset.ComputeDoseOnAdditionalSets(
                            OnlyOneDosePerImageSet=False, AllowGridExpansion=False, ExaminationNames=[imageSetName],
                            FractionNumbers=[0], ComputeBeamDoses=True)
                        for ru in rangeUncertainty:
                            beamset.ComputePerturbedDose(
                                DensityPerturbation=ru, PatientShift={'x': 0.0, 'y': 0.0, 'z': 0.0}, OnlyOneDosePerImageSet=False,
                                AllowGridExpansion=True, ExaminationNames=[imageSetName], FractionNumbers=[0], ComputeBeamDoses=True)
                    else:  # for version 2023B
                        beamset.ComputeDoseOnAdditionalSets(
                            Examinations=[case.Examinations[imageSetName]],
                            Fractions=None, ComputeBeamDoses=True, AllowGridExpansion=True)
                        for ru in rangeUncertainty:
                            beamset.ComputePerturbedDose(
                                DensityPerturbation=ru, PatientShift={'x': 0.0, 'y': 0.0, 'z': 0.0}, RotationPoint=None, YawDegrees=0.0, PitchDegrees=0.0, RollDegrees=0.0,
                                Examinations=[imageSetName], Fractions=None, ComputeBeamDoses=True, AllowGridExpansion=True)

                    logger.info(
                        f'Calculated dose on case {case.CaseName}, plan {plan.Name}, beamset {beamset.DicomPlanLabel} for generated exams {imageSetName}')
    except:
        logger.error(
            f'Calculate dose on case {case.CaseName}, plan {plan.Name if plan else "None"}, beamset {beamset.DicomPlanLabel if beamset else "None"} for generated exams {imageSetName} failed')


def crop_external(case, exam_name, logger):
    exam = case.Examinations[exam_name]
    box = exam.Series[0].ImageStack.GetBoundingBox()
    x_dist = abs(box[0].x - box[1].x)
    y_dist = abs(box[0].y - box[1].y)
    z_dist = abs(box[0].z - box[1].z)

    if box[0].x > box[1].x:
        mid_x = box[0].x - x_dist / 2.0
    else:
        mid_x = box[1].x - x_dist / 2.0
    if box[0].y > box[1].y:
        mid_y = box[0].y - y_dist / 2.0
    else:
        mid_y = box[1].y - y_dist / 2.0
    if box[0].z > box[1].z:
        mid_z = box[0].z - z_dist / 2.0
    else:
        mid_z = box[1].z - z_dist / 2.0

    fov_exists = False
    for rois in case.PatientModel.StructureSets[exam_name].RoiGeometries:
        if rois.OfRoi.Name == "CT_FOV":
            fov_exists = True
            break
    if not fov_exists:
        case.PatientModel.CreateRoi(Name=r"CT_FOV", Color="Red", Type="Undefined", TissueName=None, RbeCellTypeName=None, RoiMaterial=None)

    case.PatientModel.StructureSets[exam_name].RoiGeometries[r"CT_FOV"].OfRoi.CreateBoxGeometry(
        Size={'x': x_dist, 'y': y_dist, 'z': z_dist},
        Examination=exam, Center={'x': mid_x, 'y': mid_y, 'z': mid_z}, Representation="TriangleMesh", VoxelSize=None)

    override_ROIs, support_ROIs = SSF.find_override_ROI(case.PatientModel.StructureSets[exam_name])
    for rois in case.PatientModel.StructureSets[exam_name].RoiGeometries:
        if rois.OfRoi.Type == 'External':
            try:
                case.PatientModel.StructureSets[exam_name].RoiGeometries[rois.OfRoi.Name].OfRoi.CreateAlgebraGeometry(
                    Examination=exam, Algorithm="Auto",
                    ExpressionA={'Operation': "Union", 'SourceRoiNames': [rois.OfRoi.Name], 'MarginSettings': {
                        'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0}},
                    ExpressionB={'Operation': "Union", 'SourceRoiNames': [r"CT_FOV"], 'MarginSettings': {
                        'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0}},
                    ResultOperation="Intersection", ResultMarginSettings={'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0})

                case.PatientModel.StructureSets[exam_name].SimplifyContours(RoiNames=[rois.OfRoi.Name], RemoveHoles3D=True, RemoveSmallContours=True,
                                                                            AreaThreshold=0.1, ReduceMaxNumberOfPointsInContours=True, MaxNumberOfPoints=1000, CreateCopyOfRoi=False, ResolveOverlappingContours=True)
                # crop all override ROIs outside of external
                for override_rois in override_ROIs:
                    if override_rois in support_ROIs:  # don't crop support ROIs
                        continue
                    case.PatientModel.StructureSets[exam_name].RoiGeometries[override_rois].OfRoi.CreateAlgebraGeometry(
                        Examination=exam, Algorithm="Auto",
                        ExpressionA={'Operation': "Union", 'SourceRoiNames': [override_rois], 'MarginSettings': {
                            'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0}},
                        ExpressionB={'Operation': "Union", 'SourceRoiNames': [rois.OfRoi.Name], 'MarginSettings': {
                            'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0}},
                        ResultOperation="Intersection", ResultMarginSettings={'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0})

            except:
                logger.debug("Crop failed. Is External an approved structure?")
                return False
            break

    return True


def CopyRoiGeometries_ver11(the_case, source_examination, target_examinationNames, roi_names, RayVersion):
    if RayVersion < 11:
        the_case.PatientModel.CopyRoiGeometries(SourceExamination=source_examination,
                                                TargetExaminationNames=target_examinationNames, RoiNames=roi_names)
    elif RayVersion < 12:
        the_case.PatientModel.CopyRoiGeometries(SourceExamination=source_examination,
                                                TargetExaminationNames=target_examinationNames, RoiNames=roi_names, ImageRegistrationNames=[])
    else:
        the_case.PatientModel.CopyRoiGeometries(SourceExamination=source_examination, TargetExaminationNames=target_examinationNames,
                                                RoiNames=roi_names, ImageRegistrationNames=[], TargetExaminationNamesToSkipAddedReg=[])
