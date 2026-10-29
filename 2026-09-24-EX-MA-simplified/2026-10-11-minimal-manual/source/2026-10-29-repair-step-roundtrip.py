#!/usr/bin/env python3
"""STEP round-trip repair for the converted arm halves (used for the 2026-10-29 minimal assembly).

Source/2026-09-28-arm-halves-cad.py keeps a half that replays but does not read back from STEP as one
valid solid as <part>.step.failed.brep. Three halves needed this with CadQuery 2.8 / OCCT 7.8:

  stick-half-right   reads back valid; only missed the converter's 1 mm3 volume check (2.6 mm3)
                     -> used as written (export + read back)
  stick-half-left    two faces read back unorientable
                     -> nurbs:  those faces rebuilt as NURBS, solid resewn (twice), reads back valid
  boom-half-left     a 0.01 mm2 cone sliver reads back unorientable
                     -> patch (two passes): drop the flagged face of the read-back solid, close the
                        hole with a filled patch, resew; the second pass replaced a 2 mm2 cone blend

Usage:  python 2026-10-29-repair-step-roundtrip.py nurbs in.brep out.step
        python 2026-10-29-repair-step-roundtrip.py patch in.(brep|step) out.step   (repeat on out)
"""
import sys


def nurbs():
    import sys, cadquery as cq
    from OCP.BRepTools import BRepTools, BRepTools_ReShape
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Shape, TopoDS
    from OCP.BRepCheck import BRepCheck_Analyzer, BRepCheck_NoError
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.ShapeFix import ShapeFix_Shell, ShapeFix_Solid
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SHELL
    inp, out = sys.argv[2], sys.argv[3]
    s=TopoDS_Shape(); BRepTools.Read_s(s,inp,BRep_Builder()); s=cq.Shape.cast(s).Solids()[0]
    v0=s.Volume()
    def rb(x):
        x.exportStep(out); b=cq.importers.importStep(out).solids().vals(); return b[0] if len(b)==1 else None
    def bad(x):
        an=BRepCheck_Analyzer(x.wrapped); r=[]
        for f in x.Faces():
            res=an.Result(f.wrapped)
            if res is not None and any(st!=BRepCheck_NoError for st in res.Status()): r.append(f)
        return r
    def sew(faces, tol=1e-4):
        sw=BRepBuilderAPI_Sewing(tol)
        for f in faces: sw.Add(f)
        sw.Perform(); sh=sw.SewedShape()
        e=TopExp_Explorer(sh,TopAbs_SHELL); shells=[]
        while e.More(): shells.append(TopoDS.Shell_s(e.Current())); e.Next()
        assert len(shells)==1, len(shells)
        fs=ShapeFix_Shell(shells[0]); fs.Perform()
        so=ShapeFix_Solid(BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(fs.Shell())).Solid()); so.Perform()
        return cq.Shape.cast(so.Solid())
    conv=set()
    for it in range(4):
        b=rb(s)
        if b is not None and b.isValid() and abs(b.Volume()-v0) < 1e-3 * v0:
            print(f"OK after {it} rounds: {len(conv)} faces as NURBS, readback dvol {b.Volume()-v0:.2f}, faces {len(b.Faces())}"); sys.exit(0)
        print("  readback:", None if b is None else (b.isValid(), round(b.Volume()-v0,2)))
        bf=bad(b) if b is not None else []
        print(f"round {it}: {len(bf)} bad faces after readback", [(f.geomType(), round(f.Area(),3)) for f in bf])
        targets=[]
        for f in bf:
            c=f.Center(); a=abs(f.Area())
            best=min(s.Faces(), key=lambda g: (g.Center()-c).Length + abs(abs(g.Area())-a))
            targets.append(best)
        faces=[]
        tset={t.wrapped.__hash__() for t in targets}
        for f in s.Faces():
            if any(f.wrapped.IsSame(t.wrapped) for t in targets):
                if abs(f.Area()) < 0.1:                 # sliver: flat patch on its outer wire
                    from OCP.BRepFill import BRepFill_Filling
                    from OCP.GeomAbs import GeomAbs_C0
                    fl=BRepFill_Filling()
                    for e in f.outerWire().Edges(): fl.Add(e.wrapped, GeomAbs_C0, True)
                    fl.Build(); faces.append(fl.Face())
                else:
                    faces.append(BRepBuilderAPI_NurbsConvert(f.wrapped, True).Shape())
                conv.add(round(f.Area(),4))
            else:
                faces.append(f.wrapped)
        s=sew(faces)
        print(f"  resewn: valid {s.isValid()} solids {len(s.Solids())} dvol {s.Volume()-v0:.2f}")
    print("FAILED"); sys.exit(1)


