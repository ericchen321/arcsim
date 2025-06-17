/*
  Copyright ©2013 The Regents of the University of California
  (Regents). All Rights Reserved. Permission to use, copy, modify, and
  distribute this software and its documentation for educational,
  research, and not-for-profit purposes, without fee and without a
  signed licensing agreement, is hereby granted, provided that the
  above copyright notice, this paragraph and the following two
  paragraphs appear in all copies, modifications, and
  distributions. Contact The Office of Technology Licensing, UC
  Berkeley, 2150 Shattuck Avenue, Suite 510, Berkeley, CA 94720-1620,
  (510) 643-7201, for commercial licensing opportunities.

  IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT,
  INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING
  LOST PROFITS, ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS
  DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED OF THE POSSIBILITY
  OF SUCH DAMAGE.

  REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT
  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
  FOR A PARTICULAR PURPOSE. THE SOFTWARE AND ACCOMPANYING
  DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED "AS
  IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT,
  UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
*/

#include "runphysics.hpp"

#include "conf.hpp"
#include "io.hpp"
#include "misc.hpp"
#include "separateobs.hpp"
#include "simulation.hpp"
#include "timer.hpp"
#include "util.hpp"
#include <boost/filesystem.hpp>
#include <cstdio>
#include <fstream>

#include <H5Cpp.h>
using namespace H5;

using namespace std;

string inprefix, outprefix;
static fstream timingfile;

Simulation sim;
std::vector<Mesh> saved_meshes;
std::vector<std::vector<Vec3>> positions;
int frame;
Timer fps;

void copy_file (const string &input, const string &output);

void init_physics (const string &json_file, string outprefix,
                   bool is_reloading) {
    load_json(json_file, sim);
    ::outprefix = outprefix;
    if (!outprefix.empty()) {
        ::timingfile.open(stringf("%s/timing", outprefix.c_str()).c_str(),
                          is_reloading ? ios::out|ios::app : ios::out);
        // Make a copy of the config file for future use
        copy_file(json_file.c_str(), stringf("%s/conf.json",outprefix.c_str()));
        // And copy over all the obstacles
        vector<Mesh*> base_meshes(sim.obstacles.size());
        for (int o = 0; o < (int)sim.obstacles.size(); o++)
            base_meshes[o] = &sim.obstacles[o].base_mesh;
        save_objs(base_meshes, stringf("%s/obs", outprefix.c_str()));
    }
    prepare(sim);    
}

void init_relax() {
	separate_obstacles(sim.obstacle_meshes, sim.cloth_meshes);
    relax_initial_state(sim);    
}

static void save (vector<Mesh*> &meshes, int frame) {
    if (!outprefix.empty() && frame < 100000)
        save_state(sim, stringf("%s/%05d", outprefix.c_str(), frame));

    if (sim.name != "none") {
        // Only tracking the state of the first cloth mesh in the simulation.
        //saved_meshes.push_back(sim.cloths[0].mesh);
        // gather up position
        std::vector<Vec3> pos;
        for (int j = 0; j < sim.cloths[0].mesh.verts.size(); j++) {
            pos.push_back(sim.cloths[0].mesh.verts[j]->node->x);
        }
        positions.push_back(pos);
    }
}

static void save_timings () {
    static double old_totals[Simulation::nModules] = {};
    if (!::timingfile)
        return; // printing timing data to stdout is getting annoying
    ostream &out = ::timingfile ? ::timingfile : cout;
    for (int i = 0; i < Simulation::nModules; i++) {
        out << sim.timers[i].total - old_totals[i] << " ";
        old_totals[i] = sim.timers[i].total;
    }
    out << endl;
}

