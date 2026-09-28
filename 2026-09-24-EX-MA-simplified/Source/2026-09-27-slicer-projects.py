#!/usr/bin/env python3
"""EX-MA slicer project files: every print, grouped onto named plates, for Bambu Studio and OrcaSlicer.

Run:  <cadenv>/bin/python 2026-09-27-slicer-projects.py [--bbs-profiles DIR] [--orca-profiles DIR]
      (package.py also calls write_projects() so the BOM and the checklist follow the same plates)
Writes (3MF/):
  2026-09-27-bambu-arm-shell-petg.3mf      2026-09-27-bambu-other-parts-plaplus.3mf
  2026-09-27-orca-arm-shell-petg.3mf       2026-09-27-orca-other-parts-plaplus.3mf

File layout copies what the slicers write themselves (read from their source, Format/bbs_3mf.cpp):
meshes in 3D/Objects/*.model referenced as components, plates in Metadata/model_settings.config and
the printer / process / filament settings in Metadata/project_settings.config. Both slicers only keep
the plates when that settings file is present, and they rebuild each plate's object list from where
the objects sit, so plate k's parts are placed on its bed at (col * 1.2 * 256, -row * 1.2 * 256).

Settings: the user's own A1 setup from References/EX-MA Colored.3mf (printer preset "A1 0.6 Fast
Start", process "0.30mm Strength @BBL A1 0.6 nozzle", 4 walls), with the filament taken from each
slicer's own profile library (Generic PETG @BBL A1 / SUNLU PLA+ 2.0 @BBL A1). The resolved settings are
cached in Source/2026-09-27-slicer-settings/, so re-runs need no profile checkout.
"""
import copy
import json
import math
import sys
import zipfile
from pathlib import Path

import numpy as np
from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
TMF = OUT / "3MF"
CACHE = HERE / "2026-09-27-slicer-settings"
TEMPLATE_3MF = OUT.parent / "References" / "EX-MA Colored.3mf"

BED, MARGIN, GAP, MAX_Z = 256.0, 5.0, 6.0, 250.0
STRIDE = BED * (1.0 + 1.0 / 5.0)                 # PartPlate.cpp: LOGICAL_PART_PLATE_GAP = 1/5
ROT_STEP, GRID = 15, 2.0

GROUPS = {
    "Arm shell": ["boom-half-left", "boom-half-right", "stick-half-left", "stick-half-right"],
    "Arm mechanism + bucket": ["boom-drum", "stick-drum", "bucket-drum-axle", "bucket", "bucket-ear-left",
                               "bucket-ear-right"],
    "Turret + slewing ring": ["tower", "base", "slewing-ring-retaining-ring"],
    "Pedestal": ["slew-drum", "slew-tube-bushing", "elbow-support", "conduit-end-fitting-pedestal"],
    "Control box": ["lever-hub-boom", "lever-hub-stick", "lever-hub-bucket", "lever-knob", "slew-spool",
                    "spool-riser", "slew-tube-post", "slew-wheel", "conduit-end-fitting-box"],
}
# two projects; plates follow the build order (pedestal, box, turret, arm)
PROJECTS = {
    "arm-shell-petg": dict(groups=["Arm shell"], filament="Generic PETG @BBL A1", colour="#F4EE2A",
                           material="PETG"),
    "other-parts-plaplus": dict(groups=["Pedestal", "Control box", "Turret + slewing ring", "Arm mechanism + bucket"],
                                filament="SUNLU PLA+ 2.0 @BBL A1", colour="#000000", material="PLA+",
                                overrides=dict(
                                    # the 22 mm3/s flow cap held every 0.3 x 0.62 mm line to ~118 mm/s; 28 at 230 C
                                    # lifts that to ~150 mm/s; outer wall, top surface and first layer unchanged
                                    process=dict(inner_wall_speed=["200"], sparse_infill_speed=["200"],
                                                 internal_solid_infill_speed=["200"], support_speed=["200"],
                                                 gap_infill_speed=["80"], default_acceleration=["10000"]),
                                    filament=dict(filament_max_volumetric_speed=["28"], nozzle_temperature=["230"]))),
}
# 40 % infill: drums, hubs, clamps and anything carrying a pin; the rest keeps the process's 25 %
LOAD_PARTS = {"boom-drum", "stick-drum", "bucket-drum-axle", "slew-drum", "lever-hub-boom", "lever-hub-stick",
              "lever-hub-bucket", "slew-spool", "slew-wheel", "slewing-ring-retaining-ring", "tower", "base",
              "bucket", "bucket-ear-left", "bucket-ear-right", "boom-half-left", "boom-half-right",
              "stick-half-left", "stick-half-right"}
