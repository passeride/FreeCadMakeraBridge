"""Bounded display meshes and material metadata in the CAM Job's work frame."""
import math

MAX_TRIANGLES = 100_000
MAX_PARTS = 32
MAX_COORDINATE = 10_000


def _number(value):
    value = getattr(value, "Value", value)
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


def _text(value, limit=200):
    return " ".join(str(value).split())[:limit]


def _base(obj):
    """Job resource clones link to their authored body, which owns its material."""
    for key in ("Objects", "BaseGeometry"):
        links = getattr(obj, key, None)
        if links:
            if isinstance(links, (list, tuple)):
                return links[0]
            return links
    return obj


def appearance(obj):
    original = _base(obj)
    card = {}
    for candidate in (original, obj):
        material = getattr(candidate, "Material", None)
        if isinstance(material, dict):
            card.update(material)
        elif material is not None:
            content = getattr(material, "Material", None)
            if isinstance(content, dict):
                card.update(content)
            for key in ("Name", "Label", "Density", "YoungsModulus", "PoissonRatio"):
                value = getattr(material, key, None)
                if value is not None:
                    card.setdefault(key, value)
    name = card.get("Name") or card.get("Label") or getattr(original, "MaterialName", None)
    result = {"name": _text(name or "Unspecified material"), "source": "freecad"}
    view = getattr(original, "ViewObject", None) or getattr(obj, "ViewObject", None)
    if view is not None:
        color = getattr(view, "ShapeColor", None)
        if color and len(color) >= 3:
            rgb = [_number(c) for c in color[:3]]
            if all(c is not None and 0 <= c <= 1 for c in rgb):
                result["color"] = "#" + "".join(f"{round(c * 255):02x}" for c in rgb)
        surface = getattr(view, "ShapeMaterial", None)
        shine = _number(getattr(surface, "Shininess", None))
        if shine is not None and 0 <= shine <= 128:
            result["roughness"] = max(0.04, min(1.0, math.sqrt(2 / (shine + 2))))
        transparency = _number(getattr(view, "Transparency", None))
        if transparency is not None and 0 <= transparency <= 100:
            result["opacity"] = max(0.05, 1 - transparency / 100)
    # Do not infer physical units from bare numbers. FreeCAD quantities convert explicitly.
    density = card.get("Density")
    if density is not None:
        try:
            import FreeCAD as App
            quantity = density if hasattr(density, "getValueAs") else App.Units.Quantity(str(density))
            kg_m3 = _number(quantity.getValueAs("kg/m^3"))
            if kg_m3 is not None and 0 < kg_m3 <= 1_000_000:
                result["densityKgM3"] = kg_m3
        except (ValueError, TypeError, AttributeError):
            pass
    properties = []
    for key in ("Density", "YoungsModulus", "PoissonRatio", "UltimateTensileStrength", "YieldStrength", "Hardness"):
        if key in card:
            properties.append({"name": key, "value": _text(card[key])})
    if properties:
        result["properties"] = properties
    return result


def _coordinates(vertex):
    values = [float(vertex.x), float(vertex.y), float(vertex.z)]
    if any(not math.isfinite(v) or abs(v) > MAX_COORDINATE for v in values):
        raise ValueError("Modellen har ugyldige koordinater.")
    return [round(v, 6) for v in values]


def export_reference(job):
    """Use Job.Model resource clones, whose shape coordinates are CAM coordinates.

    Parent placements are baked once relative to Shape.Placement. No centering, unit
    guessing, or stock-minimum translation is allowed: that would misalign G-code.
    """
    models = list(getattr(getattr(job, "Model", None), "Group", ()) or ())
    if not models or len(models) > MAX_PARTS:
        raise ValueError("CAM-jobben må ha mellom 1 og 32 modellobjekter.")
    parts = []
    total = 0
    for obj in models:
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull():
            raise ValueError("CAM-modellen mangler en gyldig Shape: " + obj.Label)
        # Shape tessellation includes Shape.Placement. Only add enclosing placements.
        correction = obj.getGlobalPlacement().multiply(shape.Placement.inverse())
        vertices, triangles = shape.tessellate(0.05)
        total += len(triangles)
        if not triangles or total > MAX_TRIANGLES:
            raise ValueError("Referansemodellen overskrider 100 000 trekanter. Forenkle modellen før eksport.")
        positions = [v for point in vertices for v in _coordinates(correction.multVec(point))]
        parts.append({"name": _text(obj.Label), "positions": positions,
                      "indices": [int(i) for triangle in triangles for i in triangle],
                      "material": appearance(obj)})
    stock = getattr(job, "Stock", None)
    if stock is None or not hasattr(stock, "Shape") or stock.Shape.isNull():
        raise ValueError("CAM-jobben mangler et gyldig startemne.")
    shape = stock.Shape.copy()
    shape.Placement = stock.getGlobalPlacement()
    box = shape.BoundBox
    minimum = [box.XMin, box.YMin, box.ZMin]
    maximum = [box.XMax, box.YMax, box.ZMax]
    if any(not math.isfinite(v) or abs(v) > MAX_COORDINATE for v in minimum + maximum) or any(b <= a for a, b in zip(minimum, maximum)):
        raise ValueError("Startemnet har ugyldige dimensjoner.")
    material = appearance(stock)
    # Stock often has no assigned material; use the single body's authored material.
    if material["name"] == "Unspecified material" and len(parts) == 1:
        material = parts[0]["material"]
    return {"name": _text(job.Label), "units": "mm", "frame": "work", "parts": parts,
            "offset": [0, 0, 0], "rotation": [0, 0, 0], "scale": 1}, {"min": minimum, "max": maximum}, material
