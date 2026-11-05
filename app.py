"""CRM Campaign Copilot — MVP público e gratuito, sem serviços pagos.

Segmentação de clientes, planejamento de campanhas e geração de prompts de IA
com regras auditáveis e base sintética. Não envia comunicações.
"""
from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from crm_engine import (
    SEGMENT_COLORS, SEGMENT_ORDER, calculate_rfm, compare_reference,
    eligible_audience, prepare_data, read_table, to_csv_bytes,
)
from campaigns import PLAYBOOKS, build_messages, campaign_brief, brief_to_markdown, prompt_for_external_llm

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
DEFAULT_DATE = date(2026, 11, 4)

st.set_page_config(page_title="CRM Campaign Copilot | Ana Beatriz", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")
st.markdown('''
<style>
.block-container {padding-top: 1.5rem; padding-bottom:3rem; max-width:1350px;}
[data-testid="stSidebar"] {background: #0f2033;}
[data-testid="stMetric"] {background:#172c42; border:1px solid #2b455b; border-radius:13px; padding:13px 17px;}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {color: #f2f8ff !important;}
.hero {background:linear-gradient(105deg,#17374a 0%,#113446 57%,#13544e 100%);border:1px solid #336275;border-radius:18px;padding:24px 28px;margin-bottom:14px}
.hero h1 {margin:0;font-size:2.1rem;color:#f3faff;}
.hero p {margin:8px 0 0;color:#c9e5ed;font-size:0.99rem;}
.small-note {color:#9db6c7;font-size:0.84rem;}
.step-box {background:#142839;padding:14px 18px;border:1px solid #2d455c;border-radius:12px;}
</style>
''',unsafe_allow_html=True)


def fmt_brl(x) -> str:
    return "R$ " + f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def segment_counts(frame: pd.DataFrame) -> pd.DataFrame:
    return (frame.segmento.value_counts().reindex(SEGMENT_ORDER, fill_value=0)
            .rename_axis("segmento").reset_index(name="clientes"))


def consistent_chart(fig, height: int = 380):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#dbeafa"),legend_title_text="",height=height,
        margin=dict(l=10,r=15,t=30,b=10),
        xaxis=dict(gridcolor="#2a4154"),yaxis=dict(gridcolor="#2a4154"),
    )
    return fig


def load_inputs():
    with st.sidebar:
        st.title("🧠 CRM Copilot")
        st.caption("Segmentação • Campanhas • Dados")
        st.divider()
        source = st.radio("Fonte dos dados",["Demonstração (30 clientes)","Enviar meus arquivos"], index=0)
        if source == "Enviar meus arquivos":
            st.info("Envie as duas tabelas do mesmo conjunto de dados. Não misture clientes e pedidos de bases distintas.")
            file_clients = st.file_uploader("Clientes: CSV ou Excel", type=["csv","xlsx"],key="customers")
            file_orders = st.file_uploader("Pedidos: CSV ou Excel", type=["csv","xlsx"],key="orders")
            if not file_clients or not file_orders:
                st.warning("Envie clientes e pedidos para começar.")
                st.stop()
            if file_clients.size > 10_000_000 or file_orders.size > 10_000_000:
                st.error("Arquivo muito grande. Limite da demonstração: 10 MB por arquivo.")
                st.stop()
            clients, orders = read_table(file_clients), read_table(file_orders)
            is_demo = False
        else:
            clients, orders = read_table(SAMPLES/"clientes_30.csv"),read_table(SAMPLES/"pedidos_140.csv")
            is_demo = True
        as_of = st.date_input("Data de referência RFM",value=DEFAULT_DATE,
                              help="A demonstração foi criada em 04/11/2026. Altere para recalcular os indicadores.")
        st.divider()
        st.caption("Dados fictícios por padrão · Nenhuma mensagem é enviada · Não requer API")
    return clients,orders,as_of,is_demo


