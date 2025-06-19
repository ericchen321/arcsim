import os
import h5py
import trimesh
import numpy as np
from typing import Dict, List, Any

def set_marker_types(jsons: List[Dict[str, Any]]):
    for _, config in enumerate(jsons):
        h5_path = os.path.join(config['h5_output'], config['name'])
        h5_path += ".h5"
        
        # TODO: as it stands, springtime is only expecting 1 set of marker types
        #       per rollout, so we will only extract the marker types for the first mesh.
        kinematic = config['handles'][0]['nodes']
        mesh_path = config['cloths'][0]["mesh"]
        mesh = trimesh.load_mesh(mesh_path)

        vertex_count = len(mesh.vertices)

        marker_types = np.ones((vertex_count, 1))
        marker_types[kinematic] = 0

        with h5py.File(h5_path, 'a') as f:
            f.create_dataset('marker_types', data=marker_types) 
