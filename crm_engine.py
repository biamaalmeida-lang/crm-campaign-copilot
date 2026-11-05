"""Regras transparentes de CRM e RFM (sem IA/API externa).

Todas as datas e os limites de segmentação são informados e podem ser auditados.
"""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
import csv
import re
import unicodedata

import pandas as pd

CUSTOMER_REQUIRED = {"id_cliente", "consentimento_email", "consentimento_whatsapp"}
ORDER_REQUIRED = {"id_pedido", "id_cliente", "data_pedido", "receita_liquida_brl", "status_pedido"}
SEGMENT_ORDER = ["VIP", "Fiel", "Potencial", "Novo", "Em risco", "Inativo"]
SEGMENT_COLORS = {
    "VIP": "#3dd6b3", "Fiel": "#60a5fa", "Potencial": "#c4a8ff",
    "Novo": "#8dd1ff", "Em risco": "#fbbf64", "Inativo": "#fc8181",
}


def read_table(file) -> pd.DataFrame:
    """Importa CSV (vírgula/semicolon, UTF-8 ou latin-1) ou Excel."""
    if isinstance(file, (str, Path)):
        file = Path(file)
        name = file.name.lower()
        payload = file.read_bytes()
    else:
        name = getattr(file, "name", "data.csv").lower()
        if hasattr(file, "seek"):
            file.seek(0)
        payload = file.read()
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    if name.endswith(".xlsx"):
        return pd.read_excel(BytesIO(payload), engine="openpyxl")
    if not name.endswith(".csv"):
        raise ValueError("Envie um arquivo .csv ou .xlsx.")
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            result = pd.read_csv(BytesIO(payload), sep=None, engine="python", encoding=encoding)
            if len(result.columns) == 1 and b";" in payload:
                result = pd.read_csv(BytesIO(payload), sep=";", encoding=encoding)
            return result
        except UnicodeError:
            continue
        except (pd.errors.ParserError, csv.Error):
            continue
    raise ValueError("Não foi possível identificar o formato do CSV. Use UTF-8 com vírgula ou ponto e vírgula.")


def _norm(x: object) -> str:
    value = unicodedata.normalize("NFD", str(x).strip().lower())
    return "".join(ch for ch in value if unicodedata.category(ch) != "Mn")


def _money(series: pd.Series) -> pd.Series:
    """Aceita 1234.56, 1234,56, 1.234,56 e formatos numéricos."""
    def as_number(v):
        if pd.isna(v):
            return float("nan")
        if isinstance(v, (int, float)):
            return float(v)
        s = re.sub(r"[^0-9,.\-]", "", str(v).strip())
        if not s:
            return float("nan")
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return float("nan")
    return series.map(as_number)


