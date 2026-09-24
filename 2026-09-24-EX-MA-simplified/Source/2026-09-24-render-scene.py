#!/usr/bin/env python3
"""Review-render scene from the real geometry (exported STLs, wood panels, hardware, modelled
rope and sleeve paths). Writes data.js for 2026-09-24-review-viewer.html.

Usage: <cadenv>/bin/python 2026-09-24-render-scene.py <out/data.js> [view-set]
view-set: 'b5' (control box + pedestal previews) or 'b7' (final review views 1-7, default).
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


ARM_PARTS = {   # b7: arm-side parts -> (group, colour)
    "boom-drum": ("arm_mech", "printed"), "stick-drum": ("arm_mech", "printed"), "bucket-drum-axle": ("arm_mech", "printed"),
    "boom-half-right": ("arm", "yellow"), "boom-half-left": ("arm_near", "yellow"),
    "stick-half-right": ("arm", "yellow"), "stick-half-left": ("arm_near", "yellow"),
    "bucket": ("arm", "base"), "bucket-ear-right": ("arm", "ear"), "bucket-ear-left": ("arm_near", "ear"),
}
COL.update(yellow="#e5b319", ear="#2f6db5")


def meshes_b7():
    """Everything in meshes() plus the arm; the turret and base get their own groups."""
    import trimesh
    out = [m for m in meshes() if m["name"] not in ("base", "slewing-ring-retaining-ring", "tower")]
    for m in out:
        if m["name"] == "slew-wheel":
            m["group"] = "box_wheel"      # b7: the wheel stays visible when the lever handles are cut away
    out.append(rec(asm.part("tower"), "tower", COL["exma"], "turret"))
    out.append(rec(asm.part("base"), "base", COL["base"], "base"))
    out.append(rec(asm.part("slewing-ring-retaining-ring"), "retaining ring", COL["printed"], "base"))
    for n, (g, c) in ARM_PARTS.items():
        out.append(rec(asm.part(n), n, COL[c], g))
    out.append(rec(asm.split_pins("boom"), "boom split pins", COL["steel"], "arm_hw"))
    out.append(rec(asm.split_pins("stick"), "stick split pins", COL["steel"], "arm_hw"))
    a, b = (ex.P_BUCKET[0], -32.0, ex.P_BUCKET[1]), (ex.P_BUCKET[0], 32.0, ex.P_BUCKET[1])
    out.append(rec(trimesh.creation.cylinder(radius=ex.PIN_D / 2, segment=np.array([a, b]), sections=24),
                   "bucket pin", COL["steel"], "arm_hw"))
    n_b = int(2 * math.pi * ex.BALL_CIRCLE_R // (ex.BALL_D + 0.4))
    balls = []
    for k in range(n_b):
        t = 2 * math.pi * k / n_b
        s_ = trimesh.creation.icosphere(subdivisions=1, radius=ex.BALL_D / 2)
        s_.apply_translation((ex.BALL_CIRCLE_R * math.cos(t), ex.BALL_CIRCLE_R * math.sin(t), ex.BALL_Z))
        balls.append(s_)
    out.append(rec(trimesh.util.concatenate(balls), "6 mm BBs", "#f4f4f4", "base"))
    return out


def strands_b7():
    cp = _load("cp", "2026-09-24-cable-paths.py")
    P = cp.all_paths()
    S = [dict(circuit=e["circuit"], color=COL[e["circuit"]], pts=[t3(q) for q in cp.polyline(e)], name=n) for n, e in P.items()]
    X = [dict(type="path", pts=[t3(q) for q in seg], r=ex.PTFE_OD / 2, color=COL["ptfe"], group="ptfe",
              name=f"PTFE {n}", opacity=0.35) for n, e in P.items() for seg in e["ptfe"]]
    return S, X


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


def views_b7():
    L = lambda text, at, dx, dy: (text, at, dx, dy)
    PB, PS, PK = ex.P_BOOM, ex.P_STICK, ex.P_BUCKET
    hub = lambda j: (ex.AXLE_U, ex.LEVERS[j][1], ex.AXLE_Z)
    keep_minus_v = dict(n=[0, 0, 1], d=0.0)          # clip away +v (camera on the +v side)
    V = {}
    V["view1-complete-excavator"] = dict(
        title="View 1 — Complete excavator: control box with 3 levers + slew wheel, pedestal, base, arm and bucket",
        hide=["sandbox_near"], cut=[], ghost={"sandbox": 0.25},
        cam=dict(pos=t3((-1000, 820, 620)), target=t3((-60, -30, 20)), fov=38),
        labels=[L("boom lever", (ex.AXLE_U, 70, ex.AXLE_Z + ex.HANDLE_LEN + 16), -120, 90),
                L("stick lever", (ex.AXLE_U, 0, ex.AXLE_Z + ex.HANDLE_LEN + 16), -60, -80),
                L("bucket lever", (ex.AXLE_U, -70, ex.AXLE_Z + ex.HANDLE_LEN + 16), 40, -90),
                L("slew wheel", (ex.WHEEL_C[0] + 60, ex.WHEEL_C[1] - 60, 62), 80, 50),
                L("boom", (100, -24, 140), 130, -90), L("stick", (260, -17, 150), -40, -130),
                L("bucket", (340, -27, 70), 90, 40), L("printed slewing ring on the base", (-45, 45, 22), -330, 40)])
    V["view2-full-system-cutaway"] = dict(
        title="View 2 — Full system cutaway: every rope from its control to its joint (modelled paths)",
        hide=["sandbox_near", "box_top", "box_left", "ped_near", "arm_near"],
        cut=["turret", "base", "conduit", "ped_hw", "sandbox", "ped_wood", "box_wood", "box_rear"],
        cutplane=keep_minus_v, ghost={"sandbox": 0.2, "box_ctrl": 0.5, "box_wheel": 0.5},
        cam=dict(pos=t3((-60, 1250, 380)), target=t3((-70, 0, -20)), fov=34),
        labels=[L("lever drums", hub("stick"), 200, 130), L("slew spool", (ex.WHEEL_C[0], ex.WHEEL_C[1], ex.Z_SLEW_LAYER), 260, -60),
                L("conduit", (-150, -20, ex.COND_Z), 0, 190), L("pedestal slew drum", (0, -55, ex.Z_SLEW_LAYER), -260, 150),
                L("copper elbow → PEX turret tube", (0, 0, -60), -380, 20),
                L("boom drum", (PB[0], 0, PB[1]), 160, -140), L("stick drum", (PS[0], 0, PS[1]), 40, -120),
                L("bucket drum-axle", (PK[0], 0, PK[1]), 90, 40)])
    V["view3-control-box-cutaway"] = dict(
        title="View 3 — Control box cutaway: lever pivots, drums, axle, rope anchors, slew spool, sleeves, rope exits",
        hide=["box_top", "box_left", "box_rear", "sandbox", "sandbox_near", "ped_wood", "ped_near", "ped_mech",
              "turret", "base", "arm", "arm_near", "arm_mech", "arm_hw", "ped_hw", "conduit"], cut=[],
        ghost={"box_ctrl": 0.35, "box_wheel": 0.35},
        cam=dict(pos=t3((-700, 430, 210)), target=t3((-320, -60, -110)), fov=34),
        labels=[L("boom lever hub + drag clamp", (ex.AXLE_U, ex.LEVERS["boom"][1], ex.AXLE_Z - 30), -330, 60),
                L("stick lever hub", (ex.AXLE_U, ex.LEVERS["stick"][1], ex.AXLE_Z - 30), -60, 220),
                L("bucket lever hub", (ex.AXLE_U, ex.LEVERS["bucket"][1], ex.AXLE_Z - 30), 60, 200),
                L("5/16in lever axle + bearing blocks", (ex.AXLE_U, 86, ex.AXLE_Z), -60, 190),
                L("slew spool on its axle", (ex.WHEEL_C[0], ex.WHEEL_C[1] - 55, ex.Z_SLEW_LAYER), 80, 60),
                L("PTFE sleeves from the posts", (*ex.spool_departures()["A"]["post"], ex.Z_SLEW_LAYER), -60, -240),
                L("rope exits: box conduit fitting", (ex.BOX_U[1] - ex.T_WOOD - 13, ex.MOUTH_V + 30, ex.COND_Z + 20), 60, -150)])
    V["view4-boom-joint"] = dict(
        title="View 4 — Boom joint: boom drum on split pins, boom ropes from the turret tube, PTFE tubes across the axis",
        hide=["arm_near", "sandbox", "sandbox_near", "box_top", "box_left"], cut=["turret", "base"], cutplane=keep_minus_v,
        ghost={"arm": 0.45},
        cam=dict(pos=t3((60, 330, 150)), target=t3((20, 0, 80)), fov=34),
        labels=[L("boom drum (crimp pocket on top)", (PB[0], 0, PB[1] + 16), 90, -120),
                L("split pins, one per side (inner ends flush with the boom walls)", (PB[0], sum(asm.SPLIT_PIN_V["boom"]) / 2, PB[1]), -300, -90),
                L("boom ropes (green)", (8, 0, 60), 120, 40), L("stick + bucket PTFE tubes", (0, 10, 55), -230, 60),
                L("PEX turret tube top", (0, 0, 22), 230, 70), L("printed slewing ring", (55, -20, 20), -260, 20)])
    V["view5-stick-joint"] = dict(
        title="View 5 — Stick joint: stick drum, stick ropes from their tube stops, bucket tubes across the axis",
        hide=["arm_near", "sandbox", "sandbox_near"], cut=[], ghost={"arm": 0.4},
        cam=dict(pos=t3((215, 300, 250)), target=t3((175, 0, 180)), fov=34),
        labels=[L("stick drum", (PS[0], 0, PS[1] + 14), -120, -110), L("stick tube stops (bulkhead)", (160, 0, 172), 200, 20),
                L("stick ropes (blue)", (167, 0, 184), 150, -190), L("bucket tubes cross the stick axis", (185, 8, 175), -250, 130),
                L("split pins", (PS[0], sum(asm.SPLIT_PIN_V["stick"]) / 2, PS[1]), -300, -20)])
    V["view6-bucket-joint"] = dict(
        title="View 6 — Bucket joint: bucket drum-axle (hex ends in the ears), bucket ropes from their stops in the stick",
        hide=["arm_near", "sandbox", "sandbox_near"], cut=[], ghost={"arm": 0.4},
        cam=dict(pos=t3((380, 280, 170)), target=t3((330, 0, 115)), fov=34),
        labels=[L("bucket drum-axle", (PK[0], 0, PK[1] + 9), -200, -70), L("bucket tube stops", (305, 0, 128), 60, -170),
                L("bucket ropes (red)", (330, 0, 118), -200, 90), L("bucket ear (hex socket)", (PK[0], -20, PK[1] - 20), 150, 60)])
    zc = ex.Z_SLEW_LAYER + 14                         # horizontal cut just above the slew-rope layer
    V["view7-slew-detail"] = dict(
        title="View 7 — Slew: wheel → spool → ropes in PTFE sleeves → conduit → pedestal fitting → slew drum → PEX tube → turret",
        hide=["box_top"], cut=["conduit", "sandbox", "sandbox_near", "box_wood", "box_left", "box_rear", "box_ctrl",
                               "ped_wood", "ped_near", "ped_hw"],
        cutplane=dict(n=[0, -1, 0], d=zc), ghost={"sandbox": 0.3, "sandbox_near": 0.3, "arm": 0.3, "arm_near": 0.3, "conduit": 0.3},
        cam=dict(pos=t3((-120, 560, 520)), target=t3((-170, -80, -90)), fov=40),
        labels=[L("slew wheel (1:1)", (ex.WHEEL_C[0] + 80, ex.WHEEL_C[1], 62), -40, -110),
                L("slew spool (two lanes)", (ex.WHEEL_C[0] + 55, ex.WHEEL_C[1], ex.Z_SLEW_LAYER), 160, 70),
                L("ropes in PTFE sleeves", (-270, -95, ex.Z_SLEW_LAYER), -40, -190),
                L("2in conduit (ghosted)", (-160, ex.MOUTH_V, ex.COND_Z), 150, 210),
                L("pedestal fitting (angled exits)", (ex.PED_U[0] + ex.T_WOOD + ex.FIT_T / 2, ex.MOUTH_V + 20, ex.Z_SLEW_LAYER), -80, 250),
                L("slew drum on the PEX turret tube", (0, 55, ex.Z_SLEW_LAYER), -300, 110),
                L("turret on the printed slewing ring", (0, 60, 25), 180, -60)])
    for k, v in V.items():
        v["labels"] = [dict(text=a, at=t3(b), dx=c, dy=d) for a, b, c, d in v["labels"]]
    return V


def main():
    out = sys.argv[1]
    vset = sys.argv[2] if len(sys.argv) > 2 else "b7"
    if vset == "b7":
        V = views_b7()
        S, X = strands_b7()
        legend = [["boom rope", COL["boom"]], ["stick rope", COL["stick"]], ["bucket rope", COL["bucket"]],
                  ["slew rope", COL["slew"]], ["PTFE tube (translucent)", "#d9dde2"], ["printed part", COL["printed"]],
                  ["plywood", COL["box"]]]
        scene = dict(proxies=X, strands=S, cable_r=1.2, views=V, legend=legend, tag="CAD — FINAL REVIEW",
                     foot="Rendered from the exported parts, wood panels and hardware; every coloured rope is the continuous "
                          "modelled path from 2026-09-24-cable-paths.py (built pose, joints at 0°), drawn at 1.5× rope diameter.")
        with open(out, "w") as f:
            f.write("window.MESHES=" + json.dumps(meshes_b7()) + ";\n")
            f.write("window.SCENE=" + json.dumps(scene) + ";\n")
        print("views:", " ".join(V))
        return
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