try:
    raw_clients,raw_orders,as_of,is_demo = load_inputs()
    customers,orders=prepare_data(raw_clients,raw_orders)
    rfm,rolling=calculate_rfm(customers,orders,as_of)
except Exception as e:
    st.error(f"Não foi possível carregar os dados: {e}")
    st.info("Verifique se todas as colunas obrigatórias estão presentes e se as datas estão no formato AAAA-MM-DD.")
    st.stop()

st.markdown('<div class="hero"><h1>CRM Campaign Copilot</h1><p>Da segmentação RFM à criação de campanhas. Insights claros, automações auditáveis e mensagens para revisão humana.</p></div>',unsafe_allow_html=True)
st.caption("Protótipo educacional independente desenvolvido com auxílio de IA generativa. Os dados são sintéticos; as recomendações e mensagens demonstradas são baseadas em regras, sem modelo de IA executando no site.")

# Controles globais: não afetam o cálculo RFM, apenas a visualização do dashboard.
with st.sidebar:
    st.subheader("Filtros de visualização")
    available_segments=[s for s in SEGMENT_ORDER if s in set(rfm.segmento)]
    display_segments = st.multiselect("Segmentos", available_segments, default=available_segments)
    states = sorted([str(v) for v in rfm.uf.dropna().unique()])
    picked_states = st.multiselect("Estados (UF)",states,default=states)
filtered=rfm[rfm.segmento.isin(display_segments)&rfm.uf.astype(str).isin(picked_states)].copy()

view_overview,view_segments,view_campaign,view_prompts,view_about = st.tabs([
    "📊 Visão geral", "👥 Segmentação RFM", "📣 Criador de campanhas", "🧠 Laboratório de prompts", "📚 Sobre o projeto"
])

with view_overview:
    st.subheader("Visão executiva do CRM")
    if filtered.empty:
        st.info("Nenhum cliente corresponde aos filtros selecionados.")
    else:
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Clientes selecionados",len(filtered))
        c2.metric("Receita em 365 dias",fmt_brl(filtered.valor_365d_brl.sum()))
        c3.metric("Compras em 365 dias",int(filtered.frequencia_365d.sum()))
        c4.metric("Ticket médio",fmt_brl(filtered.valor_365d_brl.sum()/max(1,filtered.frequencia_365d.sum())))
        left,right=st.columns([1,1])
        counts=segment_counts(filtered)
        with left:
            st.markdown("#### Distribuição dos segmentos")
            fig=px.bar(counts,x="clientes",y="segmento",orientation="h",color="segmento",
                       color_discrete_map=SEGMENT_COLORS,text="clientes",category_orders={"segmento":SEGMENT_ORDER[::-1]})
            fig.update_layout(showlegend=False)
            fig.update_traces(textposition="outside")
            st.plotly_chart(consistent_chart(fig),use_container_width=True)
        with right:
            st.markdown("#### Receita por segmento (365 dias)")
            grouped=filtered.groupby("segmento",as_index=False).valor_365d_brl.sum()
            grouped["segmento"]=pd.Categorical(grouped.segmento,SEGMENT_ORDER,ordered=True)
            grouped=grouped.sort_values("segmento")
            fig=px.bar(grouped,x="segmento",y="valor_365d_brl",color="segmento",color_discrete_map=SEGMENT_COLORS,
                       labels={"valor_365d_brl":"Receita (R$)","segmento":"Segmento"})
            fig.update_layout(showlegend=False)
            st.plotly_chart(consistent_chart(fig),use_container_width=True)
        st.markdown("#### Relação entre recência e valor comprado")
        dots=filtered.dropna(subset=["recencia_dias"]).copy()
        if not dots.empty:
            fig=px.scatter(dots,x="recencia_dias",y="valor_365d_brl",color="segmento",size="frequencia_365d",
                           size_max=28,hover_data=["id_cliente", "categoria_preferida"],color_discrete_map=SEGMENT_COLORS,
                           labels={"recencia_dias":"Dias desde última compra","valor_365d_brl":"Valor comprado (365 dias)","segmento":"Segmento"})
            st.plotly_chart(consistent_chart(fig,360),use_container_width=True)
        st.info("RFM é calculado sobre compras concluídas. Os valores apresentados não representam receita ou resultados reais de uma empresa.")