def prepare_data(customers: pd.DataFrame, orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validação com mensagens claras; não altera os dados de entrada."""
    c = customers.copy()
    o = orders.copy()
    c.columns = [str(col).strip().lower() for col in c.columns]
    o.columns = [str(col).strip().lower() for col in o.columns]
    missing_c, missing_o = CUSTOMER_REQUIRED - set(c.columns), ORDER_REQUIRED - set(o.columns)
    if missing_c:
        raise ValueError(f"Base de clientes: faltam as colunas {', '.join(sorted(missing_c))}.")
    if missing_o:
        raise ValueError(f"Base de pedidos: faltam as colunas {', '.join(sorted(missing_o))}.")
    if c.empty or o.empty:
        raise ValueError("As planilhas de clientes e pedidos não podem estar vazias.")
    for df, col in ((c, "id_cliente"), (o, "id_cliente"), (o, "id_pedido")):
        df[col] = df[col].astype("string").str.strip()
        if df[col].isna().any() or df[col].eq("").any():
            raise ValueError(f"Há valores vazios na coluna {col}.")
    if c.id_cliente.duplicated().any():
        raise ValueError("Há IDs de clientes repetidos. Cada cliente deve aparecer apenas uma vez.")
    if o.id_pedido.duplicated().any():
        raise ValueError("Há IDs de pedido repetidos.")
    without_customer = set(o.id_cliente) - set(c.id_cliente)
    if without_customer:
        sample = ", ".join(sorted(without_customer)[:4])
        raise ValueError(f"Pedidos com id_cliente ausente da base de clientes: {sample}.")
    o["data_pedido"] = pd.to_datetime(o["data_pedido"], errors="coerce", dayfirst=False).dt.normalize()
    if o.data_pedido.isna().any():
        raise ValueError("Existem datas de pedido inválidas. Prefira AAAA-MM-DD.")
    o["receita_liquida_brl"] = _money(o["receita_liquida_brl"])
    if o.receita_liquida_brl.isna().any():
        raise ValueError("Existem valores inválidos em receita_liquida_brl.")
    if (o.receita_liquida_brl < 0).any():
        raise ValueError("A receita líquida não pode ser negativa nesta versão demonstrativa.")
    o["status_normalizado"] = o.status_pedido.map(_norm)
    accepted_statuses = {"concluido", "cancelado", "devolvido", "pendente", "em andamento"}
    if not set(o.status_normalizado).issubset(accepted_statuses):
        unknown = set(o.status_normalizado) - accepted_statuses
        raise ValueError(f"Status de pedido não reconhecido: {', '.join(sorted(unknown))}.")
    for col in ["categoria_preferida", "canal_preferido", "canal_aquisicao", "cidade", "uf", "email_teste"]:
        if col not in c:
            c[col] = "Não informado"
    for col in ["categoria", "canal_venda"]:
        if col not in o:
            o[col] = "Não informado"
    for col in ["consentimento_email", "consentimento_whatsapp"]:
        c[col] = c[col].fillna("Não").astype(str).str.strip()
    return c, o


def r_score(days: float) -> int:
    if pd.isna(days): return 0
    if days <= 14: return 5
    if days <= 45: return 4
    if days <= 90: return 3
    if days <= 180: return 2
    return 1


def f_score(n: int) -> int:
    if n <= 0: return 0
    if n >= 6: return 5
    if n >= 4: return 4
    return int(n)


def m_score(amount: float) -> int:
    if amount <= 0: return 0
    if amount >= 1600: return 5
    if amount >= 900: return 4
    if amount >= 450: return 3
    if amount >= 200: return 2
    return 1


def choose_segment(recency: float, r: int, f: int, m: int) -> str:
    """Regras didáticas para a base demo; transparentes, não um modelo preditivo."""
    if pd.isna(recency) or recency >= 160:
        return "Inativo"
    if r >= 4 and f >= 5 and m >= 4:
        return "VIP"
    if r >= 4 and f >= 3:
        return "Fiel"
    if r >= 4 and f <= 2 and recency <= 30:
        return "Novo"
    if r >= 3 and f >= 2:
        return "Potencial"
    return "Em risco"


def calculate_rfm(customers: pd.DataFrame, orders: pd.DataFrame,
                  as_of: date | datetime | str = date(2026, 11, 4)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Considera pedidos concluídos até a data de referência.

    Recência: última compra concluída (histórico até a referência).
    Frequência e monetário: janela inclusiva [referência-365 dias, referência].
    """
    ref = pd.Timestamp(as_of).normalize()
    o = orders.loc[(orders.status_normalizado == "concluido") &
                   (orders.data_pedido <= ref)].copy()
    last = o.groupby("id_cliente").data_pedido.max().rename("ultima_compra")
    rolling = o.loc[o.data_pedido >= ref - pd.Timedelta(days=365)].copy()
    agg = rolling.groupby("id_cliente").agg(
        frequencia_365d=("id_pedido", "count"),
        valor_365d_brl=("receita_liquida_brl", "sum"),
    )
    result = customers.merge(last, left_on="id_cliente", right_index=True, how="left")
    result = result.merge(agg, left_on="id_cliente", right_index=True, how="left")
    result["frequencia_365d"] = result.frequencia_365d.fillna(0).astype(int)
    result["valor_365d_brl"] = result.valor_365d_brl.fillna(0).round(2)
    result["recencia_dias"] = (ref - result.ultima_compra).dt.days.astype("Int64")
    result["score_r"] = result.recencia_dias.map(r_score).astype(int)
    result["score_f"] = result.frequencia_365d.map(f_score).astype(int)
    result["score_m"] = result.valor_365d_brl.map(m_score).astype(int)
    result["segmento"] = result.apply(lambda x: choose_segment(x.recencia_dias, x.score_r, x.score_f, x.score_m),axis=1)
    result["ticket_medio_365d"] = (result.valor_365d_brl / result.frequencia_365d.replace(0,float("nan"))).fillna(0).round(2)
    return result, rolling


def eligible_audience(rfm: pd.DataFrame, segment: str, channel: str, respect_preference: bool = False) -> pd.DataFrame:
    base = rfm.loc[rfm.segmento == segment].copy()
    consent_col = {"E-mail": "consentimento_email", "WhatsApp": "consentimento_whatsapp"}[channel]
    base = base.loc[base[consent_col].map(_norm).isin(["sim", "true", "1"])].copy()
    if respect_preference:
        normal_channel = _norm(channel)
        base = base.loc[base.canal_preferido.map(_norm).isin([normal_channel, "sem preferencia"])].copy()
    return base


def compare_reference(rfm: pd.DataFrame, reference: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    """Compara segmentação com um gabarito, sem utilizá-lo no cálculo."""
    required = {"id_cliente", "segmento"}
    if not required.issubset(reference.columns):
        raise ValueError("Gabarito necessita das colunas id_cliente e segmento.")
    merged = rfm[["id_cliente", "segmento"]].merge(
        reference[["id_cliente", "segmento"]].rename(columns={"segmento":"segmento_referencia"}), on="id_cliente", how="inner"
    )
    if merged.empty: raise ValueError("Nenhum cliente do gabarito está presente na análise.")
    merged["concordancia"] = merged.segmento == merged.segmento_referencia
    return float(merged.concordancia.mean()), merged


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    safe = df.copy()
    # Mitigação de injeção de fórmulas caso o CSV seja aberto no Excel.
    for column in safe.select_dtypes(include=["object", "string"]).columns:
        safe[column] = safe[column].map(lambda v: "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v)
    return safe.to_csv(index=False).encode("utf-8-sig")
