"""Playbooks e mensagens demonstrativas baseadas em regras, sem uso de LLM."""
from __future__ import annotations

from datetime import datetime

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
        "categoria": category,
        "objetivo":p["objetivo"],"estrategia":p["estrategia"],"kpi":p["kpi"],
        "versao_a":variant_a,"versao_b":variant_b,"status":"Rascunho para revisão humana",
        "observacao":"Demonstração sintética. Não há envio automático nem geração de textos por LLM."}


def brief_to_markdown(brief: dict) -> str:
    """Briefing legível para revisão de Marketing, em vez de um JSON técnico."""
    return f"""# Briefing de campanha — {brief['marca']}

**Público:** {brief['segmento']} | **Canal:** {brief['canal']}  
**Contatos elegíveis:** {brief['clientes_elegiveis']} (dados fictícios)  
**Categoria:** {brief.get('categoria', 'Não informada')}

## Objetivo
{brief['objetivo']}

## Estratégia proposta
{brief['estrategia']}

## Versão A — rascunho
{brief['versao_a']}

## Versão B — rascunho
{brief['versao_b']}

## Indicador principal
{brief['kpi']}

## Cuidados antes de utilizar
- Revisar a linguagem, as ofertas e o tom de voz.
- Confirmar consentimentos válidos, preferências e opção de descadastro.
- Não disparar mensagens sem aprovação humana.
- Não interpretar um teste com poucos contatos como evidência estatística.

*Protótipo com dados sintéticos; mensagens baseadas em modelos de texto, sem envio automático.*
"""


def prompt_for_external_llm(brief: dict, avg_days: float, avg_spend: float) -> str:
    """Prompt do Modo Marketing: briefing legível, somente dados agregados."""
    quantidade = int(brief['clientes_elegiveis'])
    categoria = brief.get('categoria', 'não informada')
    canal = brief['canal']
    corpo = (
        "Para cada versão, apresente Assunto, Prévia do e-mail (preheader), Corpo "
        "(até 120 palavras) e CTA. Inclua uma opção clara de descadastro nos textos."
        if canal == 'E-mail'
        else "Para cada versão, apresente uma mensagem para WhatsApp (até 70 palavras), CTA "
             "e orientação para interromper contatos a pedido da pessoa. Não use links inventados."
    )
    if quantidade == 0:
        regra_amostra = (
            "ATENÇÃO: não existem contatos elegíveis neste segmento e canal. "
            "Não escreva mensagens prontas para envio. Explique a ausência de público "
            "e proponha ações de diagnóstico e obtenção legítima de consentimento."
        )
    elif quantidade < 30:
        regra_amostra = (
            f"ATENÇÃO: a audiência tem apenas {quantidade} contato(s). Trate A/B como "
            "duas alternativas editoriais, não como um teste capaz de gerar conclusões "
            "estatísticas confiáveis. Não prometa resultado ou conversão."
        )
    else:
        regra_amostra = (
            "Trate a comparação A/B como hipótese a validar; não declare vencedor "
            "nem significância estatística sem dados de experimento."
        )
    return f"""Você é estrategista sênior de CRM, Marketing de Relacionamento e Retenção.
Sua missão é transformar um resumo de clientes FICTÍCIOS em um briefing de campanha
claro, criativo e profissional, pronto para revisão de uma equipe de Marketing.

CONTEXTO DO NEGÓCIO (dados sintéticos e agregados):
- Marca fictícia: {brief['marca']}
- Segmento RFM: {brief['segmento']}
- Canal: {canal}
- Contatos elegíveis segundo os consentimentos simulados: {quantidade}
- Categoria mais comum de interesse: {categoria}
- Recência média das compras: {avg_days:.1f} dias
- Valor médio comprado nos últimos 365 dias: R$ {avg_spend:.2f}
- Objetivo sugerido: {brief['objetivo']}
- Estratégia de referência: {brief['estrategia']}
- KPI principal: {brief['kpi']}

ENTREGA SOLICITADA — somente MODO MARKETING:
Escreva em português brasileiro, usando títulos e parágrafos legíveis.
NÃO use JSON, blocos de código, tabelas técnicas nem nomes de campos de programação.
Organize a resposta exatamente nesta sequência:

1. RESUMO DA CAMPANHA: nome criativo, objetivo e proposta de valor.
2. PÚBLICO E INSIGHT: perfil do segmento, necessidade e oportunidade; diferencie
   observações dos dados de hipóteses sobre o comportamento.
3. HIPÓTESE DE TESTE: o que diferencia as variantes A e B e o que se quer aprender.
4. ESTRATÉGIA: abordagem de comunicação, tom de voz e direcionamento criativo.
5. VARIANTE A: mensagem completa para o canal selecionado.
6. VARIANTE B: mensagem completa, com abordagem realmente diferente da A.
7. MÉTRICAS: KPI principal, até três métricas secundárias e forma de acompanhar.
8. CHECKLIST PARA APROVAÇÃO: consistência de marca, consentimento, descadastro,
   riscos de promessas exageradas, revisão humana e cuidados com o público.

REGRAS PARA AS MENSAGENS:
- {corpo}
- Não invente descontos, cupons, benefícios, produtos, preços, estoques,
  frete grátis, links, prazos, resultados alcançados ou urgência artificial.
- Não solicite nem inclua dados pessoais; não personalize com nomes reais.
- Não execute nenhuma campanha nem simule que algo já foi enviado.
- Use uma linguagem natural, útil e respeitosa, apropriada para CRM de varejo.
- Apresente conteúdo pronto para revisão, mas NÃO afirme que está aprovado.
- {regra_amostra}

Responda exclusivamente no formato de briefing de Marketing solicitado.
"""
