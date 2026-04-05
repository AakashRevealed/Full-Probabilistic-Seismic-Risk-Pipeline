# src/geometry_gmsh.py
#
# Gmsh 3D FE mesh of building for ParaView.

import os
import gmsh
import meshio


def build_gmsh_building(geom_params,
                        msh_path="mesh/building.msh",
                        vtu_path="mesh/building.vtu"):

    os.makedirs(os.path.dirname(msh_path), exist_ok=True)

    try:
        if gmsh.isInitialized():
            gmsh.finalize()

        gmsh.initialize()
        gmsh.model.add("building")
    
        n_stories     = geom_params["n_stories"]
        story_heights = geom_params["story_heights"]
        bay_lengths_x = geom_params["bay_lengths_x"]
        bay_lengths_y = geom_params["bay_lengths_y"]
        mesh_size     = geom_params.get("mesh_size", 1.0)
            
        Lx = sum(bay_lengths_x)
        Ly = sum(bay_lengths_y)
        H  = sum(story_heights)
        print(f"GMSH: Lx={Lx}, Ly={Ly}, H={H}")
    
        # p1 = gmsh.model.occ.addPoint(0.0, 0.0, 0.0, mesh_size)
        # p2 = gmsh.model.occ.addPoint(Lx, 0.0, 0.0, mesh_size)
        # p3 = gmsh.model.occ.addPoint(Lx, Ly, 0.0, mesh_size)
        # p4 = gmsh.model.occ.addPoint(0.0, Ly, 0.0, mesh_size)
    
        # l1 = gmsh.model.occ.addLine(p1, p2)
        # l2 = gmsh.model.occ.addLine(p2, p3)
        # l3 = gmsh.model.occ.addLine(p3, p4)
        # l4 = gmsh.model.occ.addLine(p4, p1)
    
        # cl = gmsh.model.occ.addCurveLoop([l1, l2, l3, l4])
        # s  = gmsh.model.occ.addPlaneSurface([cl])
    
        # gmsh.model.occ.extrude([(2, s)], 0.0, 0.0, H)
        # --- Generate grid coordinates ---
        x_coords = [0.0]
        for L in bay_lengths_x:
            x_coords.append(x_coords[-1] + L)
        
        y_coords = [0.0]
        for L in bay_lengths_y:
            y_coords.append(y_coords[-1] + L)
        
        z_coords = [0.0]
        for h in story_heights:
            z_coords.append(z_coords[-1] + h)
        
        
        # --- Create points (nodes) ---
        point_tags = {}
        
        for iz in range(len(z_coords)):
            for iy in range(len(y_coords)):
                for ix in range(len(x_coords)):
        
                    x = x_coords[ix]
                    y = y_coords[iy]
                    z = z_coords[iz]
        
                    tag = gmsh.model.occ.addPoint(x, y, z, mesh_size)
                    point_tags[(ix, iy, iz)] = tag
        
        
        # --- Columns (vertical elements) ---
        for iz in range(len(z_coords) - 1):
            for iy in range(len(y_coords)):
                for ix in range(len(x_coords)):
        
                    p1 = point_tags[(ix, iy, iz)]
                    p2 = point_tags[(ix, iy, iz + 1)]
        
                    gmsh.model.occ.addLine(p1, p2)
        
        
        # --- Beams in X direction ---
        for iz in range(1, len(z_coords)):
            for iy in range(len(y_coords)):
                for ix in range(len(x_coords) - 1):
        
                    p1 = point_tags[(ix, iy, iz)]
                    p2 = point_tags[(ix + 1, iy, iz)]
        
                    gmsh.model.occ.addLine(p1, p2)
        
        
        # --- Beams in Y direction ---
        for iz in range(1, len(z_coords)):
            for ix in range(len(x_coords)):
                for iy in range(len(y_coords) - 1):
        
                    p1 = point_tags[(ix, iy, iz)]
                    p2 = point_tags[(ix, iy + 1, iz)]
        
                    gmsh.model.occ.addLine(p1, p2)
        
        # --- Synchronize geometry ---
        gmsh.model.occ.synchronize()
        
        # --- Generate mesh (1D for frame) ---
        gmsh.model.mesh.generate(1)
        
        # --- Write mesh ---
        gmsh.write(msh_path)
        
        # --- Convert to VTU ---
        mesh = meshio.read(msh_path)
        mesh.cell_sets = {}
        meshio.write(vtu_path, mesh)
    
        # z_tol = 1e-6
    
        # # Base surfaces
        # base_surfs = gmsh.model.getEntitiesInBoundingBox(
        #     0.0, 0.0, -z_tol,
        #     Lx,  Ly,  z_tol,
        #     2
        # )
        # if base_surfs:
        #     base_tags = [tag for dim, tag in base_surfs]
        #     gmsh.model.addPhysicalGroup(2, base_tags, 1)
        #     gmsh.model.setPhysicalName(2, 1, "Base")
    
        # # Building volume
        # vols = gmsh.model.getEntities(3)
        # if vols:
        #     vol_tags = [tag for dim, tag in vols]
        #     gmsh.model.addPhysicalGroup(3, vol_tags, 2)
        #     gmsh.model.setPhysicalName(3, 2, "Building")
    
        # # Floor surfaces at each story level
        # floor_z = 0.0
        # for i, h in enumerate(story_heights, start=1):
        #     z_low  = floor_z - z_tol
        #     z_high = floor_z + z_tol
        #     fl_surfs = gmsh.model.getEntitiesInBoundingBox(
        #         0.0, 0.0, z_low,
        #         Lx,  Ly, z_high,
        #         2
        #     )
        #     if fl_surfs:
        #         group_id = 10 + i
        #         tags = [tag for dim, tag in fl_surfs]
        #         gmsh.model.addPhysicalGroup(2, tags, group_id)
        #         gmsh.model.setPhysicalName(2, group_id, f"Floor_{i}")
        #     floor_z += h
    
        # gmsh.model.mesh.generate(3)
        # gmsh.write(msh_path)
            
        # mesh = meshio.read(msh_path)
        # meshio.write(vtu_path, mesh)
    finally:     
        gmsh.finalize()
    
        print(f"Written {msh_path} and {vtu_path}")