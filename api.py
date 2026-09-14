"""API FastAPI — endpoint obrigatório GET /oportunidades?min_score=70."""
from fastapi import FastAPI, Query

from storage import carregar_resultados

app = FastAPI(title="Radar de Editais — Engevia")


@app.get("/oportunidades")
def listar_oportunidades(min_score: float = Query(0, ge=0, le=100)):
    """Lista contratações com score de aderência >= min_score, ordenadas do maior pro menor."""
    resultados = carregar_resultados()
    filtrados = [r for r in resultados if r["score"]["valor_final"] >= min_score]
    filtrados.sort(key=lambda r: r["score"]["valor_final"], reverse=True)
    return {"total": len(filtrados), "oportunidades": filtrados}


@app.get("/")
def raiz():
    return {"status": "ok", "endpoint_principal": "/oportunidades?min_score=70"}