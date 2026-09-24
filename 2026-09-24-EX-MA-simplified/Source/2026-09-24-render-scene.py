#!/usr/bin/env python3
"""Review-render scene from the real geometry (exported STLs, wood panels, hardware, modelled
rope and sleeve paths). Writes data.js for 2026-09-24-review-viewer.html.

Usage: <cadenv>/bin/python 2026-09-24-render-scene.py <out/data.js> [view-set]
view-set: 'b5' (control box + pedestal previews).
"""
import base64
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, HERE / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


asm = _load("asm", "2026-09-24-assembly.py")
bx = _load("bx", "2026-09-24-build-box.py")
ex = asm.ex

COL = dict(printed="#f08a24", box="#c89a5c", ply="#dcc08e", steel="#9aa3ab", copper="#b87333", pvc="#e9ecef",
           pex="#f4f4f4", dowel="#a8743f", knob="#20262e", ptfe="#ffffff", exma="#3d4a57", base="#2b2f35",
           boom="#2e9e44", stick="#2a6fdb", bucket="#d93a2b", slew="#8e44ad")
PART_GROUP = {
    "lever-hub-boom": "box_mech", "lever-hub-stick": "box_mech", "lever-hub-bucket": "box_mech",
    "slew-spool": "box_mech", "slew-wheel": "box_ctrl", "spool-riser": "box_mech",
    "slew-tube-post@A": "box_mech", "slew-tube-post@B": "box_mech", "conduit-end-fitting-box": "box_mech",
    "slew-drum": "ped_mech", "conduit-end-fitting-pedestal": "ped_mech", "slew-tube-bushing": "ped_mech",
    "elbow-support": "ped_mech", "base": "arm", "slewing-ring-retaining-ring": "arm", "tower": "arm",
}


def t3(p):
    return [round(float(p[0]), 3), round(float(p[2]), 3), round(float(-p[1]), 3)]


def rec(mesh, name, color, group, clip=True):
    tri = mesh.vertices[mesh.faces].reshape(-1, 3)
    arr = np.column_stack((tri[:, 0], tri[:, 2], -tri[:, 1])).astype(np.float32)
    return dict(name=name, color=color, group=group, clip=clip, b64=base64.b64encode(arr.tobytes()).decode())


def meshes():
    out = []
    for n, g in PART_GROUP.items():
        col = COL["printed"] if g != "arm" else (COL["base"] if n != "tower" else COL["exma"])
        out.append(rec(asm.part(n), n, col, g))
    wood_group = {"control-box": "box_wood", "pedestal": "ped_wood", "sandbox": "sandbox"}
    for p in bx.panels():
        m = ex.shape_to_mesh(bx.panel_solid(p).val(), tol=0.2)
        g = wood_group[p.group]
        if p.name.startswith("box top"):
            g = "box_top"
        elif p.name == "box left side":
            g = "box_left"
        elif p.name == "box rear":
            g = "box_rear"
        elif p.name in ("pedestal wall +v", "pedestal wall +u (removable access)"):
            g = "ped_near"
        elif p.name in ("sandbox wall +v", "sandbox wall -v", "sandbox wall +u"):
            g = "sandbox_near"
        out.append(rec(m, p.name, COL["box"] if p.group == "control-box" else COL["ply"], g))
    for n, (m, c) in bx.hardware().items():
        col = dict(steel=COL["steel"], dowel=COL["dowel"], pvc=COL["pvc"], copper=COL["copper"], pex=COL["pex"])[c]
        g = ("box_ctrl" if "handle" in n else "conduit" if "conduit" in n
             else "ped_hw" if ("PEX" in n or "copper" in n) else "hardware")
        out.append(rec(m, n, col, g))
    return out


def strands():
    S = []
    for j in ex.LEVERS:
        for s in bx.lever_strands(j, 0.0):
            S.append(dict(circuit=j, color=COL[j], pts=[t3(s["tangent"]), t3(s["hole"])], name=s["name"]))
    for lane in "AB":
        fb, fp = bx.slew_rope_free(lane)
        S.append(dict(circuit="slew", color=COL["slew"], pts=[t3(p) for p in fb], name=f"slew {lane} box"))
        S.append(dict(circuit="slew", color=COL["slew"], pts=[t3(p) for p in fp], name=f"slew {lane} pedestal"))
        sl = bx.slew_sleeve(lane)
        S.append(dict(circuit="slew", color=COL["slew"], pts=[t3(p) for p in sl["poly"]], name=f"slew {lane} in sleeve"))
    return S


def proxies():
    P = []
    for lane in "AB":
        sl = bx.slew_sleeve(lane)
        P.append(dict(type="path", pts=[t3(p) for p in sl["poly"]], r=ex.PTFE_OD / 2, color=COL["ptfe"],
                      group="sleeves", name=f"slew PTFE sleeve {lane}", opacity=0.45))
    return P


