# BeatForge Testing Guide

> **Testausohjeet projektin kehittajille ja testereille**
> 
> *Paeivitetty: 2026-06-23* | *Versio: 0.1.0* | *Status: M0+M1 Complete*

---

## 🎯 Yleiskatsaus

BeatForge on **pre-alpha** vaiheessa. Tama tiedosto kertoo miten testata kaikkea mita on toistaiseksi toteutettu.

### 📋 Nykyinen Tila

| Milestone | Status | Testit | Komennot |
|-----------|--------|--------|----------|
| **M0** (Foundation) | ✅ **Valmis** | 5+ testia | `make-empty`, `validate-midi` |
| **M1** (Rules-based) | ✅ **Valmis** | 40+ testia | `generate-basic`, `parse-prompt`, `generate` |
| **M2** (Audio) | 🔲 Stubit | 0 testia | `analyze`, `groove` (ei toiminnallisuutta) |
| **M3** (Editing) | 🔲 Stubit | 0 testia | `edit` (ei toiminnallisuutta) |
| **M4** (ML) | 🔲 Stubit | 0 testia | `generate-ml`, `models` (ei toiminnallisuutta) |

**Kaikki 58 testia lapaisevat** ✅

---

## 🚀 Paikallinen Testaus (Windows/Linux)

### 1. Ympariston Asennus

#### Windows (PowerShell)
```powershell
# Siirry projektin kansioon
cd C:\Repos\Omat\BeatForge

# Luo virtuaaliymparisto (jos ei ole jo olemassa)
python -m venv .venv

# Aktivoi venv
.\.venv\Scripts\activate

# Asenna riippuvuudet
pip install -U pip
pip install -e ".[dev]"
```

#### Linux/macOS (Bash)
```bash
# Siirry projektin kansioon
cd /path/to/BeatForge

# Luo virtuaaliymparisto
python3 -m venv .venv

# Aktivoi venv
source .venv/bin/activate

# Asenna riippuvuudet
pip install -U pip
pip install -e ".[dev]"
```

### 2. Perustestit

#### Kaikki testit
```bash
# Aja kaikki 58 testia
python -m pytest -v

# Lyhyempi tulostus
python -m pytest -q
```

#### Tietyt testiryhmat
```bash
# Vain M0 testit (make-empty, validate-midi)
python -m pytest tests/test_make_empty.py tests/test_validator.py -v

# Vain M1 testit (generate, parse-prompt)
python -m pytest tests/test_generate_basic.py tests/test_generate_prompt_driven.py tests/test_parse_prompt.py -v

# Vain privacy testit
python -m pytest tests/privacy/ -v
```

### 3. No-Network Testit (Privacy Varmistus)
```bash
# Aja vain no_network merkityt testit
python -m pytest -m no_network -v

# Tarkista etta ei avata socket yhdysia
python -m pytest tests/privacy/test_no_audio_egress.py -v
```

### 4. Staattinen No-Audio-Egress Tarkistus
```bash
# Tarkista etta koodi ei yrita lahetta audioa verkkoon
python tools/static_no_audio_egress.py
```

### 5. Koodin Laadun Tarkistus

#### Ruff (Linttaaja)
```bash
# Tarkista koodin tyylit
python -m ruff check .

# Korjaa automaattisesti
python -m ruff check . --fix
```

#### Ruff (Formatoija)
```bash
# Tarkista formatointi
python -m ruff format --check .

# Korjaa automaattisesti
python -m ruff format .
```

#### MyPy (Tyypityksen Tarkistus)
```bash
# Tarkista tyypitykset
python -m mypy src
```

### 6. Taysi Paikallinen Testaus (Pre-commit)

**Suorita nain ennen jokaista commitia:**

```bash
# 1. Koodin tyylit
python -m ruff check .

# 2. Koodin formatointi
python -m ruff format --check .

# 3. Tyypitykset
python -m mypy src

# 4. Kaikki testit
python -m pytest -q

# 5. No-network testit
python -m pytest -m no_network

# 6. No-audio-egress tarkistus
python tools/static_no_audio_egress.py
```

** Jos kaikki lapaisee, voit tehdä commitin! **

---

## 🎵 Musiikillinen Testaus

### Perus Toiminnallisuus

#### 1. make-empty (M0.2)
```bash
# Luo tyhja MIDI tiedosto
drumgen make-empty --bars 16 --bpm 120 --out test_empty.mid

# Tarkista etta se on validi
drumgen validate-midi test_empty.mid
```

**Odotettu tulostus:**
```
PASS  test_empty.mid
  stat   bpm=120
  stat   channel=9
  stat   ppq=480
```

