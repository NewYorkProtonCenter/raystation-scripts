import platform
import sys

assert platform.python_implementation() == "CPython"
from connect import get_current
from System.Windows import *
import numpy as np


patient = 'hn5718'
ct_list0 = ['CT 1']
ct_list1 = ['ct1']
pet_list0 = ['PET 1']
pet_list1 = ['3mth']
roi_list0 = ['ctv', 'ctv5mm', 'ctv7mm', 'suv1', 'suv2', 'suv3', 'suv4', 'suv5', 'suv6']
roi_list1 = ['ctv', 'ctv5mm', 'ctv7mm', 'suv1', 'suv2', 'suv3', 'suv4', 'suv5', 'suv6']
dose_models = ['physical', 'Carabe', 'McNamara', 'Wedenberg']

# data_dir = 'W:/Users/Hang/radiobiology/MSKCC publication supplement/data_analysis/' + patient + '/data/'
data_dir = 'W:/Users/Hang/radiobiology/txt_data_from_rs/' + patient + '/'

case = get_current("Case")
beam_set = get_current("BeamSet")
dose_grid = beam_set.FractionDose.InDoseGrid

let_d = beam_set.FractionDose.DoseValues.PhysicalData.DoseAveragedLetData * 0.1  # in keV/um
dose_nominal = beam_set.FractionDose.DoseValues.DoseData * 0.01 / 1.1  # Physical Dose in Gy/fx

dose_grid_shape = dose_nominal.shape

if dose_grid_shape != let_d.shape:
	sys.exit('!!!!!!!!!!!!!!!! LET grid not equal to dose grid !!!')

print('#########################################################')
dose_opt = True
if dose_opt:
	print('Dose - ', dose_models[0], dose_nominal.shape, dose_nominal[70, 50, 90])
	file_nominal = data_dir + 'dose_' + dose_models[0] + '.txt'
	with open(file_nominal, 'w') as file_nominal_output:
		file_nominal_output.write('# Dose - ' + dose_models[0] + ' array shape: {0}\n'.format(dose_nominal.shape))
		slice_num = 0
		for slice_i in dose_nominal:
			file_nominal_output.write('# slice {0}\n'.format(slice_num))
			np.savetxt(file_nominal_output, slice_i)
			slice_num = slice_num + 1
	saved = np.loadtxt(file_nominal)
	saved = saved.reshape(dose_grid_shape)
	print('Dose - ', dose_models[0], saved.shape, saved[70, 50, 90])

print('#########################################################')
let_opt = True
if let_opt:
	print('LETd - ', let_d.shape, let_d[70, 50, 90])
	file_let = data_dir + 'let_d.txt'
	with open(file_let, 'w') as file_let_output:
		file_let_output.write('# LETd - array shape: {0}\n'.format(let_d.shape))
		slice_num = 0
		for slice_i in let_d:
			file_let_output.write('# slice {0}\n'.format(slice_num))
			np.savetxt(file_let_output, slice_i)
			slice_num = slice_num + 1
	saved = np.loadtxt(file_let)
	saved = saved.reshape(dose_grid_shape)
	print('LETd - ', saved.shape, saved[70, 50, 90])

print('#########################################################')
dose_opt = False
if dose_opt:
	for i in range(1, len(dose_models)):
		data = case.TreatmentDelivery.FractionEvaluations[0].DoseOnExaminations[0].DoseEvaluations[
			i - 1].DoseValues.DoseData
		print('Dose - ', dose_models[i], data.shape, data[70, 50, 90])

		file = data_dir + 'dose_' + dose_models[i] + '.txt'
		with open(file, 'w') as file_output:
			file_output.write('# Dose - ' + dose_models[i] + ' array shape: {0}\n'.format(data.shape))
			slice_num = 0
			for slice_i in data:
				file_output.write('# slice {0}\n'.format(slice_num))
				np.savetxt(file_output, slice_i)
				slice_num = slice_num + 1

		saved = np.loadtxt(file)
		saved = saved.reshape(dose_grid_shape)
		print('Dose - ', dose_models[i], saved.shape, saved[70, 50, 90])

