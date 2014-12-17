from __future__ import division
from traits.api import HasTraits, Array, String, Int, Float, Bool, Instance, Event, on_trait_change, Tuple, ListInstance, Dict, List
from traitsui.api import View, Item
from chaco.api import ArrayPlotData, Plot, GridDataSource, ImageData
from enable.component_editor import ComponentEditor
import h5py
import numpy as np
array = np.array
from bottleneck import anynan


class DataError(Exception):
    pass
class DataContainer(HasTraits):
    name = String()
    desc = String('')
    h5_group = Instance(h5py.Group)
    h5_label = String()
    plotdata = Instance(ArrayPlotData)    
    idx = Int(-1)
    full = Bool(False)
    def prepare_h5(self, base):
        if not self.h5_label:
            if self.name not in base:
                self.h5_label = self.name
            else:
                idx = 1
                while self.name + str(idx) in base:
                    idx = idx +1
                self.h5_label = self.name + str(idx)
            group = base.create_group(self.h5_label)
            self.h5_group = group
            group.attrs["classname"] = self.__class__.__name__
            if self.desc:
                group.attrs["desc"] = self.desc

class Dataset(HasTraits):
    data=Array()
    label=String('')
    unit=String('')
    desc = String('')
    
    changed = Event()
    def __init__(self, label, data=None, points=None, unit='', desc= ''):
        super(Dataset, self).__init__()
        if isinstance(data, np.ndarray):
            self.data = data
        elif points:
            self.data = np.empty(points)
            self.data[:] = np.nan
        else:
            raise DataError('Unknown data definition')
        self.label = label
        if unit is None:
            self.unit = ''
        else:
            self.unit = unit
        if desc is None:
            self.desc = ''
        else:
            self.desc = desc
    def axis_label(self):
        if self.unit:
            return self.label + " [{}]".format(self.unit)
        else:
            return self.label
    def write_h5(self, base):
        if self.label in base.keys():
            if len(self.data.shape) == 1:
                base[self.label][...] = self.data
            elif len(self.data.shape) == 2:
                base[self.label][...] = self.data
            elif len(self.data.shape) == 3:
                base[self.label][...] = self.data
                print('updated 3D DATA')
        else:
            data_dset = base.create_dataset(self.label, data = self.data)
            data_dset.attrs["label"] = self.label            
            data_dset.attrs["unit"] = self.unit
            data_dset.attrs["desc"] = self.desc 
    def copy(self):
        return Dataset(self.label, unit=self.unit, desc=self.desc, data=self.data.copy())

class DataXY(DataContainer):
    x = Instance(Dataset)
    y = Instance(Dataset)
    idx = Int(-1)
    full = Bool(False)
    changed = Event()
    complete = Event()
    def __init__(self, name, x=None, y=None, points=None, x_label=None, x_unit='', x_desc='', y_label=None, y_unit='', y_desc=''):
        self.name = name
        if isinstance(x, Dataset):
            self.x = x.copy()
        elif points is not None:
            newdata = np.empty(points)
            newdata[:] = np.nan
            self.x = Dataset(x_label, unit=x_unit, desc=x_desc, data=newdata)
        else:
            raise DataError('Unsupported data type supplied for X')
        if y is None:
            newdata = np.empty(len(self.x.data))
            newdata[:] = np.nan
            self.y = Dataset(y_label, unit=y_unit, desc=y_desc, data=newdata)
        elif isinstance(y, Dataset):
            self.y=y.copy()
        self.plotdata = ArrayPlotData(x_data=self.x.data, y_data=self.y.data)
        self.on_trait_change(self.source_new_data, 'y.data')
    def source_new_data(self):
        self.full = True
        self.complete=True
    def add_point(self, newpoint, x=None):
        self.idx = self.idx + 1
        if np.isscalar(newpoint):
            self.y.data[self.idx] = newpoint
        if x is not None:
            self.x.data[self.idx] = x
        if self.idx >= len(self.y.data)-1:
            self.full = True
            self.complete = True
        self.changed = True
    def clear(self):
        self.full = False
        self.idx = -1
        self.y.data[:] = np.nan
    def write_h5(self, base):
        self.prepare_h5(base)
        self.x.write_h5(self.h5_group)
        self.y.write_h5(self.h5_group)
        
