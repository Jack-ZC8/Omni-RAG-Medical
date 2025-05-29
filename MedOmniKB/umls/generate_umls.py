import os
import sqlite3

from tqdm import tqdm

db_path = 'umls.sqlite3'
if os.path.exists(db_path):
    os.remove(db_path)
db = sqlite3.connect(db_path)
cursor = db.cursor()

cursor.executescript("""
CREATE VIRTUAL TABLE MRCONSO USING fts5(
    CUI,
    SAB,
    STR
, tokenize="porter unicode61");


CREATE TABLE MRCONSOEM (
    CUI	char(8) NOT NULL,
    SAB	varchar(40) NOT NULL,
    STR	varchar(100) NOT NULL COLLATE NOCASE
);
CREATE INDEX X_MRCONSOEM_CUI ON MRCONSOEM(CUI);
CREATE INDEX X_MRCONSOEM_STR ON MRCONSOEM(STR);


CREATE TABLE MRDEF (
    CUI	char(8) NOT NULL,
    SAB	varchar(40) NOT NULL,
    DEF	text NOT NULL
);
CREATE INDEX X_MRDEF_CUI ON MRDEF(CUI);
CREATE INDEX X_MRDEF_SAB ON MRDEF(SAB);


CREATE TABLE MRREL (
    CUI1	char(8) NOT NULL,
    STYPE1	varchar(40) NOT NULL,
    STR1	text NOT NULL,
    CUI2	char(8) NOT NULL,
    STYPE2	varchar(40) NOT NULL,
    STR2	text NOT NULL,
    RELA	varchar(100) NOT NULL,
    SAB	varchar(40) NOT NULL
);
CREATE INDEX X_MRREL_CUI1 ON MRREL(CUI1);
CREATE INDEX X_MRREL_STYPE1 ON MRREL(STYPE1);
CREATE INDEX X_MRREL_CUI2 ON MRREL(CUI2);
CREATE INDEX X_MRREL_STYPE2 ON MRREL(STYPE2);
CREATE INDEX X_MRREL_SAB ON MRREL(SAB);
""")

english_sources = set([line.split("\t")[0]
                for line in open("data/vocab_doc.txt").readlines()
                if "\t" in line and line.split("\t")[3] == "ENG"])
rela_abbr = {line.split("\t")[0].strip(): line.split("\t")[1].strip()
                for line in open("data/rela_doc.txt").readlines()
                if "\t" in line}
rela_abbr = {i:j for i,j in rela_abbr.items() if i!="" and j!=""}


# 1. MRDEF
valid_cui = set()
for line in tqdm(open("data/MRDEF.RRF").readlines()):
    line = line.strip().split("|")
    cui = line[0]
    sab = line[4]
    defi = line[5]
    if sab in english_sources:
        cursor.execute('INSERT INTO MRDEF (CUI, SAB, DEF) VALUES (?,?,?)', (cui, sab, defi))
        valid_cui.add(cui)

# 2. MRCONSO
cui_to_name = {}
def find_common_term(terms):
    terms_lower = [term.lower().strip() for term in terms]
    common_term = None
    min_error = float('inf')
    for i, term in enumerate(terms_lower):
        error_sum = 0
        for j, other_term in enumerate(terms_lower):
            if i != j:
                error_sum += term != other_term
        if error_sum < min_error:
            min_error = error_sum
            common_term = terms[i]
    return common_term

for line in tqdm(open("data/MRCONSO.RRF").readlines()):
    line = line.strip().split("|")
    cui = line[0]
    sab = line[11]
    string = line[14]
    if sab in english_sources and cui in valid_cui:
        cursor.execute('INSERT INTO MRCONSO (CUI, SAB, STR) VALUES (?,?,?)', (cui, sab, string))
        cursor.execute('INSERT INTO MRCONSOEM (CUI, SAB, STR) VALUES (?,?,?)', (cui, sab, string))
        if cui not in cui_to_name:
            cui_to_name[cui] = []
        cui_to_name[cui].append(string)
cui_to_name = {cui: find_common_term(name) for cui, name in tqdm(cui_to_name.items())}


# 3. MRREL
for line in tqdm(open("data/MRREL.RRF").readlines()):
    line = line.strip().split("|")
    cui1 = line[0]
    stype1 = line[2]
    cui2 = line[4]
    stype2 = line[6]
    rela = line[7]
    sab = line[10]
    if sab in english_sources and rela != "" \
            and cui1 in cui_to_name and cui2 in cui_to_name and rela in rela_abbr \
            and cui1 in valid_cui and cui2 in valid_cui \
            and cui_to_name[cui1] != cui_to_name[cui2]:
        cursor.execute('INSERT INTO MRREL (CUI1, STYPE1, STR1, CUI2, STYPE2, STR2, RELA, SAB) VALUES (?,?,?,?,?,?,?,?)', (cui1, stype1, cui_to_name[cui1], cui2, stype2, cui_to_name[cui2], rela_abbr[rela], sab))

db.commit()
db.close()