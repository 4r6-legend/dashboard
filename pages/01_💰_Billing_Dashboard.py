import streamlit as st
import pandas as pd
import altair as alt
import boto3
from datetime import datetime, timedelta

from dashboard_lib import get_file_slug, require_display_name

st.set_page_config(
    page_title="AWS Billing Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.switch_page("Login.py")

st.markdown(
    """
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarNav"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

_ORG = require_display_name()
_SLUG = get_file_slug()

st.title(f"💰 {_ORG} - AWS Billing Dashboard")

aws_access_key_id = st.secrets["aws"]["aws_access_key_id"]
aws_secret_access_key = st.secrets["aws"]["aws_secret_access_key"]
aws_region = st.secrets["aws"]["aws_region"]


def _ce_client():
    return boto3.client(
        "ce",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
    )


col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Data Inicial", value=datetime.now() - timedelta(days=30))
with col2:
    end_date = st.date_input("Data Final", value=datetime.now())


@st.cache_data
def get_aws_cost_data(start_date, end_date):
    ce = _ce_client()
    response = ce.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
        },
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    rows = []
    for result in response["ResultsByTime"]:
        date = result["TimePeriod"]["Start"]
        for group in result["Groups"]:
            service = group["Keys"][0]
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            rows.append(
                {
                    "date": pd.to_datetime(date),
                    "service": service,
                    "cost": amount,
                }
            )

    return pd.DataFrame(rows)


@st.cache_data
def get_aws_cost_by_region(start_date, end_date):
    ce = _ce_client()
    response = ce.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
        },
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "REGION"}],
    )

    rows = []
    for result in response["ResultsByTime"]:
        date = result["TimePeriod"]["Start"]
        for group in result["Groups"]:
            region = group["Keys"][0] or "global / sem região"
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            rows.append(
                {
                    "date": pd.to_datetime(date),
                    "region": region,
                    "cost": amount,
                }
            )

    return pd.DataFrame(rows)


@st.cache_data
def get_service_breakdown_by_usage(
    start_date, end_date, service_name: str, breakdown_dimension: str
):
    """Custo diário filtrado a um SERVICE, agrupado por USAGE_TYPE ou USAGE_TYPE_GROUP."""
    if breakdown_dimension not in ("USAGE_TYPE", "USAGE_TYPE_GROUP"):
        raise ValueError("breakdown_dimension inválido")

    ce = _ce_client()
    response = ce.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
        },
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        Filter={"Dimensions": {"Key": "SERVICE", "Values": [service_name]}},
        GroupBy=[{"Type": "DIMENSION", "Key": breakdown_dimension}],
    )

    rows = []
    for result in response["ResultsByTime"]:
        date = result["TimePeriod"]["Start"]
        for group in result["Groups"]:
            usage_key = group["Keys"][0] or "(vazio)"
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            rows.append(
                {
                    "date": pd.to_datetime(date),
                    "usage_key": usage_key,
                    "cost": amount,
                }
            )

    out = pd.DataFrame(rows)
    if not out.empty:
        out["breakdown_dimension"] = breakdown_dimension
    return out


df = get_aws_cost_data(start_date, end_date)

if df.empty:
    st.warning("Nenhum dado encontrado.")
    st.stop()

total_cost = df["cost"].sum()
by_service = df.groupby("service")["cost"].sum()
top_service = by_service.idxmax()
top_service_cost = by_service.max()
mean_daily = df.groupby("date")["cost"].sum().mean()

st.subheader(f"🔢 Visão Geral de Custos - {_ORG}")
col1, col2, col3, col4 = st.columns(4)
col1.metric("💸 Custo Total (período)", f"${total_cost:,.2f}")
col2.metric("🔥 Serviço Mais Caro", top_service)
col3.metric("💰 Valor do Serviço Top", f"${top_service_cost:,.2f}")
col4.metric("📅 Média Diária (total)", f"${mean_daily:,.2f}")

df_total_by_service = df.groupby("service", as_index=False)["cost"].sum()

tab_resumo, tab_servicos, tab_regioes = st.tabs(
    ["Resumo executivo", "Por serviço", "Por região"]
)

with tab_resumo:
    st.caption(
        "Tendência do gasto agregado, composição dos principais serviços e participação percentual no período."
    )

    df_daily = (
        df.groupby("date", as_index=False)["cost"]
        .sum()
        .sort_values("date")
        .reset_index(drop=True)
    )
    df_daily["ma7"] = df_daily["cost"].rolling(7, min_periods=1).mean()

    base_x = alt.X("date:T", title="Data")
    layer_total = (
        alt.Chart(df_daily)
        .mark_line(strokeWidth=2, color="#1E88E5")
        .encode(
            base_x,
            y=alt.Y("cost:Q", title="Custo (USD)"),
            tooltip=[
                alt.Tooltip("date:T", title="Dia"),
                alt.Tooltip("cost:Q", title="Total do dia", format="$,.2f"),
            ],
        )
    )
    layer_ma = (
        alt.Chart(df_daily)
        .mark_line(strokeDash=[6, 4], color="#FB8C00")
        .encode(
            base_x,
            y=alt.Y("ma7:Q", title="Custo (USD)"),
            tooltip=[
                alt.Tooltip("date:T", title="Dia"),
                alt.Tooltip("ma7:Q", title="Média móvel 7d", format="$,.2f"),
            ],
        )
    )
    st.subheader("📉 Custo total diário e média móvel (7 dias)")
    st.altair_chart(
        (layer_total + layer_ma)
        .resolve_scale(y="shared")
        .properties(height=320)
        .interactive(),
        use_container_width=True,
    )
    st.caption("Linha sólida: soma de todos os serviços no dia. Tracejada: média móvel de 7 dias desse total.")

    top_n_stack = st.slider("Quantidade de serviços no empilhado (demais viram “Outros”)", 4, 15, 8, 1)
    svc_rank = by_service.sort_values(ascending=False)
    top_svc = svc_rank.head(top_n_stack).index.tolist()
    df_stack = df.copy()
    df_stack["svc_bucket"] = df_stack["service"].apply(
        lambda s: s if s in top_svc else "Outros"
    )
    df_stack = df_stack.groupby(["date", "svc_bucket"], as_index=False)["cost"].sum()

    st.subheader("🧱 Composição diária (área empilhada)")
    stacked = (
        alt.Chart(df_stack)
        .mark_area()
        .encode(
            x=alt.X("date:T", title="Data"),
            y=alt.Y("cost:Q", title="Custo (USD)", stack="zero"),
            color=alt.Color(
                "svc_bucket:N",
                title="Serviço",
                scale=alt.Scale(scheme="tableau20"),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Dia"),
                alt.Tooltip("svc_bucket:N", title="Serviço"),
                alt.Tooltip("cost:Q", title="Custo", format="$,.2f"),
            ],
        )
        .properties(height=380)
        .interactive()
    )
    st.altair_chart(stacked, use_container_width=True)

    pie_n = min(12, len(df_total_by_service))
    df_pie = df_total_by_service.nlargest(pie_n, "cost").copy()
    rest = total_cost - df_pie["cost"].sum()
    if rest > 0.0001:
        df_pie = pd.concat(
            [df_pie, pd.DataFrame([{"service": "Demais serviços", "cost": rest}])],
            ignore_index=True,
        )

    st.subheader("🍩 Participação no custo total (top serviços)")
    donut = (
        alt.Chart(df_pie)
        .mark_arc(innerRadius=64)
        .encode(
            theta=alt.Theta("cost:Q", stack=True),
            color=alt.Color("service:N", title="Serviço", scale=alt.Scale(scheme="set2")),
            tooltip=[
                alt.Tooltip("service:N", title="Serviço"),
                alt.Tooltip("cost:Q", title="Custo", format="$,.2f"),
                alt.Tooltip(
                    "pct:Q",
                    title="% do período",
                    format=".1f",
                ),
            ],
        )
        .transform_calculate(pct="(datum.cost / {}) * 100".format(total_cost))
        .properties(height=400)
    )
    st.altair_chart(donut, use_container_width=True)

with tab_servicos:
    unique_services = sorted(df["service"].unique())
    other_idx = next(
        (i for i, s in enumerate(unique_services) if "other" in s.lower()),
        0,
    )

    with st.expander(
        "🔬 Detalhar um serviço (ex.: **EC2 - Other** → o que entra em “Other”)",
        expanded=False,
    ):
        st.caption(
            "Na AWS, **EC2 - Other** (e linhas parecidas) somam itens que não entram em “instância sob demanda” "
            "— em geral **EBS**, **Elastic IP**, **NAT Gateway**, **Load Balancer** ligado ao EC2, **tráfego**, etc. "
            "Aqui o Cost Explorer quebra pelo **tipo de uso** (código de cobrança), que é o nível mais fino disponível "
            "sem ativar relatório CUR ou custo por recurso."
        )
        detail_service = st.selectbox(
            "Serviço para detalhar (nome exatamente como na AWS):",
            unique_services,
            index=other_idx,
        )
        breakdown_dim = st.radio(
            "Agrupamento",
            ("USAGE_TYPE", "USAGE_TYPE_GROUP"),
            horizontal=True,
            format_func=lambda x: "Tipo de uso (detalhado)"
            if x == "USAGE_TYPE"
            else "Grupo de tipo de uso (resumido)",
        )

        df_usage = get_service_breakdown_by_usage(
            start_date, end_date, detail_service, breakdown_dim
        )
        if df_usage.empty:
            st.info("Sem linhas de custo para esse serviço no período (ou filtro sem retorno).")
        else:
            df_usage_tot = (
                df_usage.groupby("usage_key", as_index=False)["cost"]
                .sum()
                .sort_values("cost", ascending=False)
            )
            st.subheader(f"📊 Total no período — {detail_service}")
            usage_bar = (
                alt.Chart(df_usage_tot.head(40))
                .mark_bar()
                .encode(
                    x=alt.X("cost:Q", title="Custo (USD)"),
                    y=alt.Y(
                        "usage_key:N",
                        sort="-x",
                        title="Usage type" if breakdown_dim == "USAGE_TYPE" else "Grupo",
                    ),
                    tooltip=[
                        alt.Tooltip("usage_key:N", title="Chave"),
                        alt.Tooltip("cost:Q", title="Custo", format="$,.2f"),
                    ],
                )
                .properties(
                    height=min(720, 22 * max(10, min(len(df_usage_tot), 40))),
                )
            )
            st.altair_chart(usage_bar, use_container_width=True)
            if len(df_usage_tot) > 40:
                st.caption("Gráfico limitado aos 40 maiores; tabela abaixo lista todos.")

            top_keys = df_usage_tot.head(8)["usage_key"].tolist()
            df_lines = df_usage[df_usage["usage_key"].isin(top_keys)]
            st.subheader("📈 Evolução diária (top 8 linhas)")
            usage_lines = (
                alt.Chart(df_lines)
                .mark_line()
                .encode(
                    x=alt.X("date:T", title="Data"),
                    y=alt.Y("cost:Q", title="Custo (USD)"),
                    color=alt.Color("usage_key:N", title="Tipo de uso"),
                    tooltip=["date:T", "usage_key:N", "cost:Q"],
                )
                .properties(height=340)
                .interactive()
            )
            st.altair_chart(usage_lines, use_container_width=True)

            st.dataframe(df_usage_tot, use_container_width=True, height=320)
            st.download_button(
                label=f"📥 Download CSV — {detail_service} ({breakdown_dim})",
                data=df_usage_tot.to_csv(index=False).encode("utf-8"),
                file_name=f"{_SLUG}_billing_service_usage_breakdown.csv",
                mime="text/csv",
                key=f"dl_usage_{detail_service}_{breakdown_dim}",
            )

    selected_services = st.multiselect(
        "🧩 Filtrar Serviços para o gráfico de linha:",
        unique_services,
        default=unique_services[:5],
    )
    df_filtered = df[df["service"].isin(selected_services)]

    st.subheader(f"📈 Custos Diários por Serviço ({_ORG})")
    line_chart = (
        alt.Chart(df_filtered)
        .mark_line()
        .encode(
            x=alt.X("date:T", title="Data"),
            y=alt.Y("cost:Q", title="Custo (USD)"),
            color=alt.Color("service:N", title="Serviço"),
            tooltip=["date:T", "service:N", "cost:Q"],
        )
        .properties(height=400)
        .interactive()
    )
    st.altair_chart(line_chart, use_container_width=True)

    st.subheader(f"📊 Total por Serviço ({_ORG})")
    bar_chart = (
        alt.Chart(df_total_by_service)
        .mark_bar()
        .encode(
            x=alt.X("cost:Q", title="Custo Total"),
            y=alt.Y("service:N", sort="-x", title="Serviço"),
            color=alt.Color("service:N", legend=None),
            tooltip=["service:N", "cost:Q"],
        )
        .properties(height=500)
    )
    st.altair_chart(bar_chart, use_container_width=True)

    st.subheader(f"📋 Tabela de Custos por Serviço ({_ORG})")
    st.dataframe(
        df_total_by_service.sort_values("cost", ascending=False),
        use_container_width=True,
    )

    st.download_button(
        label="📥 Download CSV (por serviço)",
        data=df_total_by_service.to_csv(index=False).encode("utf-8"),
        file_name=f"{_SLUG}_aws_billing_by_service.csv",
        mime="text/csv",
    )

with tab_regioes:
    df_reg = get_aws_cost_by_region(start_date, end_date)
    if df_reg.empty:
        st.info("Sem dados de custo por região para o período.")
    else:
        df_reg_total = df_reg.groupby("region", as_index=False)["cost"].sum()
        st.subheader("🌍 Total por região (período)")
        reg_chart = (
            alt.Chart(df_reg_total)
            .mark_bar()
            .encode(
                x=alt.X("cost:Q", title="Custo Total (USD)"),
                y=alt.Y("region:N", sort="-x", title="Região"),
                color=alt.Color("region:N", legend=None),
                tooltip=[
                    alt.Tooltip("region:N", title="Região"),
                    alt.Tooltip("cost:Q", title="Custo", format="$,.2f"),
                ],
            )
            .properties(height=min(520, 28 * max(8, len(df_reg_total))))
        )
        st.altair_chart(reg_chart, use_container_width=True)

        st.subheader("📈 Evolução diária por região (top 6 no período)")
        top_regs = (
            df_reg.groupby("region")["cost"]
            .sum()
            .nlargest(6)
            .index.tolist()
        )
        df_reg_top = df_reg[df_reg["region"].isin(top_regs)]
        reg_lines = (
            alt.Chart(df_reg_top)
            .mark_line()
            .encode(
                x=alt.X("date:T", title="Data"),
                y=alt.Y("cost:Q", title="Custo (USD)"),
                color=alt.Color("region:N", title="Região"),
                tooltip=["date:T", "region:N", "cost:Q"],
            )
            .properties(height=360)
            .interactive()
        )
        st.altair_chart(reg_lines, use_container_width=True)

        st.dataframe(
            df_reg_total.sort_values("cost", ascending=False),
            use_container_width=True,
        )
        st.download_button(
            label="📥 Download CSV (por região)",
            data=df_reg_total.to_csv(index=False).encode("utf-8"),
            file_name=f"{_SLUG}_aws_billing_by_region.csv",
            mime="text/csv",
        )

st.markdown("Desenvolvido por [Cognitivo](https://cognitivo.ai) - Cognitivo AI 💙")