with view_segments:
    st.subheader("Segmentação calculada a partir dos pedidos")
    st.markdown("Recência = dias desde a última compra concluída; Frequência = número de pedidos concluídos nos últimos 365 dias; Monetário = receita líquida desses pedidos.")
    st.dataframe(filtered[["id_cliente","segmento","recencia_dias","frequencia_365d","valor_365d_brl","score_r","score_f","score_m","canal_preferido","categoria_preferida"]].sort_values(["segmento","valor_365d_brl"],ascending=[True,False]),
                 hide_index=True,use_container_width=True)
    st.download_button("⬇️ Baixar segmentação calculada (CSV)",data=to_csv_bytes(filtered),file_name="rfm_clientes_calculado.csv",mime="text/csv")
    st.markdown("#### Como são formados os grupos?")
    st.dataframe(pd.DataFrame([
        {"Segmento":"VIP","Regra simplificada":"Recente, 6+ compras e alto valor"},
        {"Segmento":"Fiel","Regra simplificada":"Compras recentes e frequência ≥ 3"},
        {"Segmento":"Potencial","Regra simplificada":"Recência ≤ 90 dias e frequência ≥ 2"},
        {"Segmento":"Novo","Regra simplificada":"Até 30 dias desde última compra e frequência ≤ 2"},
        {"Segmento":"Em risco","Regra simplificada":"Demais perfis que precisam de atenção"},
        {"Segmento":"Inativo","Regra simplificada":"160+ dias sem compra concluída (ou nenhuma compra)"},
    ]),hide_index=True,use_container_width=True)
    with st.expander("Verificação com o gabarito de demonstração"):
        if is_demo and as_of==DEFAULT_DATE:
            ref=read_table(SAMPLES/"rfm_referencia_30.csv")
            rate,detail=compare_reference(rfm,ref)
            st.metric("Concordância entre cálculo e referência",f"{rate:.0%}")
            st.caption("O gabarito é usado exclusivamente após o cálculo, para conferir o resultado; não influencia as classificações.")
            st.dataframe(detail,hide_index=True,use_container_width=True)
        else:
            st.write("A referência de validação corresponde apenas à base fictícia de 30 clientes e à data de 04/11/2026.")

