# Author: Guanxiong, Ganidhu

import trimesh
import copy
import numpy as np
from typing import Dict, Any, List
from sklearn.neighbors import NearestNeighbors

def build_jsons(master_config: Dict[str, Any], output_dir: str) -> List[Dict[str, Any]] | List[Dict[str, Any]]:
    """
    Build JSONs from the master configuration.

    Parameters:
        master_config (Dict[str, Any]): The master configuration dictionary.
        output_dir: The output dir for the h5 files.

    Returns:
        A list of JSON configurations, one for each rollout.
    """

    frame_time = 1.0 / master_config["sim_fps"]
    frame_steps = master_config["sim_substeps"]
    duration = master_config["sim_duration"]
    cloth_meshes = master_config["meshes"]
    cloth_material = master_config["material"]
    gravity = [0.0, master_config["grav_const"], 0.0]
    disable = ["popfilter", "strainlimiting", "remeshing", "fracture"]

    num_anchors = master_config["rollouts"]["num_anchors"]
    num_pts_per_anchor = master_config["rollouts"]["num_pts_per_anchor"]
    trained_knns = []
    loaded_meshes = []

    cloth_transforms = []
    for mesh_path in cloth_meshes:
        transform = {
            "rotate": [0, 1, 0, 0],
        }

        mesh = trimesh.load_mesh(mesh_path)
        mesh.merge_vertices(True, True, 3, 3, 2)

        knn = NearestNeighbors(n_neighbors=num_pts_per_anchor - 1)
        knn.fit(mesh.vertices)

        trained_knns.append(knn)
        loaded_meshes.append(mesh)

        cloth_transforms.append(transform)

    cloths = []
    for i in range(len(cloth_meshes)):
        cloth = {
            "mesh": cloth_meshes[i],
            "transform": cloth_transforms[i],
            "materials": [{
                "data": cloth_material
            }],
            "remeshing": {
                "size": [1, 1]
            }
        }

        cloths.append(cloth)

    num_rollouts = master_config["rollouts"]["num_rollouts"]
    test_ratio = master_config["rollouts"]["test_ratio"]
    test_rollouts = max(1, num_rollouts * test_ratio)
    train_idx = range(int(num_rollouts - test_rollouts))
    test_idx = np.setdiff1d(range(num_rollouts), train_idx)

    jsons = []

    col_size = master_config["mesh_data"]["col_count"]
    row_size = master_config["mesh_data"]["row_count"]
    corner_idx = [
        0, col_size - 1, col_size * row_size - 1, col_size * row_size - row_size
    ]

    # generate one additional "default rollout" containing the default mesh data (e.g. rest configuration) 
    handles = []
    for cloth in cloths:
        cloth["transform"]["rotate"] = [0., 0., 0., 0.]
        handles.append({"nodes": [0]})

    json_data = {
        "name": f'default_rollout',
        "h5_output": f'{output_dir}/',
        "frame_time": frame_time,
        "frame_steps": frame_steps,
        "end_time": duration,
        "cloths": copy.deepcopy(cloths),
        "handles": handles,
        "gravity": gravity,
        "disable": disable
    }

    jsons.append(json_data.copy())

    for rollout_idx in range(num_rollouts):
        handles = []
        for cloth in cloths:
            if "custom_rotation" in master_config["rollouts"]:
                rot = master_config["rollouts"]["custom_rotation"]
            else:
                # randomize starting orientation of cloth
                rot = np.random.random((4,)).tolist()
                rot[0] *= 90.0 # rotation angle in the range of 0 to 90


            cloth["transform"]["rotate"] = rot

            knn = trained_knns[i]
            mesh = loaded_meshes[i]

            if rollout_idx in test_idx:
                anchor_ctr_idxs = np.random.choice(
                    corner_idx, num_anchors, replace=False)
            else:
                anchor_ctr_idxs = np.random.choice(
                    len(mesh.vertices), num_anchors, replace=False)

            if "custom_handles" in master_config["rollouts"]:
                handles.append({"nodes": master_config["rollouts"]["custom_handles"]})
            else:
                if num_pts_per_anchor > 1:
                    _, idx = knn.kneighbors(mesh.vertices[anchor_ctr_idxs])
                    handles.append({"nodes": idx.flatten().tolist()})

                else:
                    handles.append({"nodes": anchor_ctr_idxs.tolist()})

        json_data = {
            "name": f'rollout_{rollout_idx:03d}',
            "h5_output": f'{output_dir}/',
            "frame_time": frame_time,
            "frame_steps": frame_steps,
            "end_time": duration,
            "cloths": copy.deepcopy(cloths),
            "handles": handles,
            "gravity": gravity,
            "disable": disable
        }

        if rollout_idx in test_idx:
            json_data["h5_output"] = f'{output_dir}/test/'
            jsons.append(json_data.copy())
        else:
            json_data["h5_output"] = f'{output_dir}/train/'
            jsons.append(json_data.copy())

    return jsons
