import os
import h5py
import numpy as np
from typing import Dict, List, Any

def set_marker_types(jsons: List[Dict[str, Any]]):
    for _, config in enumerate(jsons):
        h5_path = os.path.join(config['h5_output'], config['name'])
        h5_path += ".h5"
        
        # TODO: as it stands, springtime is only expecting 1 set of marker types
        #       per rollout, so we will only extract the marker types for the first mesh.
        kinematic = config['handles'][0]['nodes']

        with h5py.File(h5_path, 'a') as f:
            xpos_particles = f['positions'][:]
            marker_types = np.ones((xpos_particles.shape[1]))
            marker_types[kinematic] = 0
            f.create_dataset('marker_types', data=marker_types) 