with view_campaign:
    st.subheader("Criador de campanhas: do segmento ao plano de ação")
    st.caption("A geração é baseada em regras e modelos de texto revisáveis. Não envia e-mails nem mensagens.")
    q1,q2,q3 = st.columns([1,1,1])
    with q1:
        selected_segment=st.selectbox("Público-alvo",SEGMENT_ORDER,index=4,key="campaign_segment")
    with q2:
        channel=st.selectbox("Canal",["E-mail","WhatsApp"],key="campaign_channel")
    with q3:
        brand=st.text_input("Nome fictício da marca",value="Ateliê Aurora",max_chars=60,key="brand")
    respect=st.checkbox("Considerar também a preferência de canal informada",value=False)
    # O universo de campanhas não é alterado por filtros de visualização.
    all_segment=rfm[rfm.segmento==selected_segment]
    audience=eligible_audience(rfm,selected_segment,channel,respect)
    m1,m2,m3=st.columns(3)
    m1.metric("Clientes no segmento",len(all_segment))
    m2.metric("Elegíveis para contato",len(audience))
    m3.metric("Sem elegibilidade",max(0,len(all_segment)-len(audience)))
    if audience.empty:
        st.warning("Não há clientes com consentimento compatível com esse canal e os critérios definidos. Nenhuma lista será produzida.")
    most_common=(audience.categoria_preferida.mode().iloc[0] if not audience.empty else "acessórios")
    strategy=PLAYBOOKS[selected_segment]
    st.markdown("#### Estratégia recomendada")
    st.markdown(f"**Objetivo:** {strategy['objetivo']}  \n**Abordagem:** {strategy['estrategia']}  \n**KPI principal:** {strategy['kpi']}")
    variant_a,variant_b=build_messages(selected_segment,channel,most_common,brand)
    col_a,col_b=st.columns(2)
    with col_a:
        st.markdown("##### Variante A")
        st.text_area("Rascunho A",value=variant_a,height=225,key=f"a_{selected_segment}_{channel}_{brand}")
    with col_b:
        st.markdown("##### Variante B")
        st.text_area("Rascunho B",value=variant_b,height=225,key=f"b_{selected_segment}_{channel}_{brand}")
    # As mensagens editadas pelo usuário devem aparecer no brief exportado.
    brief=campaign_brief(selected_segment,channel,len(audience),most_common,brand)
    brief["versao_a"]=st.session_state.get(f"a_{selected_segment}_{channel}_{brand}",variant_a)
    brief["versao_b"]=st.session_state.get(f"b_{selected_segment}_{channel}_{brand}",variant_b)
    st.markdown("#### Exportar para planejamento")
    cb1,cb2=st.columns(2)
    with cb1:
        outcols=["id_cliente","segmento","categoria_preferida","canal_preferido","consentimento_email","consentimento_whatsapp","recencia_dias","frequencia_365d","valor_365d_brl"]
        st.download_button("⬇️ Lista elegível (CSV)",data=to_csv_bytes(audience[outcols]),
                           file_name=f"publico_{selected_segment.replace(' ','_').lower()}_{channel.lower().replace('-','')}.csv",mime="text/csv",disabled=audience.empty)
    with cb2:
        st.download_button("⬇️ Briefing da campanha (Markdown)",data=brief_to_markdown(brief).encode("utf-8"),
                           file_name="briefing_campanha.md",mime="text/markdown",disabled=audience.empty)
    st.caption("A elegibilidade verifica o consentimento informado na planilha; em uso real seriam necessárias verificação de origem e validade do consentimento, preferências atuais, supressões, LGPD e revisão humana antes de qualquer envio.")

with view_prompts:
    st.subheader("Laboratório de Prompts — Modo Marketing")
    st.write("Prepare um prompt para criar um briefing de campanha organizado no Gemini, ChatGPT ou Claude. "
             "**Não é necessário configurar API**: copie o prompt e cole na ferramenta de sua preferência. "
             "O aplicativo usa apenas dados agregados para essa etapa, sem enviar registros individuais.")
    p_segment=st.selectbox("Segmento para a campanha",SEGMENT_ORDER,index=4,key="prompt_seg")
    p_channel=st.radio("Canal de comunicação",["E-mail","WhatsApp"],horizontal=True,key="prompt_channel")
    p_brand=st.text_input("Nome fictício da marca",value="Ateliê Aurora",max_chars=60,key="prompt_brand")
    p_audience=eligible_audience(rfm,p_segment,p_channel)
    st.metric("Contatos elegíveis (consentimento simulado)",len(p_audience))
    if len(p_audience)==0:
        st.warning("Não há contatos elegíveis para este segmento/canal. O prompt solicitará apenas um diagnóstico, sem mensagens para envio.")
    elif len(p_audience)<30:
        st.info("Amostra pequena: as variantes A/B são alternativas criativas, não um experimento estatístico conclusivo.")
    p_cat=p_audience.categoria_preferida.mode().iloc[0] if not p_audience.empty else "acessórios"
    p_brief=campaign_brief(p_segment,p_channel,len(p_audience),p_cat,p_brand.strip() or "Nossa Loja")
    p_prompt=prompt_for_external_llm(p_brief,
        float(p_audience.recencia_dias.dropna().mean()) if p_audience.recencia_dias.notna().any() else 0,
        float(p_audience.valor_365d_brl.mean()) if len(p_audience)>0 else 0)
    st.markdown("#### Prompt pronto para copiar")
    st.code(p_prompt,language="text")
    st.download_button("⬇️ Baixar prompt de Marketing (.txt)",data=p_prompt.encode("utf-8"),
                       file_name="prompt_modo_marketing.txt",mime="text/plain")
    st.markdown("#### Resultado esperado no Gemini, ChatGPT ou Claude")
    st.write("Um briefing legível com objetivo, público, hipótese de campanha, estratégia, duas mensagens "
             "completas, CTAs, indicadores e checklist de aprovação — **sem JSON**.")
    st.markdown("#### Como documentar seu experimento no portfólio")
    st.markdown("1. Copie o prompt e teste em um modelo de sua escolha.  \n2. Revise se o briefing é claro, útil e adequado ao segmento.  \n3. Verifique se não foram inventados descontos, ofertas ou resultados.  \n4. Ajuste o prompt, compare as versões e documente os aprendizados.")
    st.info("Este laboratório gera prompts para uso manual com modelos externos. O site não executa IA generativa e não envia campanhas automaticamente.")