print('#########################################################')
pet_opt = False
if pet_opt:
	for i in range(0, len(pet_list0)):
		data = case.Examinations[pet_list0[i]].Series[0].ImageStack.GetResampledPixelData(DoseGrid=dose_grid)
		data = data.reshape(dose_grid_shape)
		print(pet_list0[i], ' - ', pet_list1[i], data.shape, data[70, 50, 90])

		file = data_dir + 'pet_' + pet_list1[i] + '.txt'
		with open(file, 'w') as file_output:
			file_output.write(
				'# PET - ' + pet_list0[i] + ' - ' + pet_list1[i] + ' array shape: {0}\n'.format(data.shape))
			slice_num = 0
			for slice_i in data:
				file_output.write('# slice {0}\n'.format(slice_num))
				np.savetxt(file_output, slice_i)
				slice_num = slice_num + 1

		saved = np.loadtxt(file)
		saved = saved.reshape(dose_grid_shape)
		print(pet_list0[i], ' - ', pet_list1[i], saved.shape, saved[70, 50, 90])

print('#########################################################')
roi_opt = True
if roi_opt:
	for i in range(0, len(roi_list0)):
		data = case.PatientModel.StructureSets['CT 1'].RoiGeometries[roi_list0[i]].GetRoiGeometryAsVoxels(
			Corner=dose_grid.Corner, VoxelSize=dose_grid.VoxelSize, NrVoxels=dose_grid.NrVoxels)
		data = data.reshape(dose_grid_shape)
		print(roi_list0[i], ' - ', roi_list1[i], data.shape, data[70, 50, 90])

		file = data_dir + 'roi_' + roi_list1[i] + '.txt'
		with open(file, 'w') as file_output:
			file_output.write(
				'# ROI - ' + roi_list0[i] + ' - ' + roi_list1[i] + ' array shape: {0}\n'.format(data.shape))
			slice_num = 0
			for slice_i in data:
				file_output.write('# slice {0}\n'.format(slice_num))
				np.savetxt(file_output, slice_i)
				slice_num = slice_num + 1

		saved = np.loadtxt(file)
		saved = saved.reshape(dose_grid_shape)
		print(roi_list0[i], ' - ', roi_list1[i], saved.shape, saved[70, 50, 90])

print('#########################################################')
ct_opt = False
if ct_opt:
	for i in range(0, len(ct_list0)):
		data = case.Examinations[ct_list0[i]].Series[0].ImageStack.GetResampledPixelData(DoseGrid=dose_grid)
		data = data.reshape(dose_grid_shape)
		if case.Examinations[ct_list0[i]].Series[0].ImageStack.ConversionParameters.RescaleIntercept != -1024 or case.Examinations[ct_list0[i]].Series[0].ImageStack.ConversionParameters.RescaleSlope != 1:
			print(case.Examinations[ct_list0[i]].Series[0].ImageStack.ConversionParameters.RescaleIntercept, case.Examinations[ct_list0[i]].Series[0].ImageStack.ConversionParameters.RescaleSlope)

		data = data * case.Examinations[ct_list0[i]].Series[0].ImageStack.ConversionParameters.RescaleSlope + case.Examinations[ct_list0[i]].Series[0].ImageStack.ConversionParameters.RescaleIntercept

		print(ct_list0[i], ' - ', ct_list1[i], data.shape, data[70, 50, 90])

		file = data_dir + 'ct_' + ct_list1[i] + '.txt'
		with open(file, 'w') as file_output:
			file_output.write(
				'# CT - ' + ct_list0[i] + ' - ' + ct_list1[i] + ' array shape: {0}\n'.format(data.shape))
			slice_num = 0
			for slice_i in data:
				file_output.write('# slice {0}\n'.format(slice_num))
				np.savetxt(file_output, slice_i)
				slice_num = slice_num + 1

		saved = np.loadtxt(file)
		saved = saved.reshape(dose_grid_shape)
		print(ct_list0[i], ' - ', ct_list1[i], saved.shape, saved[70, 50, 90])