def views_b5():
    z1 = ex.BOX_Z[1]
    hub = lambda j: (ex.AXLE_U, ex.LEVERS[j][1], ex.AXLE_Z)
    V = {}
    V["b5-control-box"] = dict(
        title="B5 — Control box, conduit and pedestal (real CAD geometry)",
        hide=["sandbox_near"], cut=[], ghost={"sandbox": 0.28},
        cam=dict(pos=t3((-1050, 720, 480)), target=t3((-200, -40, -80)), fov=33),
        labels=[("boom lever", (ex.AXLE_U, 70, ex.AXLE_Z + ex.HANDLE_LEN + 14), -130, 10),
                ("stick lever", (ex.AXLE_U, 0, ex.AXLE_Z + ex.HANDLE_LEN + 14), -40, -90),
                ("bucket lever", (ex.AXLE_U, -70, ex.AXLE_Z + ex.HANDLE_LEN + 14), 40, -90),
                ("slew wheel", (ex.WHEEL_C[0] + 60, ex.WHEEL_C[1] - 60, 62), 90, 30),
                ("lever slots = hard stops", (ex.AXLE_U - 60, 0, z1), -230, 60),
                ("wooden pedestal inside the sandbox", (0, 90, -120), 150, 60),
                ("base + printed slewing ring", (0, 70, 20), 140, -60)])
    V["b5-control-box-cutaway"] = dict(
        title="B5 — Control box cutaway: lever hubs, spool, sleeves and ropes to the conduit fitting",
        hide=["box_top", "box_left", "box_rear", "sandbox", "sandbox_near", "ped_wood", "ped_near", "ped_mech",
              "arm", "ped_hw", "conduit"], cut=[], ghost={"box_ctrl": 0.35},
        cam=dict(pos=t3((-700, 430, 210)), target=t3((-320, -60, -110)), fov=34),
        labels=[("boom lever hub (drag clamp in the handle block)", (ex.AXLE_U, ex.LEVERS["boom"][1], ex.AXLE_Z - 30), -330, 60),
                ("stick lever hub", (ex.AXLE_U, ex.LEVERS["stick"][1], ex.AXLE_Z - 30), -60, 220),
                ("bucket lever hub", (ex.AXLE_U, ex.LEVERS["bucket"][1], ex.AXLE_Z - 30), 60, 200),
                ("5/16in lever axle + bearing blocks", (ex.AXLE_U, 86, ex.AXLE_Z), -60, 190),
                ("slew spool (two lanes)", (ex.WHEEL_C[0], ex.WHEEL_C[1] - 55, ex.Z_SLEW_LAYER), 80, 60),
                ("slew sleeve posts", (*ex.spool_departures()["A"]["post"], ex.Z_SLEW_LAYER), -60, 150),
                ("box conduit fitting (PTFE anchors)", (ex.BOX_U[1] - ex.T_WOOD - 13, ex.MOUTH_V + 30, ex.COND_Z + 20), 60, -150),
                ("spool riser", (ex.WHEEL_C[0], ex.WHEEL_C[1] - 14, -150), 90, 60)])
    V["b5-pedestal-cutaway"] = dict(
        title="B5 — Pedestal cutaway: slew drum, PEX bushing shelf, copper elbow and fitting",
        hide=["ped_near", "sandbox_near", "box_top", "box_left", "box_rear", "box_wood", "box_mech", "box_ctrl"],
        cut=["sandbox"], ghost={}, cutplane=dict(n=[0, 0, -1], d=0.0),
        cam=dict(pos=t3((180, 520, -30)), target=t3((-40, 0, -85)), fov=34),
        labels=[("slew drum (two lanes, crimp pockets)", (40, 30, ex.Z_SLEW_LAYER), 110, 40),
                ("shelf + PEX bushing", (40, 40, -57), 140, -60),
                ("3/4in PEX turret tube", (0, 12, -20), 120, -120),
                ("1/2in copper elbow", (-30, 8, ex.Z_ARM_LAYER + 10), -150, 90),
                ("elbow support", (bx.SHELF_U0 + 20, 0, -165), -160, 40),
                ("pedestal fitting: angled slew counterbores", (ex.PED_U[0] + ex.T_WOOD + ex.FIT_T, 30, ex.COND_Z + 22), 140, 60),
                ("printed slewing ring", (60, 40, 20), 110, -40)])
    for k, v in V.items():
        v["labels"] = [dict(text=a, at=t3(b), dx=c, dy=d) for a, b, c, d in v["labels"]]
    return V


def main():
    out = sys.argv[1]
    V = views_b5()
    legend = [["boom rope", COL["boom"]], ["stick rope", COL["stick"]], ["bucket rope", COL["bucket"]],
              ["slew rope", COL["slew"]], ["printed part", COL["printed"]], ["plywood", COL["box"]]]
    scene = dict(proxies=proxies(), strands=strands(), cable_r=1.4, views=V, legend=legend,
                 tag="CAD — B5 PREVIEW",
                 foot="Real geometry: exported printed-part STLs, wood panels and hardware from the build scripts; "
                      "ropes and sleeves are the modelled paths (drawn at 1.75× rope diameter).")
    with open(out, "w") as f:
        f.write("window.MESHES=" + json.dumps(meshes()) + ";\n")
        f.write("window.SCENE=" + json.dumps(scene) + ";\n")
    print("views:", " ".join(V))


if __name__ == "__main__":
    main()
