# Author: Guanxiong, Ganidhu


from typing import Dict, Any, List

def build_jsons(master_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build JSONs from the master configuration.

    Parameters:
        master_config (Dict[str, Any]): The master configuration dictionary.

    Returns:
        A list of JSON configurations, one for each rollout.
    """

    frame_time = 1.0 / master_config["sim_fps"]
    frame_steps = master_config["sim_substeps"]
    duration = master_config["sim_duration"]
    cloth_meshes = master_config["meshes"]
    cloth_materials = master_config["materials"]
    gravity = [0.0, master_config["grav_const"], 0.0]
    disable = ["popfilter", "strainlimiting", "remeshing", "fracture"]

    cloth_transforms = []
    handles = []
    for i in cloth_meshes:
        transform = {
            "translate": [0, 0, 0],
            "rotate": [45, 1, 0, 0],
        }

        handle = {
            "nodes": [0, 1, 16, 17, 14, 15, 29, 30]
        }

        cloth_transforms.append(transform)
        handles.append(handle)

    cloths = []
    for i in range(len(cloth_meshes)):
        cloth = {
            "mesh": cloth_meshes[i],
            "transform": cloth_transforms[i],
            "materials": cloth_materials[i]
        }

        cloths.append(cloth)

    json_data = {
        "frame_time": frame_time,
        "frame_steps": frame_steps,
        "duration": duration,
        "cloths": cloths,
        "handles": handles,
        "gravity": gravity,
        "disable": disable
    }

    num_rollouts = master_config["rollouts"]["num_rollouts"]
    jsons = []

    # TODO: initialize I.C data randomly
    for i in range(num_rollouts):
        jsons.append(json_data)


    return jsons
