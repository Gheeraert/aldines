"""Petit contrat entre le traitement Augustinus et la publication, sans modèle TEI universel."""
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Issue:
    level: str
    file: str
    message: str
    line: int | None = None

    def __str__(self):
        return f"{self.level.upper()} · {self.file}{':' + str(self.line) if self.line else ''} · {self.message}"


@dataclass
class Row:
    anchor: str
    latin: str
    french: str
    latin_text: str = ""
    french_text: str = ""
    kind: str = "sentence"
    style: str = ""


@dataclass
class Unit:
    id: str
    file: Path
    title: str
    route: str
    tome: int
    book: int
    label: str
    book_label: str
    rows: list[Row] = field(default_factory=list)
    translated: int = 0
    sentences: int = 0
    metadata: dict = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)


@dataclass
class Corpus:
    units: list[Unit] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def errors(self):
        return [i for i in self.issues if i.level == "error"]

    def report(self):
        return {"units": len(self.units), "sentences": sum(u.sentences for u in self.units),
                "translated": sum(u.translated for u in self.units),
                "issues": [asdict(i) for i in self.issues]}