SUPPORT_MM2 = 800.0                              # same line as the BOM's "supports: yes"
REAL_OUTLINE = {"Arm shell"}

SLICERS = {
    "bambu": dict(app="BambuStudio-02.08.02.61", version="02.08.02.61", orca=None),
    "orca": dict(app="BambuStudio-02.08.01.55", version="02.08.01.55", orca="2.5.0-dev"),
}
PROCESS, PRINTER_SYS, PRINTER_USER = "0.30mm Strength @BBL A1 0.6 nozzle", "Bambu Lab A1 0.6 nozzle", "A1 0.6 Fast Start"
PROFILE_META = {"type", "name", "inherits", "from", "instantiation", "setting_id", "filament_id", "description",
                "renamed_from", "compatible_printers", "compatible_printers_condition", "compatible_prints",
                "compatible_prints_condition", "is_custom_defined", "version"}


def group_of(name):
    return next(g for g, names in GROUPS.items() if name in names)


# ---------------------------------------------------------------- settings
def _profile_index(root):
    idx = {}
    for sub in ("machine", "process", "filament"):
        for f in (Path(root) / sub).rglob("*.json"):
            try:
                d = json.loads(f.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(d, dict) and "name" in d:
                idx.setdefault(d["name"], d)
    return idx


def _resolve(idx, name):
    d = idx[name]
    out = _resolve(idx, d["inherits"]) if d.get("inherits") else {}
    out.update(d)
    return out


def project_settings(slicer, project, profiles_root=None):
    """Full project_settings.config for one slicer + filament, cached in CACHE."""
    cache = CACHE / f"2026-09-27-{slicer}-{project}.json"
    cfg = json.loads(cache.read_text()) if profiles_root is None else _base_settings(slicer, project, profiles_root, cache)
    ov = PROJECTS[project].get("overrides", {})
    diff = cfg["different_settings_to_system"]
    for i, kind in enumerate(("process", "filament")):
        cfg.update(ov.get(kind, {}))
        diff[i] = ";".join(sorted(set(filter(None, diff[i].split(";"))) | set(ov.get(kind, {}))))
    return cfg


def _base_settings(slicer, project, profiles_root, cache):
    tmpl = json.loads(zipfile.ZipFile(TEMPLATE_3MF).read("Metadata/project_settings.config"))
    n_old = len(tmpl["filament_colour"])
    cfg = copy.deepcopy(tmpl)
    fil_keys = {k for k, v in tmpl.items() if isinstance(v, list) and len(v) == n_old}
    for k in fil_keys:
        cfg[k] = cfg[k][:1]
    cfg["flush_volumes_matrix"] = ["0"]
    cfg["flush_volumes_vector"] = cfg["flush_volumes_vector"][:2]
    idx = _profile_index(Path(profiles_root) / "BBL")
    spec = PROJECTS[project]
    fil = _resolve(idx, spec["filament"])
    for src in (_resolve(idx, PRINTER_SYS), _resolve(idx, PROCESS), fil):
        for k, v in src.items():
            if k not in PROFILE_META:
                cfg[k] = v
    for k in ("machine_start_gcode", "printer_notes"):         # the user's "Fast Start" printer preset
        cfg[k] = tmpl[k]
    cfg.update(
        name="project_settings", version=SLICERS[slicer]["version"],
        printer_settings_id=PRINTER_USER, print_settings_id=PROCESS, filament_settings_id=[spec["filament"]],
        filament_ids=[fil.get("filament_id", "")], filament_colour=[spec["colour"]], filament_self_index=["1"],
        filament_map=["1"], inherits_group=["", "", PRINTER_SYS],
        different_settings_to_system=["", "", "machine_start_gcode;printer_notes"],
        default_filament_profile=[spec["filament"]], print_compatible_printers=[PRINTER_SYS])
    cfg["from"] = "project"
    for k, v in cfg.items():                                    # every per-filament list now has 1 entry
        if k in fil_keys and isinstance(v, list) and len(v) > 1 and k in fil:
            cfg[k] = v[:1]
    CACHE.mkdir(exist_ok=True)
    cache.write_text(json.dumps(cfg, indent=4, sort_keys=True))
    return cfg


# ---------------------------------------------------------------- nesting
def footprint(mesh, hull=True):
    """Bed outline of a part plus half the gap. Convex hull by default, so no part is placed inside
    another's open spokes or ring; the long arm halves use their real outline (holes filled) so all four
    nest on one bed."""
    tri = mesh.triangles[:, :, :2]
    a, b = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    keep = np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]) > 1e-6
    shape = unary_union([Polygon(t) for t in tri[keep]])
    if hull:
        shape = shape.convex_hull
    else:
        parts = getattr(shape, "geoms", [shape])
        shape = unary_union([Polygon(g.exterior) for g in parts])
    return shape.buffer(GAP / 2, 8).simplify(0.2)