Vec3 vector_subtract(Vec3 a, Vec3 b) {
    Vec3 c = Vec3(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
    return c;
}

// TODO: currently we make an assumption that all arcsim simulations involve only a single cloth mesh.
void save_h5(Simulation& sim) {    
    std::string data_dir = sim.h5_output;
    std::string file_name = sim.name;
    file_name += ".h5";

    std::string path = data_dir + file_name;
    hid_t file_id = H5Fcreate(path.c_str(), H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);

    // compute velocities
    std::vector<std::vector<Vec3>> velocities;
    for (int i = 1; i < positions.size(); i++) {
        std::vector<Vec3> vel;
        for (int j = 0; j < positions[i].size(); j++) {
            Vec3 velocity = positions[i][j] - positions[i - 1][j];
            vel.push_back(velocity);
        }
        velocities.push_back(vel);
    }

    // erase first element so velocity and positions data have same size.
    if (positions.size() > velocities.size()) {
        positions.erase(positions.begin());
    }
    
    hsize_t dim_pos[3] = {positions.size(), positions[0].size(), 3 };
    hid_t pos_id = H5Screate_simple(3, dim_pos, NULL);
    hid_t dataset_pos_id = H5Dcreate2(file_id, "/positions", H5T_NATIVE_FLOAT, pos_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    H5Dwrite(dataset_pos_id, H5T_NATIVE_FLOAT, H5S_ALL, H5S_ALL, H5P_DEFAULT, positions.data());
    H5Dclose(dataset_pos_id);
    H5Sclose(pos_id);

    hsize_t dim_vel[3] = {velocities.size(), velocities[0].size(), 3 };
    hid_t vel_id = H5Screate_simple(3, dim_vel, NULL);
    hid_t dataset_vel_id = H5Dcreate2(file_id, "/velocities", H5T_NATIVE_FLOAT, vel_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    H5Dwrite(dataset_vel_id, H5T_NATIVE_FLOAT, H5S_ALL, H5S_ALL, H5P_DEFAULT, velocities.data());
    H5Dclose(dataset_vel_id);
    H5Sclose(vel_id);

    H5Fclose(file_id);
}

void save (Simulation &sim, int frame) {
    save(sim.cloth_meshes, frame);
}

void sim_step() {
    fps.tick();
    advance_step(sim);
    if ((sim.step % sim.frame_steps == 0) && (sim.step % sim.save_every) == 0) {
        save(sim, sim.frame);
        save_timings();
    }
    fps.tock();
    if (sim.time >= sim.end_time || sim.frame >= sim.end_frame) {
        save_h5(sim);
        exit(EXIT_SUCCESS);
    }
}

void offline_loop() {
    while (true)
        sim_step();
}

void run_physics (const vector<string> &args) {
    if (args.size() != 1 && args.size() != 2) {
        cout << "Runs the simulation in batch mode." << endl;
        cout << "Arguments:" << endl;
        cout << "    <scene-file>: JSON file describing the simulation setup"
             << endl;
        cout << "    <out-dir> (optional): Directory to save output in" << endl;
        exit(EXIT_FAILURE);
    }
    string json_file = args[0];
    string outprefix = args.size()>1 ? args[1] : "";
    if (!outprefix.empty())
        ensure_existing_directory(outprefix);
    init_physics(json_file, outprefix, false);
    init_relax();
    if (!outprefix.empty())
        save(sim, 0);
    offline_loop();
}

void init_resume(const vector<string> &args) {
    assert(args.size() == 2);
    string outprefix = args[0];
    string start_frame_str = args[1];
    // Load like we would normally begin physics
    init_physics(stringf("%s/conf.json", outprefix.c_str()), outprefix, true);
    // Get the initialization information
    sim.frame = atoi(start_frame_str.c_str());
    for (int i=0; i<sim.frame; i++)
    	sim.time += sim.frame_time;
    sim.step = sim.frame * sim.frame_steps;
    for(int i=0; i<(int)sim.obstacles.size(); ++i)
        sim.obstacles[i].get_mesh(sim.time);
    prepare(sim); // set cloth meshes etc.
    load_state(sim, stringf("%s/%05d",outprefix.c_str(),sim.frame));
    //separate_obstacles(sim.obstacle_meshes, sim.cloth_meshes);
}

void resume_physics (const vector<string> &args) {
    if (args.size() != 2) {
        cout << "Resumes an incomplete simulation in batch mode." << endl;
        cout << "Arguments:" << endl;
        cout << "    <out-dir>: Directory containing simulation output files"
             << endl;
        cout << "    <resume-frame>: Frame number to resume from" << endl;
        exit(EXIT_FAILURE);
    }
    init_resume(args);
    offline_loop();
}

void copy_file (const string &input, const string &output) {
    return;
    if(input == output) {
        return;
    }
    if(boost::filesystem::exists(output)) {
        boost::filesystem::remove(output);
    }
    boost::filesystem::copy_file(
        input, output);
}
