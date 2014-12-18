from traits.api import HasTraits, SingletonHasTraits, Array, String, Int, Float, Bool, Instance, Event, on_trait_change, Tuple, ListInstance, Dict, List
from traitsui.api import View, Item
import time
import os
import h5py


class ExperimentMaster(SingletonHasTraits):
    stack = List([])
    base_dir = String('experiment_codetest')
    save_list = List([])
    inited = Bool(False)
    
    def enter_experiment(self, exp):
        if not self.inited:
            
            savelabel = exp.label + time.strftime(" %Y-%m-%d_%H%M%S")
            new_dir = self.base_dir + "/" + savelabel
            os.mkdir(new_dir)
            h5_filepath = new_dir + "/data.hdf5"
            print(h5_filepath)
            new_group = h5py.File(h5_filepath, "w")
            new_stacktop = {"dir": new_dir, "level": 0, "h5_group": new_group, "save_list": [exp]}
            self.stack.append(new_stacktop)
            self.inited = True
        else:
            old_stacktop = self.stack[-1]
            savelabel = exp.label + time.strftime(" %Y-%m-%d_%H%M%S")
            new_dir = old_stacktop["dir"] + "/" + savelabel
            os.mkdir(new_dir)
            new_group = old_stacktop["h5_group"].create_group(savelabel)
            level = old_stacktop["level"]+1
            new_stacktop = {"dir": new_dir, "level": level, "h5_group": new_group, "save_list": [exp]}
            
            self.stack.append(new_stacktop)
            self.save_list.append(new_stacktop)
        
    def exit_experiment(self):
        stacktop = self.stack.pop()
        print(stacktop)
        for comp in stacktop["save_list"]:
            comp.save(stacktop)

    def register_component(self, comp):
        stacktop = self.stack[-1]
        stacktop["save_list"].append(comp)

class Experiment(HasTraits):
    label = "Undefined experiment"
    master = Instance(ExperimentMaster())
    
    def script(self):
        # Override with custom code
        pass
    
    def save(self):
        print("saving experiment")
        
    def run(self):
        self.master = ExperimentMaster()
        self.master.enter_experiment(self)
        self.script()
        self.master.exit_experiment(self)

class Component(HasTraits):
    master = Instance(ExperimentMaster)
    
    def save(self, stacktop):
        self.master = ExperimentMaster()
        print('Saving Component')
        print(stacktop)
    
if __name__ == "__main__":
    e = Experiment()
    m = ExperimentMaster()
    m.enter_experiment(e)
    e2 = Experiment()
    m.enter_experiment(e2)
    print(m.stack)
    c = Component()
    m.register_component(c)
    m.exit_experiment()