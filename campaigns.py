"""Playbooks e mensagens demonstrativas baseadas em regras, sem uso de LLM."""
from __future__ import annotations

from datetime import datetime
import json

PLAYBOOKS = {
    "VIP": {"objetivo": "Reconhecimento e fidelização de clientes de alto valor", "kpi": "Taxa de recompra e receita por cliente", "estrategia": "Acesso antecipado a novidades e benefícios aprovados."},
    "Fiel": {"objetivo": "Estimular recorrência sem depender de descontos", "kpi": "Frequência de compras e retenção", "estrategia": "Curadoria personalizada de novidades da categoria preferida."},
    "Potencial": {"objetivo": "Aumentar frequência de compra", "kpi": "Taxa de segunda/terceira compra", "estrategia": "Campanha contextual de descoberta de produtos complementares."},
    "Novo": {"objetivo": "Aumentar a chance de segunda compra", "kpi": "Conversão para segunda compra em 60 dias", "estrategia": "Boas-vindas com dicas de uso e seleção de produtos."},
    "Em risco": {"objetivo": "Reduzir abandono e recuperar relacionamento", "kpi": "Taxa de reativação em 30 dias", "estrategia": "Contato relevante e não invasivo com novidades e escuta."},
    "Inativo": {"objetivo": "Recuperar clientes com consentimento válido", "kpi": "Taxa de reativação em 60 dias", "estrategia": "Campanha de retorno com comunicação respeitosa e opção de descadastro."},
}


def build_messages(segment: str, channel: str, category: str, brand: str = "Nossa Loja") -> tuple[str,str]:
    """Duas propostas A/B pré-definidas, não geradas por IA."""
    if segment not in PLAYBOOKS:
        raise ValueError("Segmento não identificado.")
    brand = brand.strip()[:60] or "Nossa Loja"
    category = category.strip()[:60] or "seus acessórios favoritos"
    intro = {
        "VIP": (f"Novidades selecionadas em {category} para quem acompanha a {brand} de perto.",
                f"Sua preferência por {category} merece atenção: conheça nossa curadoria."),
        "Fiel": (f"Tem novidade em {category}! Veja o que preparamos para você.",
                 f"Sua próxima descoberta em {category} pode estar aqui."),
        "Potencial": (f"Que tal explorar mais opções de {category}?", f"Uma seleção de {category} para descobrir novidades."),
        "Novo": (f"Boas-vindas à {brand}! Conheça novidades em {category}.",
                 f"Obrigado por sua primeira compra. Descubra ideias de {category}."),
        "Em risco": (f"Faz um tempo! Se tiver interesse, veja novidades em {category}.",
                    f"Gostaríamos de ouvir você. Veja o que mudou em {category}."),
        "Inativo": (f"Temos novidades em {category} caso queira voltar a conhecer a {brand}.",
                    f"Sentimos sua falta! Explore novidades em {category}, sem compromisso."),
    }[segment]
    if channel == "E-mail":
        return tuple(f"Assunto: {line}\n\nOlá!\n\n{line}\n\nConheça as novidades em nosso site.\n\nSe não quiser receber mensagens, utilize a opção de descadastro.\nEquipe {brand}" for line in intro)
    return tuple(f"Olá! {line} Confira nosso catálogo, se desejar. Para não receber novas mensagens, informe sua preferência. — {brand}" for line in intro)


def campaign_brief(segment: str, channel: str, target_count: int, category: str, brand: str) -> dict:
    p=PLAYBOOKS[segment]
    variant_a, variant_b = build_messages(segment,channel,category,brand)
    return {"criado_em": datetime.now().isoformat(timespec="seconds"), "marca": brand,
        "segmento": segment,"canal": channel,"clientes_elegiveis": target_count,
        "objetivo":p["objetivo"],"estrategia":p["estrategia"],"kpi":p["kpi"],
        "versao_a":variant_a,"versao_b":variant_b,"status":"Rascunho para revisão humana",
        "observacao":"Demonstração sintética. Não há envio automático nem geração de textos por LLM."}


def prompt_for_external_llm(brief: dict, avg_days: float, avg_spend: float) -> str:
    """Somente resumos agregados: nunca encaminha dados pessoais ao modelo externo."""
    info = {"marca_ficticia":brief["marca"], "segmento":brief["segmento"],
            "canal":brief["canal"], "publico_elegivel":brief["clientes_elegiveis"],
            "recencia_media_dias":round(avg_days,1), "valor_medio_365d_brl":round(avg_spend,2),
            "objetivo":brief["objetivo"], "kpi":brief["kpi"]}
    return (
        "Você é uma pessoa estrategista de CRM. Crie uma campanha A/B a partir de DADOS "
        "SINTÉTICOS E AGREGADOS. Não invente descontos, disponibilidade, prazos, "
        "resultados, benefícios ou garantias. Não use pressão, urgência artificial ou dados pessoais.\n\n"
        "DADOS (JSON):\n"+json.dumps(info,ensure_ascii=False,indent=2)+"\n\n"
        "Produza exatamente um JSON com: objetivo, hipotese, audiencia, assunto_a, corpo_a, "
        "assunto_b, corpo_b, CTA, KPI_principal, KPIs_secundarios, riscos_e_revisao. "
        "Use português brasileiro, até 100 palavras por mensagem. "
        "Não envie mensagens: o conteúdo será revisado por um humano. "
        "Considere boas práticas de consentimento e descadastro."
    )