def nest(items):
    """Bottom-left placement of footprints on 256 x 256 beds; items that don't fit start a new bed.
    Returns a list of beds, each a list of (item, rotation deg, placed polygon)."""
    lo, hi = MARGIN, BED - MARGIN

    def fit(it, bed):
        occ = prep(unary_union([p for _, _, p in bed])) if bed else None
        best = None
        for r in range(0, 360, ROT_STEP):
            p = affinity.rotate(it["poly"], r, origin=it["poly"].centroid)
            x0, y0, x1, y1 = p.bounds
            for y in np.arange(lo - y0, hi - y1 + 1e-6, GRID):
                if best is not None and y + y1 > best[0][0]:
                    break
                hit = next((q for x in np.arange(lo - x0, hi - x1 + 1e-6, GRID)
                            for q in [affinity.translate(p, x, y)] if occ is None or not occ.intersects(q)), None)
                if hit is not None:
                    key = (hit.bounds[3], hit.bounds[2])
                    if best is None or key < best[0]:
                        best = (key, r, hit)
                    break
        return best

    beds = []
    for it in sorted(items, key=lambda i: -i["poly"].area):
        for bed in beds:
            best = fit(it, bed)
            if best:
                bed.append((it, best[1], best[2]))
                break
        else:
            best = fit(it, [])
            if best is None:
                raise ValueError(f"{it['inst']} does not fit an empty bed")
            beds.append([(it, best[1], best[2])])
    return beds


