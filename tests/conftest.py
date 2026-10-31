from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aldines.config import DEFAULTS, Project


def tei(number=1, extra="", french=True):
    uid = f"t1.l01.s{number:02}"
    translation = f'''<div type="translation" xml:id="{uid}.fr"><head>TITRE FRANÇAIS</head><p corresp="#{uid}.la.p1">
<s corresp="#{uid}.la.s1">Père et parole éternelle.<note type="trad">Sens de la traduction.</note><note type="source">Source citée.</note></s>
<s corresp="#{uid}.la.s2">Abréviation et incertitude.</s></p><trailer><s corresp="#{uid}.la.s3">Fin.</s></trailer></div>''' if french else ""
    return f'''<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><titleStmt>
<title>Édition de test {number}</title><author>Auteur TEI</author>
<respStmt><resp>direction scientifique</resp><name>Éditrice</name></respStmt></titleStmt>
<publicationStmt><p>Travail en cours</p></publicationStmt><sourceDesc><p>Imprimé de test</p></sourceDesc></fileDesc></teiHeader>
<text><body><div type="edition" xml:id="{uid}.la"><pb n="1"/><div type="liber" n="1">
<head>TITRE <hi rend="smallcaps">LATIN</hi></head><p xml:id="{uid}.la.p1">
<s xml:id="{uid}.la.s1">Pa<pb n="2"/><cb n="a"/>ter &amp; <quote xml:lang="grc">λόγος</quote> <note place="margin-left" n="a">Manchette ancienne.</note><hi rend="smallcaps">æterna</hi>.<fw type="catch">Réclame</fw></s>
<s xml:id="{uid}.la.s2"><choice><abbr>q;</abbr><expan>que</expan></choice> <sic>u</sic><unclear>i</unclear><gap reason="illegible"/>{extra}</s>
</p><trailer><s xml:id="{uid}.la.s3">Finis.</s></trailer></div></div>
{translation}
</body></text></TEI>'''


@pytest.fixture
def project(tmp_path):
    source = tmp_path / "tei"
    source.mkdir()
    (source / "a.xml").write_text(tei(1), encoding="utf-8")
    (source / "b.xml").write_text(tei(2), encoding="utf-8")
    (source / "master.xml").write_text('''<teiCorpus xmlns="http://www.tei-c.org/ns/1.0" xmlns:xi="http://www.w3.org/2001/XInclude"><xi:include href="b.xml"/><xi:include href="a.xml"/></teiCorpus>''', encoding="utf-8")
    data = deepcopy(DEFAULTS)
    data["sources"].update(directory="tei", master="tei/master.xml")
    p = Project(tmp_path / "aldines.json", data)
    p.save()
    return p
