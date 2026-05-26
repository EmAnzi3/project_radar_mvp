# Procedura aggiornamento mensile Project Radar MVP

Questa procedura serve per aggiornare mensilmente il radar OpenCUP + ANAC e verificare che il sito sia coerente dopo la rigenerazione.

## Quando lanciare la Action

Lanciare la GitHub Action solo se:

- OpenCUP ha pubblicato un nuovo dataset mensile;
- sono stati aggiornati gli asset ANAC nella release `anac-raw-2026`;
- è stato modificato codice di pipeline e serve rigenerare gli output;
- serve un test completo della pipeline.

Non lanciare la Action se i dati sorgente sono invariati.

## Pre-check locale

```powershell
cd "C:\Users\anzillotti\OneDrive - CGT Edilizia S.p.a\Documenti\GitHub\project_radar_mvp"
git status --short
git pull