def patch():
    import sys, cadquery as cq
    from OCP.BRepTools import BRepTools
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Shape, TopoDS
    from OCP.BRepCheck import BRepCheck_Analyzer, BRepCheck_NoError
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SHELL, TopAbs_WIRE, TopAbs_EDGE
    from OCP.BRepFill import BRepFill_Filling
    from OCP.GeomAbs import GeomAbs_C0
    from OCP.ShapeFix import ShapeFix_Shell, ShapeFix_Solid, ShapeFix_Shape
    inp, out = sys.argv[2], sys.argv[3]
    if inp.endswith(".brep"):
        s=TopoDS_Shape(); BRepTools.Read_s(s,inp,BRep_Builder()); s=cq.Shape.cast(s).Solids()[0]
        s.exportStep(out); inp=out
    b=cq.importers.importStep(inp).solids().vals()[0]; v0=b.Volume()
    an=BRepCheck_Analyzer(b.wrapped)
    badf=[f for f in b.Faces() if (r:=an.Result(f.wrapped)) is not None and any(st!=BRepCheck_NoError for st in r.Status())]
    print("bad faces", [(f.geomType(), round(f.Area(),4)) for f in badf])
    keep=[f for f in b.Faces() if not any(f.wrapped.IsSame(g.wrapped) for g in badf)]
    def sew(faces, tol):
        sw=BRepBuilderAPI_Sewing(tol)
        for f in faces: sw.Add(f)
        sw.Perform(); return sw.SewedShape()
    sh=sew([f.wrapped for f in keep], 1e-3)
    fb=ShapeAnalysis_FreeBounds(sh, 1e-3, False, False)
    closed=fb.GetClosedWires()
    e=TopExp_Explorer(closed, TopAbs_WIRE); patches=[]
    while e.More():
        w=TopoDS.Wire_s(e.Current()); fl=BRepFill_Filling()
        ee=TopExp_Explorer(w, TopAbs_EDGE)
        while ee.More(): fl.Add(TopoDS.Edge_s(ee.Current()), GeomAbs_C0, True); ee.Next()
        fl.Build(); patches.append(fl.Face()); e.Next()
    print("holes patched", len(patches))
    sh=sew([f.wrapped for f in keep]+patches, 1e-3)
    e=TopExp_Explorer(sh, TopAbs_SHELL); shells=[]
    while e.More(): shells.append(TopoDS.Shell_s(e.Current())); e.Next()
    print("shells", len(shells))
    fs=ShapeFix_Shell(shells[0]); fs.Perform()
    so=ShapeFix_Solid(BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(fs.Shell())).Solid()); so.Perform()
    x=cq.Shape.cast(so.Solid()); fx=ShapeFix_Shape(x.wrapped); fx.Perform(); x=cq.Shape.cast(fx.Shape()).Solids()[0]
    print("patched: valid", x.isValid(), "dvol %.3f" % (x.Volume()-v0), "faces", len(x.Faces()))
    x.exportStep(out); r=cq.importers.importStep(out).solids().vals()
    print("readback: solids", len(r), "valid", r[0].isValid(), "dvol %.3f" % (r[0].Volume()-v0))
    sys.exit(0 if len(r)==1 and r[0].isValid() else 1)


if __name__ == "__main__":
    {"nurbs": nurbs, "patch": patch}[sys.argv[1]]()
