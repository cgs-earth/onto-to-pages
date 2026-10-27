from pathlib import Path

from rdflib import Graph

from onto_to_pages.model import build_ontology_doc, local_name

FIXTURE = Path(__file__).parent / "fixtures" / "example.ttl"


def _load_doc():
    graph = Graph()
    graph.parse(FIXTURE, format="turtle")
    return build_ontology_doc(graph, fallback_title="Example Vocabulary")


def test_ontology_metadata():
    doc = _load_doc()
    assert doc.title == "Example Vocabulary"
    assert doc.description == "A small vocabulary used to exercise onto-to-pages."
    assert doc.version_info == "0.1.0"
    assert doc.creators == ["Jane Doe"]


def test_classes_extracted_with_hierarchy():
    doc = _load_doc()
    labels = {c.label for c in doc.classes}
    assert {"Animal", "Dog", "Person"} <= labels

    dog = next(c for c in doc.classes if c.label == "Dog")
    assert dog.comment == "A domesticated canine."
    assert [r.label for r in dog.sub_of] == ["Animal"]

    animal = next(c for c in doc.classes if c.label == "Animal")
    assert "Dog" in [r.label for r in animal.super_of]


def test_classes_ordered_depth_first_with_indentation_depth():
    doc = _load_doc()
    # Dog (a subclass of Animal) should be placed immediately after Animal,
    # one level deeper, rather than sorted alphabetically into its own slot.
    labels_in_order = [c.label for c in doc.classes]
    assert labels_in_order.index("Dog") == labels_in_order.index("Animal") + 1

    by_label = {c.label: c for c in doc.classes}
    assert by_label["Animal"].depth == 0
    assert by_label["Dog"].depth == 1
    assert by_label["Person"].depth == 0


def test_skos_labels_and_definitions_used_as_fallback():
    doc = _load_doc()
    person = next(c for c in doc.classes if c.label == "Person")
    assert person.comment == "A human being."


def test_object_and_datatype_properties_split_correctly():
    doc = _load_doc()
    assert [p.label for p in doc.object_properties] == ["owner"]
    assert [p.label for p in doc.datatype_properties] == ["name"]

    owner = doc.object_properties[0]
    assert [r.label for r in owner.domain] == ["Animal"]
    assert [r.label for r in owner.range] == ["Person"]


def test_individuals_extracted():
    doc = _load_doc()
    assert [i.label for i in doc.individuals] == ["Rex"]


def test_local_name_handles_bare_namespace_iris():
    # A seeAlso/domain/range target can be a bare namespace IRI (no local
    # part after the final "/" or "#"); it must fall back to something
    # readable instead of an empty label.
    assert local_name("https://schema.org/") == "schema.org"
    assert local_name("http://www.w3.org/ns/dcat#") == "dcat"
    assert local_name("http://www.w3.org/ns/sosa/") == "sosa"
    assert local_name("https://example.org/vocab#Dog") == "Dog"


def test_see_also_targets_that_are_bare_namespaces_get_a_label():
    graph = Graph()
    graph.parse(data=f"""
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        <https://example.org/onto> a owl:Ontology ;
            rdfs:seeAlso <https://schema.org/>, <http://www.w3.org/ns/dcat#> .
    """, format="turtle")
    doc = build_ontology_doc(graph, fallback_title="Test")
    labels = {r.label for r in doc.see_also}
    assert "" not in labels
    assert labels == {"schema.org", "dcat"}


def test_skos_notes_are_collected_separately_from_the_main_comment():
    doc = _load_doc()
    dog = next(c for c in doc.classes if c.label == "Dog")
    assert dog.comment == "A domesticated canine."
    assert dog.notes == [
        "Includes working and companion breeds alike.",
        "Not to be confused with ex:Wolf, which is out of scope for this vocabulary.",
    ]


def test_untyped_subclass_subjects_inferred_as_classes():
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex: <http://example.org/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Feature rdfs:subClassOf ex:External .
        ex:Network a owl:Class ; rdfs:subClassOf ex:Feature .
        """,
        format="turtle",
    )
    doc = build_ontology_doc(graph)

    by_label = {c.label: c for c in doc.classes}
    # ex:Feature has no rdf:type but is the subject of rdfs:subClassOf.
    assert "Feature" in by_label
    # ex:External is only ever an object, so it stays external.
    assert "External" not in by_label
    # The inferred class participates in the hierarchy like a declared one.
    assert by_label["Feature"].depth == 0
    assert by_label["Network"].depth == 1
    assert "Network" in [r.label for r in by_label["Feature"].super_of]


def test_properties_ordered_by_subproperty_hierarchy():
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex: <http://example.org/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:related a owl:ObjectProperty .
        ex:parent a owl:ObjectProperty ; rdfs:subPropertyOf ex:related .
        ex:mother a owl:ObjectProperty ; rdfs:subPropertyOf ex:parent .
        ex:another a owl:ObjectProperty .

        ex:identifier a owl:DatatypeProperty .
        ex:isbn a owl:DatatypeProperty ; rdfs:subPropertyOf ex:identifier .
        """,
        format="turtle",
    )
    doc = build_ontology_doc(graph)

    assert [(p.label, p.depth) for p in doc.object_properties] == [
        ("another", 0),
        ("related", 0),
        ("parent", 1),
        ("mother", 2),
    ]
    assert [(p.label, p.depth) for p in doc.datatype_properties] == [
        ("identifier", 0),
        ("isbn", 1),
    ]