class DataXYZ(DataContainer):
    x = Instance(Dataset)
    y = Instance(Dataset)
    z = Instance(Dataset)
    idx = Int(-1)
    source = Instance(DataXY)
    full = Bool(False)
    
    complete = Event()
    changed = Event()
    plotdata = Instance(ArrayPlotData)
    def __init__(self, name, x, y, z=None, link_source=False):
        self.name = name
        if isinstance(x, Dataset):
            self.x = x.copy()
        if isinstance(y, Dataset):
            self.y = y.copy()
        elif isinstance(y, DataXY):
            # Using a DataXY as prototype for both y and z directions.
            self.y = y.x.copy()
            newdata=np.empty((len(self.y.data), len(self.x.data)))
            newdata[:] = np.nan
            self.z = Dataset(y.y.label, unit=y.y.unit, desc=y.y.desc, data=newdata)
        else:
            raise DataError('Unsupported data type supplied for Y')
        if isinstance(z, Dataset):
            if z.data.shape[1] == len(x.data) and z.data.shape[0] == len(y.data):
                self.z = z.copy()
            else:
                raise DataError('Dimension mismatch')
        elif z is None and not isinstance(y, DataXY):
            newdata=np.empty((len(self.y.data), len(self.x.data)))
            newdata[:] = np.nan
            self.z = Dataset('z data', data=newdata) 
        if link_source:
            self.source = y
            self.on_trait_event(self.update_from_source, 'source:complete')
        x_pixwidth = (self.x.data[-1]-self.x.data[0])/len(self.x.data)
        x_bounds = np.linspace(self.x.data[0]-x_pixwidth/2.0, self.x.data[-1]+x_pixwidth/2.0, len(self.x.data)+1)
        y_pixwidth = (self.y.data[-1]-self.y.data[0])/len(self.y.data)
        y_bounds = np.linspace(self.y.data[0]-y_pixwidth/2.0, self.y.data[-1]+y_pixwidth/2.0, len(self.y.data)+1) 
        self.plotdata = ArrayPlotData(x_data=self.x.data, y_data=self.y.data, x_bounds=x_bounds, y_bounds=y_bounds)
        self.plotdata.set_data('z_data', self.z.data)
    def update_from_source(self):
        self.add_line(self.source)
        print('adding line to XYZ!')
    def add_line(self, newline, x=None):
        if self.full:
            raise DataError('The data container is already full')
        self.idx = self.idx + 1
        if isinstance(newline, Dataset):
            self.z.data[:,self.idx] = newline.data
        elif isinstance(newline, DataXY):
            self.z.data[:,self.idx] = newline.y.data
        else:
            raise DataError('Unsupported data')
        if x is not None:
            self.x.data[self.idx] = x
        if self.idx >= len(self.x.data)-1:
            self.full = True
            self.complete = True
        self.changed = True
        self.update_plots()
    @on_trait_change('z.data')
    def update_plots(self):
        self.plotdata.set_data('z_data', self.z.data)
        print('Updating the XYZ plot!')
    def write_h5(self, base):
        self.prepare_h5(base)
        self.x.write_h5(self.h5_group)
        self.y.write_h5(self.h5_group)
        self.z.write_h5(self.h5_group)
    def clear(self):
        self.full = False
        self.idx = -1
        self.z.data[:] = np.nan
class DataXYNZ(DataContainer):
    x = Instance(Dataset)
    y = Instance(Dataset)
    n = Instance(Dataset)
    z = Instance(Dataset)
    idx = Int(-1)
    source = Instance(DataXYZ)
    full = Bool(False)
    complete = Event()
    changed = Event()
    plotdata = Instance(ArrayPlotData)
    def __init__(self, name, n, xyz, link_source=False):
        self.name = name
        if isinstance(n, Dataset):
            self.n = n.copy()
        if isinstance(xyz, DataXYZ):
            self.x = xyz.x.copy()
            self.y = xyz.y.copy()
            newdata=np.empty((len(self.y.data), len(self.x.data), len(self.n.data)))
            newdata[:] = np.nan
            self.z = Dataset(xyz.z.label, unit=xyz.z.unit, desc=xyz.z.desc, data=newdata)
        else:
            raise DataError('Unsupported data type')
        if link_source:
            self.source = xyz
            self.on_trait_event(self.update_from_source, 'source:complete')
    def update_from_source(self):
        self.add_frame(self.source)
        print('adding frame to XYNZ!')
    def add_frame(self, newframe, n=None):
        if self.full:
            raise DataError('The data container is already full')
        self.idx = self.idx + 1
        if isinstance(newframe, Dataset):
            self.z.data[:,:,self.idx] = newframe.data
        elif isinstance(newframe, DataXYZ):
            self.z.data[:,:,self.idx] = newframe.z.data
        else:
            raise DataError('Unsupported data')
        if n is not None:
            self.n.data[self.idx] = n
        if self.idx >= len(self.n.data)-1:
            self.full = True
            self.complete = True
        self.changed = True
    def write_h5(self, base):
        self.prepare_h5(base)
        self.x.write_h5(self.h5_group)
        self.y.write_h5(self.h5_group)
        self.n.write_h5(self.h5_group)
        self.z.write_h5(self.h5_group)
if __name__ == '__main__':
    x = Dataset('freq', unit='Hz', desc='vanlig', data=np.empty(7))
    p = Dataset('power', unit='dBm', desc='ovanlig', data=np.empty(5))
    y1 = Dataset('mag', unit='dB', desc='kanin1', points=7)
    xy = DataXY('VNA trace', x=x, y=y1)
    xyz = DataXYZ('I Q frame', x=p, y=xy, link_source=True)
    y1.data = np.arange(7)
    print(xy.y.data)
    print(xyz.z.data)
    #f = h5py.File("C:\\Documents and Settings\\Martin\\Desktop\\file tests\\tst4.h5")
    #xyz.write_h5(f)
    #xy.write_h5(f)
    #p.write_h5(f)
    #f.flush()
    #f.close()