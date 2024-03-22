# encoding: utf8

# Contains treatment plan tests for individual treatment plans.
#
# Verified for RayStation 6.0.

# GUI framework (debugging only):
#clr.AddReference("PresentationFramework")
#from System.Windows import *

# Local script imports:
from ts_classes import test as TEST

# This class contains tests for the RayStation ROI object:
class TSROI(object):
  def __init__(self, roi, ts_case=None):
    # RayStation objects:
    self.roi = roi
    # Related test suite objects:
    self.ts_case = ts_case
    if ts_case:
      ts_case.ts_rois.append(self)
      self.parent_param = ts_case.param
    else:
      self.parent_param = None
    # Parameters:
    self.param = TEST.Parameter('ROI', self.roi.Name, self.parent_param) # (roi parameter)

