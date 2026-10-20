from pathlib import Path

from rdflib import Graph

from onto_to_pages.model import build_ontology_doc

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