def placed_mesh(it, rot, poly):
    """Oriented mesh rotated/translated exactly like its nested footprint."""
    m = it["mesh"].copy()
    c = it["poly"].centroid
    R = np.eye(4)
    a = math.radians(rot)
    R[:2, :2] = [[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]
    T0, T1 = np.eye(4), np.eye(4)
    T0[:2, 3] = (-c.x, -c.y)
    p0 = affinity.rotate(it["poly"], rot, origin=c)
    T1[:2, 3] = (c.x + poly.bounds[0] - p0.bounds[0], c.y + poly.bounds[1] - p0.bounds[1])
    m.apply_transform(T1 @ R @ T0)
    return m


def layout(rows):
    """Plates for both projects: [(project, [dict(name, group, parts=[(inst_name, row, mesh)])])]."""
    by_name = {r["name"]: r for r in rows}
    out = {}
    for proj, spec in PROJECTS.items():
        plates = []
        for g in spec["groups"]:
            items = []
            for n in GROUPS[g]:
                r = by_name[n]
                if "_poly" not in r:
                    r["_poly"] = footprint(r["oriented"], hull=g not in REAL_OUTLINE)
                for k in range(r["qty"]):
                    items.append(dict(row=r, inst=n + (f"-{k + 1}" if r["qty"] > 1 else ""), mesh=r["oriented"],
                                      poly=r["_poly"]))
            beds = nest(items)
            for b, bed in enumerate(beds):
                title = g + (f" ({b + 1}/{len(beds)})" if len(beds) > 1 else "")
                plates.append(dict(name=title, group=g, parts=[(it["inst"], it["row"], placed_mesh(it, rot, poly), poly)
                                                             for it, rot, poly in bed]))
        out[proj] = plates
    return out


# ---------------------------------------------------------------- 3MF writer
def _cols(n):
    v = math.sqrt(n)
    return int(round(v)) + 1 if v > round(v) else int(round(v))


def plate_origin(i, n):
    cols = _cols(n)
    return np.array([(i % cols) * STRIDE, -(i // cols) * STRIDE, 0.0])


def _mesh_xml(oid, sub_uuid, m):
    v = "\n".join(f'     <vertex x="{a:.6f}" y="{b:.6f}" z="{c:.6f}"/>' for a, b, c in m.vertices)
    t = "\n".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
    return (f'  <object id="{oid}" p:UUID="{sub_uuid}" type="model">\n   <mesh>\n    <vertices>\n{v}\n    </vertices>\n'
            f'    <triangles>\n{t}\n    </triangles>\n   </mesh>\n  </object>\n')


HEAD = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n')
REL_3D = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"


def write_project(path, slicer, proj, plates, cfg):
    sl = SLICERS[slicer]
    n = len(plates)
    objs, items, ms_objs, ms_plates, rels = [], [], [], [], []
    files = {}
    k = 0
    for pi, pl in enumerate(plates):
        org = plate_origin(pi, n)
        insts = []
        for inst, row, m, _ in pl["parts"]:
            k += 1
            main_id, sub_id = 2 * k, 2 * k - 1
            ctr = (m.bounds[0] + m.bounds[1]) / 2
            local = m.copy()
            local.apply_translation(-ctr)
            pos = ctr + org
            fn = f"3D/Objects/{inst}_{k}.model"
            files[fn] = (HEAD + ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n'
                         + _mesh_xml(sub_id, f"{k:04x}0000-81cb-4c03-9d28-80fed5dfa1dc", local)
                         + ' </resources>\n <build/>\n</model>\n')
            rels.append(f' <Relationship Target="/{fn}" Id="rel-{k}" Type="{REL_3D}"/>')
            objs.append(f'  <object id="{main_id}" p:UUID="{k:08x}-61cb-4c03-9d28-80fed5dfa1dc" type="model">\n'
                        f'   <components>\n    <component p:path="/{fn}" objectid="{sub_id}" '
                        f'p:UUID="{k:04x}0000-b206-40ff-9872-83e8017abed1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n'
                        f'   </components>\n  </object>\n')
            items.append(f'  <item objectid="{main_id}" p:UUID="{k:08x}-b1ec-4553-aec9-835e5b724bb4" '
                         f'transform="1 0 0 0 1 0 0 0 1 {pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}" printable="1"/>')
            extra = []
            if row["name"] in LOAD_PARTS:
                extra.append(("sparse_infill_density", "40%"))
            if row["support"] >= SUPPORT_MM2:
                extra.append(("enable_support", "1"))
            md = "".join(f'    <metadata key="{a}" value="{b}"/>\n' for a, b in extra)
            ms_objs.append(f'  <object id="{main_id}">\n    <metadata key="name" value="{inst}"/>\n'
                           f'    <metadata key="extruder" value="1"/>\n{md}'
                           f'    <metadata face_count="{len(m.faces)}"/>\n'
                           f'    <part id="{sub_id}" subtype="normal_part">\n'
                           f'      <metadata key="name" value="{inst}"/>\n'
                           f'      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                           f'      <mesh_stat face_count="{len(m.faces)}" edges_fixed="0" degenerate_facets="0" '
                           f'facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n    </part>\n  </object>\n')
            insts.append(f'    <model_instance>\n      <metadata key="object_id" value="{main_id}"/>\n'
                         f'      <metadata key="instance_id" value="0"/>\n'
                         f'      <metadata key="identify_id" value="{1000 + k}"/>\n    </model_instance>\n')
        ms_plates.append(f'  <plate>\n    <metadata key="plater_id" value="{pi + 1}"/>\n'
                         f'    <metadata key="plater_name" value="{pl["name"].replace("&", "&amp;")}"/>\n'
                         f'    <metadata key="locked" value="false"/>\n'
                         f'    <metadata key="filament_map_mode" value="Auto For Flush"/>\n'
                         f'    <metadata key="filament_maps" value="1"/>\n' + "".join(insts) + '  </plate>\n')
    meta = [("Application", sl["app"])] + ([("OrcaSlicer", sl["orca"])] if sl["orca"] else []) + [
        ("BambuStudio:3mfVersion", "1"), ("CreationDate", "2026-09-27"), ("ModificationDate", "2026-09-27"),
        ("Title", f"EX-MA {proj}"), ("Designer", ""), ("Description", ""), ("Copyright", ""), ("License", ""),
        ("Origin", "")]
    files["3D/3dmodel.model"] = (HEAD + "".join(f' <metadata name="{a}">{b}</metadata>\n' for a, b in meta)
                                 + " <resources>\n" + "".join(objs) + " </resources>\n"
                                 + ' <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">\n' + "\n".join(items)
                                 + "\n </build>\n</model>\n")
    files["3D/_rels/3dmodel.model.rels"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships '
                                            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                                            + "\n".join(rels) + "\n</Relationships>\n")
    files["_rels/.rels"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships '
                            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                            f' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="{REL_3D}"/>\n</Relationships>\n')
    files["[Content_Types].xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
        ' <Default Extension="png" ContentType="image/png"/>\n'
        ' <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>\n')
    files["Metadata/model_settings.config"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n' + "".join(ms_objs)
                                               + "".join(ms_plates) + "</config>\n")
    files["Metadata/project_settings.config"] = json.dumps(cfg, indent=4, sort_keys=True) + "\n"
    hdr = f'    <header_item key="X-BBL-Client-Version" value="{sl["version"]}"/>\n'
    if sl["orca"]:
        hdr += f'    <header_item key="OrcaSlicer-Version" value="{sl["orca"]}"/>\n'
    files["Metadata/slice_info.config"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <header>\n'
                                           '    <header_item key="X-BBL-Client-Type" value="slicer"/>\n' + hdr
                                           + "  </header>\n</config>\n")
    files["Metadata/filament_sequence.json"] = json.dumps(
        {f"plate_{i + 1}": {"nozzle_sequence": [], "optimal_assignment": [], "sequence": []} for i in range(n)})
    order = ["[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model", "3D/_rels/3dmodel.model.rels"]
    order += sorted(f for f in files if f.startswith("3D/Objects/")) + sorted(f for f in files if f.startswith("Metadata/"))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in order:
            z.writestr(f, files[f])


# ---------------------------------------------------------------- check
def check_file(path, plates):
    """Re-read the file the way the slicer places objects: each build item's mesh bbox must fall inside
    exactly its own plate's bed (PartPlateList::reload_all_objects), with no footprint overlaps."""
    import xml.etree.ElementTree as ET
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
          "p": "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"}
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("3D/3dmodel.model"))
    comp = {}
    for o in root.find("m:resources", ns):
        c = o.find("m:components/m:component", ns)
        comp[o.get("id")] = c.get("{%s}path" % ns["p"]).lstrip("/")
    ms = ET.fromstring(z.read("Metadata/model_settings.config"))
    names = {o.get("id"): o.find("metadata[@key='name']").get("value") for o in ms.findall("object")}
    plate_of = {}
    for pl in ms.findall("plate"):
        pid = int(pl.find("metadata[@key='plater_id']").get("value"))
        for mi in pl.findall("model_instance"):
            plate_of[mi.find("metadata[@key='object_id']").get("value")] = pid
    n = len(plates)
    found = {i + 1: [] for i in range(n)}
    ok_inside, heights = True, []
    for it in root.find("m:build", ns):
        oid = it.get("objectid")
        t = np.array([float(x) for x in it.get("transform").split()])[9:]
        sub = ET.fromstring(z.read(comp[oid]))
        v = np.array([[float(x.get(a)) for a in "xyz"] for x in sub.iter("{%s}vertex" % ns["m"])]) + t
        lo, hi = v.min(0), v.max(0)
        heights.append(hi[2] - lo[2])
        hits = [i + 1 for i in range(n) if np.all(lo[:2] >= plate_origin(i, n)[:2] - 1e-6)
                and np.all(hi[:2] <= plate_origin(i, n)[:2] + BED + 1e-6)]
        if len(hits) != 1 or hits[0] != plate_of[oid] or abs(lo[2]) > 1e-3:
            ok_inside = False
        found[plate_of[oid]].append(names[oid])
    overlap = any(a.intersects(b) for pl in plates for i, (_, _, _, a) in enumerate(pl["parts"])
                  for (_, _, _, b) in pl["parts"][i + 1:])
    json.loads(z.read("Metadata/project_settings.config"))
    return dict(file=path.name, plates=[dict(plate=i + 1, name=plates[i]["name"], parts=found[i + 1])
                                        for i in range(n)],
                objects=sum(len(v) for v in found.values()), inside_own_plate=ok_inside, footprint_overlap=overlap,
                max_height_mm=round(float(max(heights)), 1), fits_height=bool(max(heights) <= MAX_Z))


def write_projects(rows, profiles=None):
    """Write the 4 project files; returns the check list (for package.py / reports.py)."""
    profiles = profiles or {}
    TMF.mkdir(exist_ok=True)
    lay = layout(rows)
    checks = []
    for slicer in SLICERS:
        for proj, plates in lay.items():
            path = TMF / f"2026-09-27-{'bambu' if slicer == 'bambu' else 'orca'}-{proj}.3mf"
            write_project(path, slicer, proj, plates, project_settings(slicer, proj, profiles.get(slicer)))
            c = check_file(path, plates)
            c.update(slicer=slicer, project=proj, material=PROJECTS[proj]["material"],
                     filament=PROJECTS[proj]["filament"])
            checks.append(c)
    return checks


def _package():
    import importlib.util
    spec = importlib.util.spec_from_file_location("pk", HERE / "2026-09-24-package.py")
    pk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pk)
    return pk


def main():
    a = sys.argv[1:]
    prof = {}
    for flag, key in (("--bbs-profiles", "bambu"), ("--orca-profiles", "orca")):
        if flag in a:
            prof[key] = a[a.index(flag) + 1]
    pk = _package()
    rows = pk.printed_parts()
    for r in rows:
        r["oriented"], r["orient"], r["support"], r["contact"] = pk.orient(r["mesh"], r["name"])
    for c in write_projects(rows, prof):
        print(c["file"], "objects", c["objects"], "inside", c["inside_own_plate"], "overlap", c["footprint_overlap"],
              "max h", c["max_height_mm"])
        for p in c["plates"]:
            print(f"   plate {p['plate']} {p['name']}: {', '.join(p['parts'])}")


if __name__ == "__main__":
    main()
