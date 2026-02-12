# Homework 01
Agent analyzující SQL dotaz.

Pokud uživatel požádá o analýzu SQL dotazu, použije se `analyze_sql` tool.

Tento tool ověří, zda se jedná o jednoduchý dotaz - pro účely tohoto cvičení prostý SELECT maximálně s WHERE podmínkou - a pokud ano, doporučí indexovat sloupce použité ve WHERE podmínce.

Pokud se jedná o složitější dotaz, zavolá se expert LLM.

## Spuštění skriptu
```bash
uv run tools.py
```

## Ukázka komunikace
Viz soubor `output.txt`