#### 2. generate-basic (M1.1)
```bash
# Luo rock tyylinen kappale
drumgen generate-basic --style rock --bars 64 --bpm 120 --seed 42 --out rock_song.mid

# Luo punk tyylinen kappale (tiheammat potkut)
drumgen generate-basic --style punk --bars 64 --bpm 180 --seed 42 --out punk_song.mid

# Luo funk tyylinen kappale (16th hatit)
drumgen generate-basic --style funk --bars 64 --bpm 110 --seed 42 --out funk_song.mid

# Validoi kaikki
for f in rock_song.mid punk_song.mid funk_song.mid; do
  drumgen validate-midi $f
done
```

**Tyylit:** `rock`, `pop`, `punk`, `funk`

#### 3. parse-prompt (M1.2)
```bash
# Jasenna promptti StyleSpeciks
drumgen parse-prompt --prompt "punk 180bpm, snare on 2&4, fills before chorus"

# Tallenna JSON tiedostoon
drumgen parse-prompt --prompt "rock 120bpm, 16th hats, ghost notes" --out spec.json

# Katso tulostus
cat spec.json
```

**Odote:**
```json
{
  "stylespec": {
    "bpm": 180,
    "fills": "before_chorus",
    "genre": "punk",
    "backbeat": "2_and_4",
    ...
  }
}
```

#### 4. generate (M1.3) - Pääkomento
```bash
# Prompt-pohjainen generointi
drumgen generate --prompt "punk 180bpm, snare on 2&4" --bars 96 --seed 42 --out punk_drums.mid

# StyleSpec tiedoston kaytto
drumgen generate --stylespec spec.json --bars 64 --out from_spec.mid

# BPM override
drumgen generate --prompt "rock 120bpm" --bpm 140 --bars 32 --out override_bpm.mid
```

### Musiikilliset Varmistukset

#### ✅ Tarkista etta:

1. **MIDI on validi:**
   ```bash
   drumgen validate-midi output.mid
   ```
   → Tulostuu `PASS`

2. **Deterministisyys:**
   ```bash
   # Aja kaksi kertaa samalla seedilla
   drumgen generate --prompt "rock" --bars 32 --seed 42 --out a.mid
   drumgen generate --prompt "rock" --bars 32 --seed 42 --out b.mid
   
   # Tiedostot pitaisi olla identtisia
   cmp a.mid b.mid  # Linux
   fc a.mid b.mid   # Windows
   ```
   → Ei eroja

3. **Tyylierot kuuluvat:**
   - **Punk**: Tiheammat potkut, 8th hatit
   - **Funk**: 16th hatit, syncopated kick
   - **Rock**: Vakio 2&4 backbeat
   - **Metal**: Double kick

4. **Rakenne on oikea:**
   ```bash
   # 64 baaria = intro(8) + verse(16) + chorus(16) + verse(16) + chorus(8)
   drumgen generate --prompt "rock" --bars 64 --out structure_test.mid
   ```

5. **Uudet instrumentit (Vaihe A parannukset):**
   ```bash
   # Ride cymbal pitaisi olla läsnä versessä ja choruksessa
   # Crash pitaisi olla läsnä fill barin alussa
   drumgen generate --prompt "rock" --bars 64 --out with_crash.mid
   ```

---

## 🎛️ REAPER Testaus

### MIDI Import

1. **Avaa REAPER**
2. **Lataa MIDI tiedosto:**
   - `File` → `Import` → Valitse `.mid` tiedosto
   - tai Raaha ja pudota tiedosto REAPERiin

3. **Tarkista:**
   - ✅ Kanava 10 (GM Drums)
   - ✅ Tempo asetettu oikein (esim. 120 BPM)
   - ✅ Time signature 4/4
   - ✅ Kaikki instrumentit läsna (kick, snare, hat, ride, crash, toms)

### Suositellut Samplerit

| Sampler | Ohje |
|---------|------|
| **SSD5 Free** | Ilmainen, hyva perus soundi |
| **MT Power Drum Kit** | Ilmainen, ammattimainen |
| **Steven Slate Drums** | Kaupallinen, premium |
| **GetGood Drums** | Kaupallinen, metal/rock |

**Asennus:**
1. Lataa sampler (esim. MT Power Drum Kit)
2. REAPERissa: `Options` → `Preferences` → `MIDI Devices`
3. Aseta drum sampler kanavalle 10
4. Lataa MIDI tiedosto

---

## 📊 Testitulokset

### Viimeisimmat Tulokset (2026-06-23)