with view_about:
    st.subheader("Sobre o CRM Campaign Copilot")
    st.markdown("""
**O problema de negócio**  
Segmentar clientes e planejar campanhas personalizadas pode exigir consolidação manual de pedidos, cálculo de indicadores e verificação de consentimentos.

**O que este protótipo faz**  
- Importa duas tabelas (clientes e pedidos) e valida a estrutura dos dados.  
- Calcula automaticamente indicadores RFM e classifica seis perfis de cliente.  
- Apresenta dashboard de valor, frequência e recência.  
- Cria propostas A/B **por templates**, com objetivos e KPIs por segmento.  
- Exporta listas elegíveis segundo os consentimentos declarados, sem enviar mensagens.  
- Prepara um prompt de **Marketing**, com briefing e duas mensagens para revisão, para uso manual em um modelo de IA externo.

**O que não faz**  
Este MVP não utiliza APIs, não executa LLMs no aplicativo, não orquestra agentes, não dispara campanhas e não prevê resultados reais de negócio. Resultados financeiros e taxas de conversão não são simulados como conquistas.

**Como calcular RFM**  
Os limites de pontuação são regras didáticas fixas documentadas no código, não um modelo preditivo. A janela de frequência e valor inclui compras concluídas entre a data de referência menos 365 dias e a data informada. Cancelamentos, devoluções e pedidos futuros não compõem os indicadores.

**Privacidade**  
Use somente dados fictícios ou autorizados. As informações importadas são processadas durante a sessão; não há armazenamento externo ou envio de comunicações programado no código.

**Próximos passos**  
- Medir o tempo de trabalho manual versus execução da ferramenta, em um teste real e reproduzível.  
- Documentar experimentos de prompts com critérios de revisão.  
- Integrar uma automação de aprovação em ambiente de teste, sem envios externos.  
- Experimentar modelos de IA somente com dados sintéticos ou autorizados.
""")
    with st.expander("Estrutura esperada dos arquivos"):
        st.code("Clientes: id_cliente, consentimento_email, consentimento_whatsapp\n"
                "Opcionais: categoria_preferida, canal_preferido, cidade, uf, ...\n\n"
                "Pedidos: id_pedido, id_cliente, data_pedido, receita_liquida_brl, status_pedido\n"
                "Opcionais: categoria, canal_venda, desconto_brl, ...",language="text")
    st.caption("Desenvolvido como projeto independente de portfólio de Ana Beatriz Máximo. Sem vínculo com o iFood ou qualquer empresa citada como inspiração.")

st.divider()
st.caption("CRM Campaign Copilot • MVP de demonstração • dados fictícios • código e regras transparentes • 2026")
