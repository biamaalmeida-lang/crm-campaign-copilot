# CRM Campaign Copilot 🧠

**Plataforma demonstrativa de segmentação de clientes e planejamento de campanhas.**

Projeto independente de portfólio de **Ana Beatriz Máximo**, inspirado em problemas comuns de CRM e varejo. Não utiliza dados reais e não possui vínculo com o iFood.

## O que o aplicativo faz

- Importa duas planilhas CSV/XLSX com clientes e pedidos.
- Calcula RFM (**Recência, Frequência, Monetário**) automaticamente a partir de compras concluídas.
- Separa seis segmentos (VIP, Fiel, Potencial, Novo, Em risco, Inativo).
- Exibe um dashboard com filtros, receita, frequência e comportamento de compra.
- Recomenda um objetivo e KPI por segmento e produz duas versões de mensagem por templates.
- Verifica consentimento por canal antes de exportar a lista de campanha.
- Gera um **prompt estruturado** para testes manuais no ChatGPT, Claude ou Gemini.

### Importante: transparência sobre IA

O aplicativo foi desenvolvido com auxílio de IA, mas **não executa um modelo generativo, agente ou API em tempo real**. A segmentação e as sugestões são baseadas em regras explícitas. O Laboratório de Prompts fornece material que pode ser copiado para um LLM externo com os dados **agregados** da campanha; o app não o envia automaticamente. Também não dispara e-mails/WhatsApp.

## Teste rápido

Na abertura, a base padrão carrega **30 clientes fictícios e 140 pedidos fictícios**. Selecione as abas **Visão geral**, **Segmentação RFM**, **Criador de campanhas**, **Laboratório de prompts** e **Sobre o projeto**.

A data de referência inicial é **04/11/2026**, correspondente ao gabarito `samples/rfm_referencia_30.csv`. Na base de demonstração, são calculados cinco clientes por segmento. O gabarito só é usado para **verificação posterior**, nunca para atribuir segmentos.

## Como executar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publicação no Streamlit Community Cloud

1. No GitHub, crie um **novo repositório** (por exemplo `crm-campaign-copilot`).
2. Envie **todos** os arquivos e pastas deste projeto, mantendo `app.py` e `requirements.txt` na raiz e os arquivos de demonstração dentro de `samples/`.
3. Acesse https://share.streamlit.io/ e selecione **Create app → I have an app**.
4. Indique o repositório, a branch `main` e o arquivo principal `app.py`.
5. Clique em **Deploy**. **Não é necessário configurar chave de API.**

## Estrutura

```text
crm-campaign-copilot/
├── app.py
├── crm_engine.py
├── campaigns.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
├── samples/
│   ├── clientes_30.csv
│   ├── pedidos_140.csv
│   └── rfm_referencia_30.csv
└── tests/
    └── test_crm_engine.py
```

## Esquema mínimo dos arquivos

**Clientes:** `id_cliente`, `consentimento_email`, `consentimento_whatsapp`.

**Pedidos:** `id_pedido`, `id_cliente`, `data_pedido` (AAAA-MM-DD), `receita_liquida_brl`, `status_pedido` (Concluído, Cancelado, Devolvido, Pendente ou Em andamento).

Campos adicionais como `categoria_preferida`, `canal_preferido`, `uf` e `cidade` são recomendados e podem estar ausentes. O programa valida dados inconsistentes, IDs repetidos e pedidos sem cliente cadastrado.

## Regras RFM

**Data padrão de análise:** 04/11/2026. Recência usa a última compra concluída até essa data. Frequência e Monetário consideram compras concluídas entre a data-base menos **365 dias** e a data-base (inclusive). Não entram compras canceladas ou devolvidas.

| Score | Recência (dias) | Frequência (pedidos) | Monetário (R$) |
|---|---|---|---|
| 5 | 0–14 | ≥6 | ≥1.600 |
| 4 | 15–45 | 4–5 | 900–1.599,99 |
| 3 | 46–90 | 3 | 450–899,99 |
| 2 | 91–180 | 2 | 200–449,99 |
| 1 | >180 | 1 | <200 e >0 |
| 0 | Sem compras | 0 | 0 |

**Segmentos:** VIP (R≥4, F≥5 e M≥4); Fiel (R≥4 e F≥3); Novo (R≥4, F≤2 e recência≤30); Potencial (R≥3 e F≥2); Inativo (recência≥160 ou sem compras); Em risco (demais perfis). A implementação verifica as regras em ordem, com Inativo antes dos outros segmentos. São limites didáticos, que devem ser calibrados em uma base real.

## Validação realizada

Com o dataset sintético, o cálculo reproduz **30 de 30** classificações e os respectivos escores e indicadores do arquivo de referência quando usada a data **04/11/2026**. Este é um teste de **consistência do algoritmo com o gabarito sintético**, não uma avaliação da precisão de um modelo de IA.

## Segurança e limitações

- Todos os clientes e e-mails do exemplo são fictícios (`example.com`).
- O app não possui integração de envio nem salva históricos em um serviço externo.
- O consentimento mostrado é simulado; em bases reais, é necessário cumprir LGPD e políticas de opt-in, opt-out, finalidade e retenção.
- As sugestões de campanhas não garantem conversões ou receita. As duas variantes A/B são propostas para testar, não resultados medidos.
- Não divulgue dados pessoais reais em repositório público.

## Próximas evoluções

- Registrar tempo gasto em uma tarefa manual e na ferramenta, com método reproduzível.
- Testar prompts manualmente e documentar versões, erros e avaliação humana.
- Criar fluxo de aprovação no Make/n8n usando apenas dados sintéticos, sem disparo real.
