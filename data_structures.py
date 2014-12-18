from __future__ import division
from traits.api import HasTraits, Array, String, Int, Float, Bool, Instance, Event, on_trait_change, Tuple, ListInstance, Dict, List
from traitsui.api import View, Item
from chaco.api import ArrayPlotData, Plot, GridDataSource, ImageData
from enable.component_editor import ComponentEditor
import h5py
import numpy as np
import uuid
array = np.array
from bottleneck import anynan


class DataError(Exception):
    pass
    
class DataX(HasTraits):
    # Rewritten and simplified
    description = String('')
    uuid = String()
    
    values = Array()
    unit = String()
    label = String()
    
    def __init__(self, x, label = '', unit = '', description = ''):
        self.uuid = uuid.uuid4().hex
        self.description = description
        if isinstance(x, DataX):
            self.values = x.values.copy()
            self.label = x.label
            self.unit = x.unit
        elif isinstance(x, np.ndarray):
            self.values = x
        elif isinstance(x, int):
            self.values = np.empty(x)
            self.values[:] = np.nan
        if label:
            self.label = label
        if unit:
            self.unit = unit

    def write_h5(self, h5_base):
        dset = h5_base.create_dataset(self.uuid, data=self.values)
        dset.attrs["unit"] = self.unit
        dset.attrs["label"] = self.label
        dset.attrs["description"] = self.description
        dset.attrs["uuid"] = self.uuid

class DataXY(HasTraits):
    # Rewritten and simplified
    label = String()
    description = String('')
    uuid = String()

    values = Array()
    unit = String()
    
    x = Instance(DataX)
    
    full = Bool(False)
    index = Int(-1)
    
    def __init__(self, x, y = None, label = '', unit = '', description = ''):
        self.uuid = uuid.uuid4().hex
        self.label = label
        self.description = description
        self.unit = unit
        
        self.x = x
        
        if isinstance(y, DataX):
            self.values = x.values.copy()
            self.label = x.label
            self.unit = x.unit
        elif isinstance(x, np.ndarray):
            self.values = x
        elif not y:
            self.values = np.empty(len(x.values))
            self.values[:] = np.nan

    def add_point(self, newpoint, x=None):
        if self.full:
            raise DataError('The data container is already full')
        self.index = self.index + 1
        if isinstance(newpoint, Number):
            self.values[:,self.index] = newpoint
            if x is not None:
                self.x.value[self.idx] = x
        elif isinstance(newline, tuple):
            self.x.values[:,self.index] = newpoint[0]
            self.values[:,self.index] = newpoint[1]
        else:
            raise DataError('Unsupported data')
        if self.idx >= self.values.shape[0]-1:
            self.full = True
        self.changed = True
        
    def write_h5(self, h5_base):
        dset = h5_base.create_dataset(self.uuid, data=self.values)
        dset.attrs["unit"] = self.unit
        dset.attrs["label"] = self.label
        dset.attrs["description"] = self.description
        dset.attrs["uuid"] = self.uuid

class DataXYZ(HasTraits):
    # Rewritten and simplified. Does not contain the x- and y-arrays
    description = String('')
    uuid = String()
    
    x = Instance(DataX)
    y = Instance(DataX)
    values = Array()
    label = String('z')
    unit = String('')
    
    full = Bool(False)
    index = Int(-1)
    changed = Event()
    
    def __init__(self, x, y, label = '', unit = '', description = ''):
        self.uuid = uuid.uuid4().hex
        self.label = label
        self.description = description
        self.unit = unit

        self.x = x
        self.y = y
        
        self.values = np.empty(len(x.values),len(y.values))
        self.values[:] = np.nan
    
    def add_line(self, newline, x=None):
        if self.full:
            raise DataError('The data container is already full')
        self.index = self.index + 1
        if isinstance(newline, DataX):
            self.values[:,self.index] = newline.values
        elif isinstance(newline, np.ndarray):
            self.values[:,self.index] = newline
        elif isinstance(newline, DataXY):
            self.values[:,self.index] = newline.values
        else:
            raise DataError('Unsupported data')
        if x is not None:
            self.x.value[self.idx] = x
        if self.idx >= self.values.shape[0]-1:
            self.full = True
        self.changed = True
    
    def write_h5(self, h5_base):        
        dset = h5_base.create_dataset(self.uuid, data=self.values)
        dset.attrs["label"] = self.label            
        dset.attrs["unit"] = self.unit
        dset.attrs["description"] = self.description
        dset.attrs["uuid"] = self.uuid
        dset.attrs["x"] = self.x.uuid
        dset.attrs["y"] = self.y.uuid
        dset.attrs["class"] = self.__class__.__name__

if __name__ == '__main__':
