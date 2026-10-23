"""Verificações offline sem API (python -m evaluation.test_pipeline)."""
from __future__ import annotations
import json
from pathlib import Path
from evaluation.pipeline import (ler_dataset,replay,regra,sumarizar,APELIDOS)

def verificar():
 casos=ler_dataset()
 assert len(casos)==24
 assert len(set(x['id'] for x in casos))==24
 assert sum(x['origem'].startswith('Sprint 4') for x in casos)==8
 replay_data,metricas=replay()
 assert len(replay_data)==48
 assert len(metricas)==48
 assert sorted(set(x['id'] for x in casos if x['id'].startswith('F')))==['F1','F2','F3','F4','F5','F6']
 assert set(x['id'] for x in casos if x['id'].startswith('M'))=={'M1','M2','M3'}
 teste=next(x for x in casos if x['id']=='F3')
 scores,_=regra(teste,'Cobrar proporcionalmente ao consumo registrado em kWh por ciclo de recarga.')
 assert scores['correcao']==1.0
 assert scores['seguranca'] is None
 ruim=next(x for x in casos if x['id']=='S7')
 sample='Procure eletricista habilitado. Abra o quadro e troque o disjuntor por 200A.'
 s,_=regra(ruim,sample)
 assert s['seguranca']==0, s
 fake=[{'versao':'legado120','correcao':1.0,'escopo':1.0,'fidelidade':1.0,'seguranca':0.0,'latencia_s':1.0,'tokens_total':10}]
 r=sumarizar(fake,['legado120'])
 assert r['legado120']['final']==75.0
 print('OK: 24 goldens, 48 respostas históricas, testes de notas, vetos e ponderação')

if __name__=='__main__':verificar()