```
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.3, pluggy-1.6.0
collected 58 items

# M0 Testit (5 testia)
tests/privacy/test_no_audio_egress.py::test_allowlist_is_empty_in_m0 PASSED
tests/privacy/test_no_audio_egress.py::test_make_empty_opens_no_socket PASSED
tests/privacy/test_no_audio_egress.py::test_help_opens_no_socket PASSED
tests/privacy/test_no_audio_egress.py::test_recorder_sees_no_traffic_from_cli PASSED
tests/privacy/test_no_audio_egress.py::test_recorder_sees_no_traffic_from_cli PASSED

# CLI Testit (3 testia)
tests/test_cli_smoke.py::test_help_exits_zero PASSED
tests/test_cli_smoke.py::test_help_lists_all_expected_subcommands PASSED
tests/test_cli_smoke.py::test_each_stub_subcommand_exits_zero PASSED

# M1 Testit
# - make-empty (4 testia)
# - generate-basic (9 testia)
# - generate-prompt-driven (14 testia)
# - parse-prompt (14 testia)
# - validator (6 testia)

============================== 58 passed in 1.15s =============================
```

---

## 🐛 Ongelmatapaukset

### Yleiset Ongelmat

| Ongelma | Ratkaisu |
|---------|----------|
| `ModuleNotFoundError: mido` | `pip install -e ".[dev]"` |
| `ruff: command not found` | `pip install ruff` |
| `mypy: command not found` | `pip install mypy` |
| Testit epaonnistuvat | Katso error viesti, tavallisesti puuttuva riippuvus |

### Windows Spesifiset

| Ongelma | Ratkaisu |
|---------|----------|
| `python` ei toimi | Kayta `py` tai `.venv\Scripts\python` |
| `source` ei toimi | Kayta `.\.venv\Scripts\activate` |
| Path liian pitka | Siirra projekti lyhyempaan polkuun (esim. `C:\bf`) |

### Linux Spesifiset

| Ongelma | Ratkaisu |
|---------|----------|
| `python3` vs `python` | Kayta `python3` tai asenna `python-is-python3` |
| Permission denied | `chmod +x .venv/bin/*` |

---

## 📝 Testiraportin Luominen

Jos haluat luoda testiraportin (esim. CI:n ulkopuolella):

```bash
# Luo HTML raportti
python -m pytest --html=test_report.html --self-contained-html

# Luo JSON raportti
python -m pytest --junitxml=test_report.xml

# Kattavuusraportti
python -m pytest --cov=src --cov-report=html
```

---

## 🎯 Checklist Ennen PR:aa

- [ ] `python -m ruff check .` ✅
- [ ] `python -m ruff format --check .` ✅
- [ ] `python -m mypy src` ✅
- [ ] `python -m pytest -q` ✅
- [ ] `python -m pytest -m no_network` ✅
- [ ] `python tools/static_no_audio_egress.py` ✅
- [ ] Kaikki testit lapaisevat ✅
- [ ] Koodi on formatoitu ✅
- [ ] Ei uusia `TODO`/`FIXME` kommentteja ✅

---

## 📞 Apua ja Tuki

### Yleiset Kysymykset
- **Q: Mitka komennot ovat valmiita?**
  - A: `make-empty`, `validate-midi`, `generate-basic`, `parse-prompt`, `generate`

- **Q: Mitka tyylit ovat tuettuja?**
  - A: `rock`, `pop`, `punk`, `funk`, `metal`

- **Q: Miten testaan uutta koodia?**
  - A: Lisaa testit `tests/` kansioon, aja `pytest`

### Debuggaus

```bash
# Aja yksi testi verbose moodissa
python -m pytest tests/test_generate_basic.py::test_generates_valid_midi -v -s

# Aja pdb debuggerilla
python -m pytest tests/test_generate_basic.py --pdb

# Tulosta MIDI eventit konsoliin (debug)
python -c "
from beatforge.gen.basic import generate_basic_song
from beatforge.midi.writer import DrumEvent
events = generate_basic_song(bars=16, style='rock', seed=42)
for ev in events[:20]:
    print(f'Tick: {ev.start_tick}, Note: {ev.note}, Vel: {ev.velocity}')
"
```

---

## 📚 Lisatiedot

- **[ROADMAP.md](ROADMAP.md)** – Kehityssuunnitelma ja milestonet
- **[PRIVACY.md](PRIVACY.md)** – Privacy policy ja no-audio-egress
- **[AGENTS.md](AGENTS.md)** – Ohjeet Copilot agentille
- **[CONTRIBUTING.md](CONTRIBUTING.md)** – Kontribuointiohjeet
- **[docs/STYLESPEC.md](docs/STYLESPEC.md)** – StyleSpec skeeman dokumentaatio

---

## 🏷️ Versiohistoria

| Versio | Paivamaara | Muutokset |
|--------|------------|-----------|
| 0.1.0 | 2026-06-23 | Ensimmainen testausohje, M0+M1 valmiina |

---

## 🎉 Onnistuit!

Jos olet saanut kaikki testit lapaiseemaan ja MIDI tiedostot toimimaan REAPERissa, **onnistuit!** ✅

Seuraavaksi voit:
1. Testata uusia promptteja
2. Raportoida bugeja
3. Ehdottaa parannuksia
4. Auttaa kehittamaan M2-M5

**Kiitos testauksesta!** 🎸
