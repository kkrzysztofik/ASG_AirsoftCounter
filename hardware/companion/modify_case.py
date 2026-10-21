# /// script
# dependencies = ["trimesh","numpy","lxml","scipy","networkx","rtree","manifold3d","shapely"]
# ///
"""Modify the mesh-only Heltec V4 companion case 3MF:
- antenna side: stretch the left wall outward and bore the bay for a 12.5 mm antenna base;
- key switch: lengthen the antenna end and cut a double-D hole in the front plate.
usage: modify_case.py IN.3mf OUT.3mf"""
import re, sys, zipfile, numpy as np, trimesh, manifold3d as mf
from lxml import etree
from shapely.geometry import Point, Polygon

# Measured from the original mesh, FK frame.
AXIS_X, AXIS_Z = -22.51, -2.14   # SMA hole centre
WALL_FACE_Y = 2.06               # bulkhead wall face, antenna side
BK_DZ = -2.14 - 6.0              # BK rim (z=6) meets FK parting plane (z=-2.14)
OUTER_X = -29.71                 # original left outer face

# Antenna bay.
BORE = 13.5                      # 12.5 antenna base + 0.5/side FDM clearance
STRETCH_X = 1.6                  # left wall grows by this much
SPLIT_X = -28.2                  # cuts only outer skin: left of the bay (-27.7), screw boss (-23.7), nut pocket (-27.1)

NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
PARTS = {'3D/Objects/object_1.model': (0.0, True), '3D/Objects/object_7.model': (BK_DZ, False)}  # FK, BK

def parse(data):
    t = etree.fromstring(data)
    v = np.array([[float(x.get(a)) for a in 'xyz'] for x in t.iterfind('.//m:vertex', NS)])
    f = np.array([[int(x.get(a)) for a in ('v1', 'v2', 'v3')] for x in t.iterfind('.//m:triangle', NS)])
    return t, trimesh.Trimesh(v, f, process=True)

def write_mesh(t, m):
    mesh = t.find('.//m:mesh', NS)
    for child in list(mesh): mesh.remove(child)
    vs = etree.SubElement(mesh, f'{{{NS["m"]}}}vertices')
    for x, y, z in m.vertices: etree.SubElement(vs, f'{{{NS["m"]}}}vertex', x=f'{x:.6g}', y=f'{y:.6g}', z=f'{z:.6g}')
    ts = etree.SubElement(mesh, f'{{{NS["m"]}}}triangles')
    for a, b, c in m.faces: etree.SubElement(ts, f'{{{NS["m"]}}}triangle', v1=str(a), v2=str(b), v3=str(c))
    return etree.tostring(t, xml_declaration=True, encoding='UTF-8')

def to_mf(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))

def from_mf(M):
    out = M.to_mesh()
    return trimesh.Trimesh(out.vert_properties[:, :3], out.tri_verts, process=False)

def stretch(M, axis, at, by):
    """Cut at coordinate `at` on `axis`, move the far side (the side `by` points to) by `by`,
    and fill the gap with the cross-section extruded |by|."""
    n, s = np.eye(3)[axis], np.sign(by)
    fixed = M.trim_by_plane(tuple(-s * n), -s * at)
    moving = M.trim_by_plane(tuple(s * n), s * at).translate(tuple(n * by))
    P = np.eye(3)[[(axis + 1) % 3, (axis + 2) % 3, axis]]   # rows: axis becomes z
    sect = M.transform(np.c_[P, np.zeros(3)]).slice(at)
    slab = mf.Manifold.extrude(sect, abs(by) + 0.02).translate((0, 0, min(at, at + by) - 0.01))
    return fixed + slab.transform(np.c_[P.T, np.zeros(3)]) + moving

def bore(dz):
    y0, y1 = WALL_FACE_Y + 0.04, 90.0
    c = trimesh.creation.cylinder(radius=BORE / 2, height=y1 - y0, sections=96)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([AXIS_X, (y0 + y1) / 2, AXIS_Z - dz])
    return to_mf(c)

def modify(m, dz, fk):
    M = to_mf(m)
    assert M.status() == mf.Error.NoError, M.status()
    M = stretch(M, 0, SPLIT_X, -STRETCH_X)
    return M - bore(dz)

def free_dia(meshes, y):
    """Largest circle about the antenna axis that clears both shells at section y (FK frame)."""
    c, best = Point(AXIS_X, AXIS_Z), 99.0
    for m, dz in meshes:
        s = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
        if s is None: continue
        for e in s.discrete:
            pg = Polygon(np.c_[e[:, 0], e[:, 2] + dz]).buffer(0)
            best = min(best, 0.0 if pg.contains(c) else 2 * pg.distance(c))
    return best

zin = zipfile.ZipFile(sys.argv[1]); out = {}; before, after = [], []
for name, (dz, fk) in PARTS.items():
    t, m = parse(zin.read(name))
    assert m.is_watertight, name
    n = from_mf(modify(m, dz, fk))
    print(f'{name}: bodies {m.body_count} -> {n.body_count}, bounds {m.bounds.round(2).tolist()} -> {n.bounds.round(2).tolist()}')
    assert n.is_watertight and n.body_count == 1, f'{name}: broken or split'  # FK's overlapping hood body merges in
    before.append((m, dz)); after.append((n, dz)); out[name] = write_mesh(t, n)

BAY_YS = (3, 5, 10, 20, 30, 36)
for y in (1.5,) + BAY_YS:
    print(f'y={y:4}: antenna free dia {free_dia(before, y):5.2f} -> {free_dia(after, y):5.2f}')
assert all(free_dia(after, y) >= BORE - 0.05 for y in BAY_YS)
assert free_dia(after, 1.5) == 0  # bulkhead wall kept
wall = AXIS_X - BORE / 2 - (OUTER_X - STRETCH_X)
print(f'side wall beside the bore: {wall:.2f} mm')
assert wall >= 1.6, 'wall under 4 perimeters of a 0.4 nozzle'

with zipfile.ZipFile(sys.argv[2], 'w', zipfile.ZIP_DEFLATED) as zo:
    for i in zin.infolist():
        data = out.get(i.filename, zin.read(i.filename))
        if i.filename == 'Metadata/model_settings.config':  # drop stale face counts, Bambu recomputes
            data = re.sub(rb'\s*<(metadata face_count|mesh_stat)[^>]*/>', b'', data)
        zo.writestr(i, data)
print('wrote', sys.argv[2])
