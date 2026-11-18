"""Offline inspection of saved SEC inline XBRL, independent of the application."""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def local(tag):
    return tag.rsplit("}", 1)[-1]


def text(node):
    return re.sub(r"\s+", " ", " ".join(node.itertext())).strip()


def inspect(path):
    root = ET.fromstring(path.read_bytes())
    parents = {child: parent for parent in root.iter() for child in parent}
    contexts, units = {}, {}
    for element in root.iter():
        if local(element.tag) == "context":
            values = {local(child.tag): text(child) for child in element.iter()
                      if local(child.tag) in ("startDate", "endDate", "instant", "identifier")}
            values["dimensions"] = [text(child) for child in element.iter()
                                    if local(child.tag) in ("explicitMember", "typedMember")]
            contexts[element.attrib["id"]] = values
        elif local(element.tag) == "unit":
            units[element.attrib["id"]] = ET.tostring(element, encoding="unicode")
    facts, blocks = [], []
    for element in root.iter():
        tag = local(element.tag)
        if tag == "nonFraction":
            parent = element
            while parent in parents and local(parent.tag) != "tr":
                parent = parents[parent]
            facts.append({"id": element.get("id"), "name": element.get("name"),
                          "context_ref": element.get("contextRef"), "context": contexts[element.get("contextRef")],
                          "unit_ref": element.get("unitRef"), "unit_xml": units.get(element.get("unitRef")),
                          "scale": element.get("scale", "0"), "sign": element.get("sign", "+"),
                          "decimals": element.get("decimals"), "format": element.get("format"),
                          "display_text": text(element), "statement_row": text(parent)[:4000]})
        if tag in ("tr", "p") or (tag == "div" and not any(local(e.tag) in ("div", "tr", "p") for e in list(element))):
            value = text(element)
            if value and (not blocks or blocks[-1] != value):
                blocks.append(value)
    return {"source_file": str(path.relative_to(ROOT)), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "extraction": "stdlib ElementTree; statement text is a saved projection, raw HTML retained",
            "contexts": contexts, "units": units, "facts": facts}, blocks


if __name__ == "__main__":
    out = ROOT / "inspection"
    out.mkdir(exist_ok=True)
    for source in sorted((ROOT / "sources").glob("*.htm")):
        parsed, blocks = inspect(source)
        with (out / (source.stem + ".inline.json")).open("x", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
            f.write("\n")
        with (out / (source.stem + ".text.txt")).open("x", encoding="utf-8") as f:
            f.write("\n".join(blocks) + "\n")
        print(source.name, "inline facts", len(parsed["facts"]), "text blocks", len(blocks))
