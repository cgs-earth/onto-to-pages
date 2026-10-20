"""Extract a documentation-friendly model from an rdflib Graph.

This is the piece that stands in for pyLODE: it walks the parsed RDF graph
and pulls out whatever "useful for documentation" annotations are present
(rdfs:label/comment, skos labels/definitions, dcterms metadata, ...) into
plain dataclasses that the templates can render without knowing anything
about RDF.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import DC, DCTERMS, OWL, RDF, RDFS, SKOS

# Preference order for picking a human label / description out of a graph.
# rdfs:label and rdfs:comment are the RDF-native choices; SKOS and Dublin
# Core terms are common on vocabularies that model themselves as thesauri.
LABEL_PROPERTIES = (RDFS.label, SKOS.prefLabel, DCTERMS.title, DC.title)
COMMENT_PROPERTIES = (RDFS.comment, SKOS.definition, DCTERMS.description, DC.description)

PREFERRED_LANGS = ("en", "")


@dataclass
class TermRef:
    """A lightweight, renderable pointer to another RDF term."""

    uri: str
    curie: str
    label: str
    anchor: str = ""


@dataclass
class Entity:
    uri: str
    curie: str
    label: str
    comment: str | None = None
    notes: list[str] = field(default_factory=list)
    kind: str = ""
    deprecated: bool = False
    sub_of: list[TermRef] = field(default_factory=list)
    super_of: list[TermRef] = field(default_factory=list)
    domain: list[TermRef] = field(default_factory=list)
    range: list[TermRef] = field(default_factory=list)
    see_also: list[TermRef] = field(default_factory=list)
    is_defined_by: TermRef | None = None
    depth: int = 0

    @property
    def anchor(self) -> str:
        # Matches the fragment of the term's own IRI, so appending
        # "#LocalName" to the page URL (the same way you'd dereference the
        # IRI itself) jumps straight to this term.
        return local_name(self.uri)


@dataclass
class NamespaceBinding:
    prefix: str
    uri: str


@dataclass
class OntologyDoc:
    uri: str | None
    title: str
    description: str | None = None
    version_info: str | None = None
    version_iri: str | None = None
    license: str | None = None
    creators: list[str] = field(default_factory=list)
    see_also: list[TermRef] = field(default_factory=list)
    imports: list[TermRef] = field(default_factory=list)
    namespaces: list[NamespaceBinding] = field(default_factory=list)
    classes: list[Entity] = field(default_factory=list)
    object_properties: list[Entity] = field(default_factory=list)
    datatype_properties: list[Entity] = field(default_factory=list)
    annotation_properties: list[Entity] = field(default_factory=list)
    properties: list[Entity] = field(default_factory=list)
    datatypes: list[Entity] = field(default_factory=list)
    individuals: list[Entity] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)

    @property
    def all_entities(self) -> list[Entity]:
        return (
            self.classes
            + self.object_properties
            + self.datatype_properties
            + self.annotation_properties
            + self.properties
            + self.datatypes
            + self.individuals
        )

    @property
    def local_uris(self) -> set[str]:
        return {e.uri for e in self.all_entities}

    @property
    def sections(self) -> list[tuple[str, str, list[Entity]]]:
        """(heading, blurb, entities) tuples for every non-empty section."""
        defs = [
            ("Classes", "Types of things this vocabulary defines.", self.classes),
            (
                "Object Properties",
                "Relationships that link one resource to another resource.",
                self.object_properties,
            ),
            (
                "Datatype Properties",
                "Relationships that link a resource to a literal value.",
                self.datatype_properties,
            ),
            (
                "Annotation Properties",
                "Metadata properties used to describe other terms.",
                self.annotation_properties,
            ),
            ("Properties", "Properties without a more specific OWL type.", self.properties),
            ("Datatypes", "Custom literal (value) types defined by this vocabulary.", self.datatypes),
            ("Individuals", "Named instances defined by this vocabulary.", self.individuals),
        ]
        return [(h, b, e) for h, b, e in defs if e]


def local_name(uri: str) -> str:
    # A bare namespace IRI (e.g. "https://schema.org/" or ".../dcat#") has
    # nothing after its final separator; strip trailing separators first so
    # these fall back to a readable name instead of an empty string.
    trimmed = uri.rstrip("#/")
    for sep in ("#", "/"):
        if sep in trimmed:
            name = trimmed.rsplit(sep, 1)[-1]
            if name:
                return name
    return trimmed or uri


def _curie(graph: Graph, uri: URIRef) -> str:
    try:
        qname = graph.namespace_manager.qname(uri)
        if qname and ":" in qname:
            return qname
    except Exception:
        pass
    return str(uri)


def _literal_values(graph: Graph, subject, prop) -> list[str]:
    """All (not just the single "best") literal values of ``prop``, in the
    preferred language. Unlike a label/comment, each skos:note is its own
    distinct remark rather than alt-language copies of the same text, so we
    want every one of them, not just the first match."""
    return [
        str(obj)
        for obj in graph.objects(subject, prop)
        if isinstance(obj, Literal) and (obj.language or "") in PREFERRED_LANGS
    ]


def _literal_value(graph: Graph, subject, properties: tuple) -> str | None:
    best = None
    for prop in properties:
        candidates = list(graph.objects(subject, prop))
        if not candidates:
            continue
        for lang in PREFERRED_LANGS:
            for obj in candidates:
                if isinstance(obj, Literal) and (obj.language or "") == lang:
                    return str(obj)
        best = str(candidates[0])
        break
    return best


def _label_for(graph: Graph, node) -> str:
    if isinstance(node, Literal):
        return str(node)
    if isinstance(node, BNode):
        return "(anonymous)"
    label = _literal_value(graph, node, LABEL_PROPERTIES)
    return label or local_name(str(node))


def _term_ref(graph: Graph, node) -> TermRef:
    uri = str(node)
    curie = _curie(graph, node) if isinstance(node, URIRef) else uri
    return TermRef(uri=uri, curie=curie, label=_label_for(graph, node), anchor=local_name(uri))


def _is_deprecated(graph: Graph, subject) -> bool:
    for obj in graph.objects(subject, OWL.deprecated):
        if isinstance(obj, Literal) and obj.toPython() is True:
            return True
    return False


def _build_entity(graph: Graph, uri: URIRef, kind: str, sub_prop) -> Entity:
    label = _literal_value(graph, uri, LABEL_PROPERTIES) or local_name(str(uri))
    comment = _literal_value(graph, uri, COMMENT_PROPERTIES)
    notes = _literal_values(graph, uri, SKOS.note)
    sub_of = [_term_ref(graph, o) for o in graph.objects(uri, sub_prop) if not isinstance(o, BNode)]
    domain = [_term_ref(graph, o) for o in graph.objects(uri, RDFS.domain) if not isinstance(o, BNode)]
    rng = [_term_ref(graph, o) for o in graph.objects(uri, RDFS.range) if not isinstance(o, BNode)]
    see_also = [_term_ref(graph, o) for o in graph.objects(uri, RDFS.seeAlso)]
    defined_by = next(graph.objects(uri, RDFS.isDefinedBy), None)

    return Entity(
        uri=str(uri),
        curie=_curie(graph, uri),
        label=label,
        comment=comment,
        notes=notes,
        kind=kind,
        deprecated=_is_deprecated(graph, uri),
        sub_of=sub_of,
        domain=domain,
        range=rng,
        see_also=see_also,
        is_defined_by=_term_ref(graph, defined_by) if defined_by is not None else None,
    )


def _link_hierarchy(entities: list[Entity]) -> None:
    """Fill in Entity.super_of by inverting the sub_of relationships."""
    by_uri = {e.uri: e for e in entities}
    for entity in entities:
        for parent in entity.sub_of:
            parent_entity = by_uri.get(parent.uri)
            if parent_entity is not None:
                parent_entity.super_of.append(
                    TermRef(entity.uri, entity.curie, entity.label, anchor=entity.anchor)
                )


def _sorted(entities: list[Entity]) -> list[Entity]:
    return sorted(entities, key=lambda e: e.label.lower())


def _order_by_hierarchy(entities: list[Entity]) -> list[Entity]:
    """Reorder ``entities`` depth-first by their subclass hierarchy.

    Sets ``.depth`` on each entity so templates can indent subclasses under
    their parent. An entity whose declared parent isn't also in this list
    (e.g. an external/imported superclass) is treated as a root; if it has
    more than one local parent, the alphabetically-first one is used so it's
    still placed exactly once.
    """
    by_uri = {e.uri: e for e in entities}
    children: dict[str, list[Entity]] = {}
    roots: list[Entity] = []

    for entity in entities:
        local_parents = sorted(
            (p for p in entity.sub_of if p.uri in by_uri),
            key=lambda p: by_uri[p.uri].label.lower(),
        )
        if local_parents:
            children.setdefault(local_parents[0].uri, []).append(entity)
        else:
            roots.append(entity)

    for siblings in children.values():
        siblings.sort(key=lambda e: e.label.lower())
    roots.sort(key=lambda e: e.label.lower())

    ordered: list[Entity] = []
    seen: set[str] = set()

    def visit(entity: Entity, depth: int) -> None:
        if entity.uri in seen:
            return
        seen.add(entity.uri)
        entity.depth = depth
        ordered.append(entity)
        for child in children.get(entity.uri, []):
            visit(child, depth + 1)

    for root in roots:
        visit(root, 0)

    # Defensive: a subClassOf cycle would otherwise leave entities unvisited.
    for entity in entities:
        if entity.uri not in seen:
            entity.depth = 0
            ordered.append(entity)

    return ordered


def build_ontology_doc(graph: Graph, *, base_uri: str | None = None, fallback_title: str = "Ontology") -> OntologyDoc:
    """Walk ``graph`` and produce an :class:`OntologyDoc` ready for rendering."""

    ontology_uri = _select_ontology_uri(graph, base_uri)

    title = fallback_title
    description = None
    version_info = None
    version_iri = None
    license_ = None
    creators: list[str] = []
    see_also: list[TermRef] = []
    imports: list[TermRef] = []

    if ontology_uri is not None:
        title = _literal_value(graph, ontology_uri, LABEL_PROPERTIES) or fallback_title
        description = _literal_value(graph, ontology_uri, COMMENT_PROPERTIES)
        version_info = _literal_value(graph, ontology_uri, (OWL.versionInfo,))
        version_iri_obj = next(graph.objects(ontology_uri, OWL.versionIRI), None)
        version_iri = str(version_iri_obj) if version_iri_obj is not None else None
        license_obj = next(graph.objects(ontology_uri, DCTERMS.license), None)
        license_ = str(license_obj) if license_obj is not None else None
        creators = [
            _label_for(graph, o)
            for o in list(graph.objects(ontology_uri, DCTERMS.creator))
            + list(graph.objects(ontology_uri, DC.creator))
        ]
        see_also = [_term_ref(graph, o) for o in graph.objects(ontology_uri, RDFS.seeAlso)]
        imports = [_term_ref(graph, o) for o in graph.objects(ontology_uri, OWL.imports)]

    namespaces = _used_namespaces(graph)

    classified: set[str] = set()

    def collect(rdf_type, kind: str, sub_prop=RDFS.subClassOf) -> list[Entity]:
        uris = {s for s in graph.subjects(RDF.type, rdf_type) if isinstance(s, URIRef)}
        uris -= {URIRef(u) for u in classified}
        entities = [_build_entity(graph, u, kind, sub_prop) for u in uris]
        classified.update(str(u) for u in uris)
        return entities

    classes = collect(OWL.Class, "class") + collect(RDFS.Class, "class")
    object_properties = collect(OWL.ObjectProperty, "object property", RDFS.subPropertyOf)
    datatype_properties = collect(OWL.DatatypeProperty, "datatype property", RDFS.subPropertyOf)
    # owl:OntologyProperty is OWL 1's (deprecated but still seen) term for a
    # property whose domain is an ontology itself; it serves the same
    # documentation role as owl:AnnotationProperty, so the two are merged.
    annotation_properties = collect(OWL.AnnotationProperty, "annotation property", RDFS.subPropertyOf) + collect(
        OWL.OntologyProperty, "annotation property", RDFS.subPropertyOf
    )
    generic_properties = collect(RDF.Property, "property", RDFS.subPropertyOf)
    datatypes = collect(RDFS.Datatype, "datatype", RDFS.subClassOf)
    individuals = collect(OWL.NamedIndividual, "individual", RDFS.subClassOf)

    # Alignment files often state subclass axioms about terms without ever
    # declaring them as classes; rdfs:subClassOf implies its subject is one
    # (RDFS entailment rule rdfs9), so document those too. This runs after
    # every typed collection so an explicit declaration always wins.
    inferred = {
        s for s in graph.subjects(RDFS.subClassOf, None) if isinstance(s, URIRef)
    } - {URIRef(u) for u in classified}
    classes += [_build_entity(graph, u, "class", RDFS.subClassOf) for u in inferred]
    classified.update(str(u) for u in inferred)

    classes = _sorted(classes)
    object_properties = _sorted(object_properties)
    datatype_properties = _sorted(datatype_properties)
    annotation_properties = _sorted(annotation_properties)
    generic_properties = _sorted(generic_properties)
    datatypes = _sorted(datatypes)
    individuals = _sorted(individuals)

    _link_hierarchy(classes)
    for prop_group in (object_properties, datatype_properties, annotation_properties, generic_properties):
        _link_hierarchy(prop_group)

    classes = _order_by_hierarchy(classes)

    return OntologyDoc(
        uri=str(ontology_uri) if ontology_uri is not None else None,
        title=title,
        description=description,
        version_info=version_info,
        version_iri=version_iri,
        license=license_,
        creators=[c for c in creators if c],
        see_also=see_also,
        imports=imports,
        namespaces=namespaces,
        classes=classes,
        object_properties=object_properties,
        datatype_properties=datatype_properties,
        annotation_properties=annotation_properties,
        properties=generic_properties,
        datatypes=datatypes,
        individuals=individuals,
    )


def _used_namespaces(graph: Graph) -> list[NamespaceBinding]:
    """Namespace bindings that are actually referenced by a term in the graph.

    rdflib pre-binds a couple dozen well-known prefixes (dcat, geo, prov, ...)
    regardless of whether the document uses them; showing all of them would
    bury the handful that matter for this particular vocabulary.
    """
    terms: set[str] = set()
    for s, p, o in graph:
        for term in (s, p, o):
            if isinstance(term, URIRef):
                terms.add(str(term))

    used = []
    for prefix, ns in sorted(graph.namespace_manager.namespaces()):
        if prefix in ("", "xml"):
            continue
        ns_str = str(ns)
        if any(term.startswith(ns_str) for term in terms):
            used.append(NamespaceBinding(prefix=str(prefix), uri=ns_str))
    return used


def _select_ontology_uri(graph: Graph, base_uri: str | None) -> URIRef | None:
    candidates = [s for s in graph.subjects(RDF.type, OWL.Ontology) if isinstance(s, URIRef)]
    if not candidates:
        return None
    if base_uri:
        for c in candidates:
            if str(c) == base_uri:
                return c
    return candidates[0]
