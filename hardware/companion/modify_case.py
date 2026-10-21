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

# Key switch (Blow SWT-06357): double-D barrel 11.2 round / 10.5 across flats, 15.9 deep, 14 collar.
SPLIT_Y = 20.5                   # clean section: 2 mm plate + compartment walls/floor + antenna tunnel only
LENGTHEN_Y = 20.0
KEY_X, KEY_Y = 8.0, SPLIT_Y + LENGTHEN_Y / 2
KEY_ROUND, KEY_FLATS, KEY_CLEAR = 11.2, 10.5, 0.2
KEY_DEPTH, KEY_COLLAR = 15.9, 14.0
KEY_GRIP = 2.0                   # push-in, locking tab grips a 2 mm panel (measured)
PLATE_UNDER = 9.58               # front-plate underside at SPLIT_Y; its top is FK's max z
GROOVE_FILL_X = (-5.0, 21.0)     # decorative 1 mm grooves on the plate top, filled flat in the new strip

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
    for x, y, z in m.vertices: etree.SubElement(vs, f'{{{NS["m"]}}}vertex', x=f'{x:.9g}', y=f'{y:.9g}', z=f'{z:.9g}')
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

def key_hole():
    """Double-D through the front plate: round top/bottom, flats left/right (normal to x) stop it turning."""
    r, h = (KEY_ROUND + KEY_CLEAR) / 2, (KEY_FLATS + KEY_CLEAR) / 2
    z0 = PLATE_UNDER - 1.0
    cyl = mf.Manifold.cylinder(6.0, r, circular_segments=96).translate((KEY_X, KEY_Y, z0))
    flats = mf.Manifold.cube((2 * h, 2 * r + 2, 6.0)).translate((KEY_X - h, KEY_Y - r - 1, z0))
    return cyl ^ flats

def modify(m, dz, fk):
    M = to_mf(m)
    assert M.status() == mf.Error.NoError, M.status()
    M = stretch(M, 0, SPLIT_X, -STRETCH_X)
    M = stretch(M, 1, SPLIT_Y, LENGTHEN_Y)
    M = M - bore(dz)
    if fk:
        top = m.bounds[1][2]
        x0, x1 = GROOVE_FILL_X
        fill = mf.Manifold.cube((x1 - x0, LENGTHEN_Y, top - PLATE_UNDER - 0.5)).translate((x0, SPLIT_Y, PLATE_UNDER + 0.5))
        M = M + fill - key_hole()
    return M

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
    assert abs(n.bounds[0][0] - (m.bounds[0][0] - STRETCH_X)) < 0.05 and abs(n.bounds[1][1] - (m.bounds[1][1] + LENGTHEN_Y)) < 0.05
    before.append((m, dz)); after.append((n, dz)); out[name] = write_mesh(t, n)

BAY_YS = (3, 5, 10, 20, 30, 40, 50, 56)
for y in (1.5,) + BAY_YS:
    print(f'y={y:4}: antenna free dia {free_dia(before, y):5.2f} -> {free_dia(after, y):5.2f}')
assert all(free_dia(after, y) >= BORE - 0.05 for y in BAY_YS)
assert free_dia(after, 1.5) == 0  # bulkhead wall kept
wall = AXIS_X - BORE / 2 - (OUTER_X - STRETCH_X)
print(f'side wall beside the bore: {wall:.2f} mm')
assert wall >= 1.6, 'wall under 4 perimeters of a 0.4 nozzle'

def first_hit_down(mesh, x, y):
    loc, _, _ = mesh.ray.intersects_location([[x, y, 40.0]], [[0, 0, -1.0]])
    return loc[:, 2].max() if len(loc) else None

fk_n = after[0][0]
top = fk_n.bounds[1][2]
env = trimesh.creation.cylinder(radius=KEY_COLLAR / 2, height=KEY_DEPTH + 0.3, sections=96)
env.apply_translation([KEY_X, KEY_Y, PLATE_UNDER - (KEY_DEPTH + 0.3) / 2 - 0.01])
clash = 0.0
for mesh, dz in after:
    e = env.copy(); e.apply_translation([0, 0, -dz])
    clash += (to_mf(mesh) ^ to_mf(e)).volume()
hole = first_hit_down(fk_n, KEY_X, KEY_Y)
seat = [first_hit_down(fk_n, KEY_X + r * np.cos(a), KEY_Y + r * np.sin(a))
        for r in ((KEY_ROUND + KEY_CLEAR) / 2 + 1.6, KEY_COLLAR / 2 + 0.3) for a in np.linspace(0, 2 * np.pi, 16, endpoint=False)]
print(f'key switch: body clash {clash:.2f} mm3, hole first hit {hole}, seat z {min(s or -99 for s in seat):.2f}..{max(s or -99 for s in seat):.2f} (top {top:.2f})')
assert clash < 0.01, 'switch body hits the case'
assert hole is None or hole < PLATE_UNDER - 1, 'key hole not open'
assert all(s is not None and abs(s - top) < 0.02 for s in seat), 'collar seat / wall around the hole not flat full-thickness plate'
assert abs(top - PLATE_UNDER - KEY_GRIP) < 0.1, f'plate {top - PLATE_UNDER:.2f} mm, the locking tab grips {KEY_GRIP} mm'

with zipfile.ZipFile(sys.argv[2], 'w', zipfile.ZIP_DEFLATED) as zo:
    for i in zin.infolist():
        data = out.get(i.filename, zin.read(i.filename))
        if i.filename == 'Metadata/model_settings.config':  # drop stale face counts, Bambu recomputes
            data = re.sub(rb'\s*<(metadata face_count|mesh_stat)[^>]*/>', b'', data)
        zo.writestr(i, data)
print('wrote', sys.argv[2])
