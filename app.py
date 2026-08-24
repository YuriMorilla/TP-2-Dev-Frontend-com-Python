"""
Dashboard de Visualização de Dados - COVID-19 Brasil
Fonte: Portal Coronavírus Brasil (https://covid.saude.gov.br/)

Instruções de uso:
1. Baixe o arquivo CSV do portal: https://covid.saude.gov.br/
   (botão "Arquivo CSV" na página principal)
2. Coloque o arquivo na mesma pasta que este script
3. Execute: streamlit run app.py

Dependências:
    pip install streamlit pandas matplotlib seaborn altair plotly pydeck
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pydeck as pdk
import os
import warnings

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIGURAÇÃO GERAL DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="COVID-19 Brasil · Dashboard",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    h1 { color: #c0392b; }
    h2 { color: #2c3e50; border-bottom: 2px solid #c0392b; padding-bottom: 4px; }
    .stAlert { border-radius: 8px; }
    .exercise-header {
        background: linear-gradient(90deg, #c0392b 0%, #e74c3c 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 6px;
        margin-bottom: 12px;
        font-size: 1.05rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.title("🦠 Dashboard COVID-19 Brasil")
st.markdown("**Fonte:** Portal Coronavírus Brasil · Ministério da Saúde")
st.markdown("---")


# ─────────────────────────────────────────────
# CARREGAMENTO DOS DADOS
# ─────────────────────────────────────────────
@st.cache_data(show_spinner="Carregando dados…")
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8", low_memory=False)

    # Normaliza nomes de colunas (portal muda eventualmente)
    df.columns = df.columns.str.strip()

    # Conversões numéricas seguras
    num_cols = [
        "casosNovos", "casosAcumulado",
        "obitosNovos", "obitosAcumulado",
        "semanaEpi", "Recuperadosnovos",
        "emAcompanhamentoNovos",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Coordenadas (algumas versões do CSV incluem)
    for col in ["latitude", "longitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ── Sidebar: upload ou caminho ──────────────────
with st.sidebar:
    st.header("📂 Dados")
    uploaded = st.file_uploader(
        "Faça upload do CSV do portal covid.saude.gov.br",
        type=["csv"],
        help="Baixe em https://covid.saude.gov.br/ (botão 'Arquivo CSV')",
    )
    local_path = st.text_input(
        "…ou informe o caminho local do arquivo CSV",
        value="HIST_PAINEL_COVIDBR_2024_Parte1.csv",
    )

    data_source = None
    if uploaded is not None:
        data_source = uploaded
    elif os.path.exists(local_path):
        data_source = local_path

if data_source is None:
    st.info(
        "👆 Faça upload do arquivo CSV do portal Coronavírus Brasil na barra lateral "
        "para carregar as visualizações."
    )
    st.markdown(
        "Acesse **https://covid.saude.gov.br/** → clique em *Arquivo CSV* → "
        "faça o upload aqui."
    )
    st.stop()

df_raw = load_data(data_source)

# ── Subconjuntos úteis ──────────────────────────
# Dados nacionais (regiao == 'Brasil' ou estado nulo)
df_brasil = df_raw[df_raw["regiao"] == "Brasil"].copy()

# Dados estaduais (sem município, linha de estado)
df_estado = df_raw[
    (df_raw["regiao"] != "Brasil") &
    (df_raw["municipio"].isna() | (df_raw["municipio"] == ""))
].copy()

# Dados municipais
df_mun = df_raw[
    df_raw["municipio"].notna() & (df_raw["municipio"] != "")
].copy()

REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
ESTADOS_UF = sorted(df_estado["estado"].dropna().unique().tolist())


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 1 – Importância da Visualização de Dados
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 1 — Importância da Visualização de Dados</div>', unsafe_allow_html=True)

st.markdown("""
### Por que visualizar dados em uma pandemia?

Durante uma pandemia como a COVID-19, a **tomada de decisão rápida e embasada** é literalmente uma questão de vida ou morte. A visualização de dados cumpre papel central nesse processo por três razões fundamentais:

#### 1. Transformar volume em compreensão
O Ministério da Saúde consolidou dezenas de **milhões de registros** de 5 570 municípios ao longo de anos. Sem visualização, esses números são inacessíveis. Um gráfico de linha mostrando curvas de óbitos por semana epidemiológica permite que qualquer gestor identifique em segundos se está diante de um pico, de uma platô ou de queda — algo impossível de perceber numa planilha crua.

#### 2. Comunicar risco para públicos diferentes
- **Gestores de saúde pública** precisam de mapas de calor e heatmaps para alocar respiradores, UTIs e equipes de vacinação onde a pressão é maior.  
- **Epidemiologistas** usam boxplots e séries temporais para detectar anomalias e avaliar o impacto de intervenções (lockdowns, campanha de vacinação).  
- **A população em geral** responde melhor a gráficos simples e narrativos visuais que traduzem risco abstrato em algo concreto — o que aumenta a adesão a medidas de proteção.

#### 3. Monitoramento em tempo real e projeção
Painéis interativos com dados atualizados diariamente permitem:
- Detectar **surtos precoces** em municípios antes de se tornarem crises estaduais;
- Avaliar **taxa de ocupação hospitalar** para acionar planos de contingência;
- Comparar **curvas entre regiões** e inferir o efeito de políticas distintas.

> *"What gets measured gets managed."* — Peter Drucker  
> Em epidemiologia: o que é visualizado com clareza é também o que se consegue controlar.

#### Limitações a ter em mente
Toda visualização carrega escolhas: escala logarítmica vs. linear, média móvel vs. dado bruto, casos confirmados vs. suspeitos. Apresentar essas escolhas de forma transparente é parte da ética da comunicação científica.
""")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 2 – Gráfico de Barras · Casos Novos por Semana · Estado
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 2 — Gráfico de Barras · Casos Novos por Semana Epidemiológica (Estado)</div>', unsafe_allow_html=True)

st.markdown("""
**Estado escolhido: São Paulo (SP)**  
Justificativa: SP é o estado mais populoso do Brasil, concentrou os primeiros casos e óbitos do país, 
e suas curvas funcionam como indicador antecipado do comportamento nacional. Analisar sua evolução 
semanal permite entender os grandes picos da pandemia no Brasil.
""")

uf_escolhido = st.selectbox(
    "Selecione o estado (padrão: SP — exercício 2):",
    options=ESTADOS_UF,
    index=ESTADOS_UF.index("SP") if "SP" in ESTADOS_UF else 0,
    key="ex2_uf",
)

df_ex2 = (
    df_estado[df_estado["estado"] == uf_escolhido]
    .groupby("semanaEpi", as_index=False)["casosNovos"]
    .sum()
    .sort_values("semanaEpi")
)

fig_ex2, ax_ex2 = plt.subplots(figsize=(14, 4))
ax_ex2.bar(df_ex2["semanaEpi"], df_ex2["casosNovos"], color="#e74c3c", alpha=0.85, width=0.7)
ax_ex2.set_xlabel("Semana Epidemiológica")
ax_ex2.set_ylabel("Casos Novos")
ax_ex2.set_title(f"Evolução Semanal de Casos Novos — {uf_escolhido}")
ax_ex2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", ".")))
ax_ex2.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
st.pyplot(fig_ex2)

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 3 – Gráfico de Linha · Óbitos Acumulados · Brasil
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 3 — Gráfico de Linha · Óbitos Acumulados por Semana Epidemiológica · Brasil</div>', unsafe_allow_html=True)

df_ex3 = (
    df_brasil.groupby("semanaEpi", as_index=False)["obitosAcumulado"]
    .max()
    .sort_values("semanaEpi")
)

chart_ex3 = (
    alt.Chart(df_ex3)
    .mark_line(color="#c0392b", strokeWidth=2.5)
    .encode(
        x=alt.X("semanaEpi:Q", title="Semana Epidemiológica"),
        y=alt.Y("obitosAcumulado:Q", title="Óbitos Acumulados",
                axis=alt.Axis(format=",d")),
        tooltip=["semanaEpi", "obitosAcumulado"],
    )
    .properties(
        title="Óbitos Acumulados por COVID-19 — Brasil",
        width="container", height=350,
    )
    .interactive()
)
st.altair_chart(chart_ex3, use_container_width=True)

st.markdown("""
**Como interpretar a curva de óbitos acumulados:**  
- A curva de acumulados é **sempre crescente** ou estável — nunca cai, pois registra o total histórico.  
- **Inclinação acentuada** → período de alta mortalidade (picos de ondas, ex.: P2 em fev-abr/2021).  
- **Inflexão para queda de inclinação** → desaceleração: intervenções (vacinação, lockdown) começam a surtir efeito.  
- **Platô** → mortalidade próxima de zero — fase endêmica ou ausência de novos dados.  
- Comparar o ângulo entre semanas permite estimar a **taxa de mortalidade semanal** sem precisar calcular derivadas explicitamente.
""")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 4 – Gráfico de Área · Casos Acumulados · 3 Estados
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 4 — Gráfico de Área · Casos Acumulados · Comparação entre 3 Estados</div>', unsafe_allow_html=True)

default_states = ["SP", "RJ", "AM"]
estados_ex4 = st.multiselect(
    "Escolha 3 estados para comparar:",
    options=ESTADOS_UF,
    default=[s for s in default_states if s in ESTADOS_UF],
    max_selections=3,
    key="ex4_estados",
)

if len(estados_ex4) < 2:
    st.warning("Selecione ao menos 2 estados.")
else:
    df_ex4 = (
        df_estado[df_estado["estado"].isin(estados_ex4)]
        .groupby(["semanaEpi", "estado"], as_index=False)["casosAcumulado"]
        .max()
        .sort_values("semanaEpi")
    )

    chart_ex4 = (
        alt.Chart(df_ex4)
        .mark_area(opacity=0.55)
        .encode(
            x=alt.X("semanaEpi:Q", title="Semana Epidemiológica"),
            y=alt.Y("casosAcumulado:Q", title="Casos Acumulados",
                    stack=None, axis=alt.Axis(format=",d")),
            color=alt.Color("estado:N", title="Estado"),
            tooltip=["semanaEpi", "estado", "casosAcumulado"],
        )
        .properties(
            title="Casos Acumulados — Comparação entre Estados",
            width="container", height=380,
        )
        .interactive()
    )
    st.altair_chart(chart_ex4, use_container_width=True)

    st.markdown(f"""
**Análise dos estados selecionados ({', '.join(estados_ex4)}):**  
- **SP**: maior volume absoluto — reflexo direto da alta densidade demográfica e de ser hub de transporte internacional.  
- **RJ**: segunda economia do país com alta desigualdade; favelas dificultaram isolamento social, gerando curva íngreme na 1ª onda.  
- **AM**: subnotificação histórica seguida de colapso hospitalar em jan/2021 (crise do oxigênio). Curva revela impacto desproporcional em estados com menor infraestrutura.  
- A comparação em área (sem empilhamento) evidencia **quando cada estado atingiu seu pico relativo** e a velocidade de propagação local.
""")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 5 – Mapa st.map · Casos por Município · Estado
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 5 — Mapa Interativo (st.map) · Casos por Município</div>', unsafe_allow_html=True)

uf_mapa = st.selectbox(
    "Selecione o estado para o mapa municipal:",
    options=ESTADOS_UF,
    index=ESTADOS_UF.index("SP") if "SP" in ESTADOS_UF else 0,
    key="ex5_uf",
)

df_ex5 = df_mun[df_mun["estado"] == uf_mapa].copy()

if "latitude" not in df_ex5.columns or "longitude" not in df_ex5.columns:
    st.warning(
        "O CSV carregado não possui colunas de latitude/longitude por município. "
        "Alguns downloads do portal omitem essas colunas. "
        "Tente o arquivo completo ou versão com coordenadas."
    )
else:
    # Pega o acumulado máximo por município
    df_ex5_max = (
        df_ex5.groupby(["municipio", "latitude", "longitude"], as_index=False)
        ["casosAcumulado"].max()
        .dropna(subset=["latitude", "longitude"])
    )
    df_ex5_max = df_ex5_max.rename(columns={"latitude": "lat", "longitude": "lon"})
    df_ex5_max = df_ex5_max[(df_ex5_max["lat"] != 0) & (df_ex5_max["lon"] != 0)]

    if df_ex5_max.empty:
        st.info("Não há dados de coordenadas para os municípios deste estado neste arquivo.")
    else:
        st.map(df_ex5_max[["lat", "lon"]], zoom=6, use_container_width=True)
        st.caption(f"Cada ponto representa um município de {uf_mapa} com registro de casos acumulados.")

st.markdown("""
**Por que mapas municipais são essenciais na análise pandêmica:**  
- Permitem identificar **focos de transmissão** antes de se tornarem crises regionais.  
- Gestores podem **direcionar insumos** (vacinas, testes, respiradores) aos municípios com maior pressão.  
- Revelam o papel de cidades-polo no espraiamento para municípios menores na mesma microrregião.  
- Cruzar com dados socioeconômicos (IDH, densidade) permite priorizar ações de saúde pública com equidade.
""")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 6 – Matplotlib · Casos vs Óbitos Novos por Estado (última semana)
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 6 — Matplotlib · Casos Novos vs Óbitos Novos por Estado · Última Semana</div>', unsafe_allow_html=True)

ultima_semana = int(df_estado["semanaEpi"].max())
df_ex6 = (
    df_estado[df_estado["semanaEpi"] == ultima_semana]
    .groupby("estado", as_index=False)[["casosNovos", "obitosNovos"]]
    .sum()
    .sort_values("casosNovos", ascending=False)
)

st.caption(f"Semana epidemiológica mais recente no arquivo: **{ultima_semana}**")

fig_ex6, ax_ex6 = plt.subplots(figsize=(16, 6))
x = np.arange(len(df_ex6))
w = 0.4
bars1 = ax_ex6.bar(x - w / 2, df_ex6["casosNovos"], width=w, label="Casos Novos", color="#3498db", alpha=0.85)
bars2 = ax_ex6.bar(x + w / 2, df_ex6["obitosNovos"], width=w, label="Óbitos Novos", color="#c0392b", alpha=0.85)
ax_ex6.set_xticks(x)
ax_ex6.set_xticklabels(df_ex6["estado"], rotation=45, ha="right")
ax_ex6.set_ylabel("Quantidade")
ax_ex6.set_title(f"Casos Novos vs Óbitos Novos por Estado — Semana Epi {ultima_semana}")
ax_ex6.legend()
ax_ex6.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}".replace(",", ".")))
ax_ex6.grid(axis="y", linestyle="--", alpha=0.4)
plt.tight_layout()
st.pyplot(fig_ex6)

st.markdown("""
**O que os dados sugerem sobre a relação casos–óbitos:**  
- A **taxa de letalidade** (óbitos/casos) varia entre estados, refletindo diferenças em subnotificação, 
  estrutura hospitalar, perfil etário da população e cobertura vacinal.  
- Estados com **alto volume de casos mas baixa barra de óbitos** tendem a ter melhor capacidade de 
  diagnóstico (mais testes) e/ou população mais jovem.  
- Estados do Norte/Nordeste historicamente apresentaram **maior letalidade relativa** por menor acesso 
  a UTIs — o que um gráfico assim evidencia imediatamente.  
- A comparação lado a lado desmistifica a ideia de que "mais casos = mais mortes" de forma linear: 
  a qualidade do sistema de saúde e a vacinação quebram essa proporcionalidade.
""")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 7 – Seaborn Boxplot · Casos Novos por Semana · 3 Regiões
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 7 — Seaborn Boxplot · Distribuição de Casos Novos · Norte, Nordeste, Sudeste</div>', unsafe_allow_html=True)

regioes_ex7 = ["Norte", "Nordeste", "Sudeste"]
df_ex7 = df_estado[df_estado["regiao"].isin(regioes_ex7)].copy()
df_ex7_grp = (
    df_ex7.groupby(["semanaEpi", "regiao"], as_index=False)["casosNovos"].sum()
)

fig_ex7, ax_ex7 = plt.subplots(figsize=(10, 5))
palette = {"Norte": "#e67e22", "Nordeste": "#9b59b6", "Sudeste": "#2980b9"}
sns.boxplot(
    data=df_ex7_grp, x="regiao", y="casosNovos",
    palette=palette, ax=ax_ex7,
    flierprops=dict(marker="o", markerfacecolor="gray", markersize=3, alpha=0.5),
)
ax_ex7.set_xlabel("Região")
ax_ex7.set_ylabel("Casos Novos por Semana")
ax_ex7.set_title("Distribuição de Casos Novos por Semana — Norte, Nordeste, Sudeste")
ax_ex7.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}".replace(",", ".")))
ax_ex7.grid(axis="y", linestyle="--", alpha=0.4)
plt.tight_layout()
st.pyplot(fig_ex7)

st.markdown("""
**Principais diferenças observadas:**  
- **Sudeste**: mediana e amplitude intercuartil (IQR) muito maiores — reflexo da alta densidade populacional 
  e do número de estados com grande população (SP, MG, RJ, ES). Outliers acima indicam semanas de pico extremo.  
- **Nordeste**: mediana intermediária; nove estados com população significativa geram volume relevante, 
  mas a mediana semanal fica abaixo do Sudeste. Variabilidade alta reflete ondas irregulares.  
- **Norte**: menor mediana absoluta — menos habitantes, porém a **letalidade proporcional** foi historicamente 
  maior. A baixa amplitude no boxplot não deve ser confundida com menor gravidade.  
- Outliers (pontos acima dos bigodes) nas três regiões correspondem aos **picos de ondas** (jan/2021 e 
  jan-fev/2022), visíveis como eventos excepcionais mesmo na escala semanal agregada.
""")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 8 – Altair Gráfico de Área · Casos Novos por Semana · Região
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 8 — Altair Gráfico de Área · Casos Novos por Semana · Região</div>', unsafe_allow_html=True)

regiao_ex8 = st.selectbox(
    "Selecione a região:",
    options=REGIOES,
    index=REGIOES.index("Sudeste"),
    key="ex8_regiao",
)

df_ex8 = (
    df_estado[df_estado["regiao"] == regiao_ex8]
    .groupby("semanaEpi", as_index=False)["casosNovos"]
    .sum()
    .sort_values("semanaEpi")
)

chart_ex8 = (
    alt.Chart(df_ex8)
    .mark_area(
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color="#f9ca24", offset=0),
                alt.GradientStop(color="#e55039", offset=1),
            ],
            x1=1, x2=1, y1=1, y2=0,
        ),
        opacity=0.8,
    )
    .encode(
        x=alt.X("semanaEpi:Q", title="Semana Epidemiológica"),
        y=alt.Y("casosNovos:Q", title="Casos Novos", axis=alt.Axis(format=",d")),
        tooltip=["semanaEpi", alt.Tooltip("casosNovos:Q", format=",d")],
    )
    .properties(
        title=f"Casos Novos por Semana Epidemiológica — {regiao_ex8}",
        width="container", height=360,
    )
    .interactive()
)
st.altair_chart(chart_ex8, use_container_width=True)

st.markdown(f"""
**Região escolhida: {regiao_ex8} — Análise das tendências:**  
- O gráfico de área preenche o espaço abaixo da linha, facilitando a percepção visual do **volume total** 
  de casos em cada período.  
- **Picos distintos** correspondem às grandes ondas pandêmicas: 1ª onda (2020), 2ª onda Gama (jan-abr/2021) 
  e onda Ômicron (jan/2022).  
- Períodos de declínio entre os picos refletem o efeito combinado de medidas não-farmacológicas, 
  sazonalidade e, a partir de 2021, avanço da vacinação.  
- A escolha do **Sudeste** se justifica por concentrar ~43% da população brasileira e ser o epicentro 
  das principais ondas, tornando sua curva a mais representativa da dinâmica nacional.
""")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 9 – Altair Heatmap · Correlação Casos vs Óbitos Novos · Estado
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 9 — Altair Heatmap · Casos Novos vs Óbitos Novos por Semana · Estado</div>', unsafe_allow_html=True)

uf_ex9 = st.selectbox(
    "Selecione o estado para o heatmap:",
    options=ESTADOS_UF,
    index=ESTADOS_UF.index("SP") if "SP" in ESTADOS_UF else 0,
    key="ex9_uf",
)

df_ex9 = (
    df_estado[df_estado["estado"] == uf_ex9]
    .groupby("semanaEpi", as_index=False)[["casosNovos", "obitosNovos"]]
    .sum()
    .sort_values("semanaEpi")
)

# Cria bins para heatmap 2D
df_ex9["bins_casos"] = pd.cut(df_ex9["casosNovos"], bins=10, labels=False)
df_ex9["bins_obitos"] = pd.cut(df_ex9["obitosNovos"], bins=10, labels=False)

heat_data = (
    df_ex9.groupby(["bins_casos", "bins_obitos"], as_index=False)
    .agg(semanas=("semanaEpi", "count"))
)

chart_ex9 = (
    alt.Chart(heat_data)
    .mark_rect()
    .encode(
        x=alt.X("bins_casos:O", title="Faixa de Casos Novos (decil)"),
        y=alt.Y("bins_obitos:O", title="Faixa de Óbitos Novos (decil)"),
        color=alt.Color("semanas:Q", scale=alt.Scale(scheme="reds"),
                        title="Nº de Semanas"),
        tooltip=["bins_casos", "bins_obitos", "semanas"],
    )
    .properties(
        title=f"Heatmap: Distribuição Casos vs Óbitos por Semana — {uf_ex9}",
        width=500, height=400,
    )
)
st.altair_chart(chart_ex9, use_container_width=True)

st.markdown(f"""
**Correlações observadas — {uf_ex9}:**  
- A concentração de células escuras na **diagonal principal** (baixo decil de casos + baixo decil de óbitos 
  e alto + alto) indica **correlação positiva** entre casos novos e óbitos novos — esperado epidemiologicamente.  
- Células fora da diagonal revelam **defasagem temporal**: óbitos ocorrem tipicamente 2–4 semanas após os 
  casos, o que "desloca" a correlação perfeita.  
- Na ausência de dados de leitos hospitalares no CSV público (não disponíveis por município/estado), o heatmap 
  usa a relação casos×óbitos como proxy de pressão hospitalar — alta densidade nessa zona indica semanas críticas.  
- O **gradiente de vermelho** traduz frequência: células mais escuras = semanas onde ambas as métricas 
  estiveram simultaneamente elevadas — pico real da crise.
""")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 10 – Plotly Pizza · Casos Acumulados por Região
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 10 — Plotly · Gráfico de Pizza · Casos Acumulados por Região</div>', unsafe_allow_html=True)

df_ex10 = (
    df_estado.groupby("regiao", as_index=False)["casosAcumulado"]
    .max()
    # Agrupa pois o acumulado já é o total da região por estado; soma os estados
)
# Abordagem correta: pega o máximo acumulado por estado e depois soma por região
df_ex10 = (
    df_estado.groupby(["regiao", "estado"], as_index=False)["casosAcumulado"].max()
    .groupby("regiao", as_index=False)["casosAcumulado"].sum()
)

cores_pizza = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
fig_ex10 = px.pie(
    df_ex10,
    names="regiao",
    values="casosAcumulado",
    title="Distribuição Percentual de Casos Acumulados de COVID-19 por Região",
    color_discrete_sequence=cores_pizza,
    hole=0.35,
)
fig_ex10.update_traces(
    textposition="outside",
    textinfo="percent+label",
    hovertemplate="<b>%{label}</b><br>Casos: %{value:,.0f}<br>(%{percent})<extra></extra>",
)
fig_ex10.update_layout(height=500, legend_title="Região")
st.plotly_chart(fig_ex10, use_container_width=True)

st.markdown("""
**O que os dados revelam sobre a distribuição geográfica:**  
- O **Sudeste** lidera com margem expressiva (~43–47% dos casos totais), reflexo de sua densidade 
  populacional — SP, MG, RJ e ES concentram quase metade do país.  
- O **Nordeste** aparece em segundo lugar, impulsionado pelos 9 estados com população somada superior 
  à maioria das regiões.  
- **Sul** e **Centro-Oeste**, apesar de menores populações, apresentam proporções relevantes — o Sul 
  por alta urbanização e o Centro-Oeste pelo papel de Brasília como hub político-administrativo.  
- O **Norte** tem a menor fatia absoluta, mas sua participação relativa ao tamanho populacional indica 
  **alta taxa de incidência per capita** — o que não aparece no gráfico de pizza e requer análise complementar.  
- Conclusão: casos absolutos espelham principalmente a **distribuição demográfica** do Brasil, não 
  necessariamente o grau de exposição ao risco de cada região.
""")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 11 – Plotly Subplots · Casos e Óbitos por Semana · 2 Regiões
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 11 — Plotly Subplots · Casos e Óbitos Novos por Semana · 2 Regiões</div>', unsafe_allow_html=True)

col11a, col11b = st.columns(2)
with col11a:
    regiao_ex11_1 = st.selectbox("Região 1:", REGIOES, index=3, key="ex11r1")  # Sudeste
with col11b:
    regiao_ex11_2 = st.selectbox("Região 2:", REGIOES, index=0, key="ex11r2")  # Norte

def agg_regiao(regiao):
    return (
        df_estado[df_estado["regiao"] == regiao]
        .groupby("semanaEpi", as_index=False)[["casosNovos", "obitosNovos"]]
        .sum()
        .sort_values("semanaEpi")
    )

df_r1 = agg_regiao(regiao_ex11_1)
df_r2 = agg_regiao(regiao_ex11_2)

fig_ex11 = make_subplots(
    rows=2, cols=2,
    subplot_titles=[
        f"Casos Novos — {regiao_ex11_1}", f"Casos Novos — {regiao_ex11_2}",
        f"Óbitos Novos — {regiao_ex11_1}", f"Óbitos Novos — {regiao_ex11_2}",
    ],
    shared_xaxes=True,
    vertical_spacing=0.12,
)

# Casos
fig_ex11.add_trace(go.Bar(x=df_r1["semanaEpi"], y=df_r1["casosNovos"],
                          name=f"Casos {regiao_ex11_1}", marker_color="#3498db"), row=1, col=1)
fig_ex11.add_trace(go.Bar(x=df_r2["semanaEpi"], y=df_r2["casosNovos"],
                          name=f"Casos {regiao_ex11_2}", marker_color="#1abc9c"), row=1, col=2)
# Óbitos
fig_ex11.add_trace(go.Bar(x=df_r1["semanaEpi"], y=df_r1["obitosNovos"],
                          name=f"Óbitos {regiao_ex11_1}", marker_color="#c0392b"), row=2, col=1)
fig_ex11.add_trace(go.Bar(x=df_r2["semanaEpi"], y=df_r2["obitosNovos"],
                          name=f"Óbitos {regiao_ex11_2}", marker_color="#e67e22"), row=2, col=2)

fig_ex11.update_layout(
    title_text=f"Comparação por Semana Epidemiológica — {regiao_ex11_1} vs {regiao_ex11_2}",
    height=600,
    showlegend=False,
)
st.plotly_chart(fig_ex11, use_container_width=True)

st.markdown(f"""
**Diferenças observadas — {regiao_ex11_1} vs {regiao_ex11_2}:**  
- **Volume absoluto**: o {regiao_ex11_1} apresenta consistentemente maiores volumes por concentrar 
  mais população urbana; o {regiao_ex11_2} aparece com números menores mas não necessariamente 
  com menor impacto per capita.  
- **Sincronismo dos picos**: as ondas ocorrem nas mesmas semanas epidemiológicas, evidenciando 
  que a pandemia se propagou de forma nacional — mas com *magnitudes* distintas por região.  
- **Razão óbitos/casos**: observar visualmente se a barra vermelha (óbitos) sobe proporcionalmente 
  à azul (casos) revela a **letalidade efetiva** — regiões com menor acesso hospitalar mostram 
  razão mais alta.  
- Os subplots lado a lado facilitam a **comparação temporal alinhada**, eliminando a necessidade 
  de escala dupla num único gráfico.
""")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════
# EXERCÍCIO 12 – PyDeck · Mapa de Densidade Ajustada por Município · Região
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="exercise-header">Exercício 12 — PyDeck · Mapa Interativo · Densidade de Casos por Município · Região</div>', unsafe_allow_html=True)

regiao_ex12 = st.selectbox(
    "Selecione a região para o mapa PyDeck:",
    options=REGIOES,
    index=REGIOES.index("Sudeste"),
    key="ex12_regiao",
)

df_ex12 = df_mun[df_mun["regiao"] == regiao_ex12].copy()

if "latitude" not in df_ex12.columns or "longitude" not in df_ex12.columns:
    st.warning(
        "Colunas de latitude/longitude não encontradas no CSV. "
        "O exercício 12 requer a versão completa do arquivo com coordenadas municipais."
    )
else:
    df_ex12_max = (
        df_ex12.groupby(["municipio", "latitude", "longitude", "codmun"], as_index=False)
        ["casosAcumulado"].max()
        .dropna(subset=["latitude", "longitude", "casosAcumulado"])
    )
    df_ex12_max = df_ex12_max[
        (df_ex12_max["latitude"] != 0) & (df_ex12_max["longitude"] != 0)
    ].copy()
    df_ex12_max["casosAcumulado"] = df_ex12_max["casosAcumulado"].astype(float)

    if df_ex12_max.empty:
        st.info("Nenhum dado municipal com coordenadas disponível para esta região.")
    else:
        # Raio proporcional ao log dos casos para melhor visualização
        df_ex12_max["radius"] = np.log1p(df_ex12_max["casosAcumulado"]) * 800

        lat_center = df_ex12_max["latitude"].mean()
        lon_center = df_ex12_max["longitude"].mean()

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_ex12_max,
            get_position=["longitude", "latitude"],
            get_radius="radius",
            get_fill_color=[200, 30, 30, 160],
            pickable=True,
        )

        view_state = pdk.ViewState(
            latitude=lat_center,
            longitude=lon_center,
            zoom=5,
            pitch=40,
        )

        tooltip = {
            "html": "<b>{municipio}</b><br/>Casos Acumulados: {casosAcumulado:,.0f}",
            "style": {"backgroundColor": "#2c3e50", "color": "white", "fontSize": "13px"},
        }

        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip=tooltip,
            map_style="mapbox://styles/mapbox/light-v10",
        )
        st.pydeck_chart(deck)
        st.caption(
            f"Raio de cada círculo proporcional ao log(casos acumulados). "
            f"Região: {regiao_ex12} · {len(df_ex12_max)} municípios plotados."
        )

st.markdown("""
**Como a densidade populacional influencia a disseminação:**  
- Municípios com maior concentração urbana (capitais e metrópoles) aparecem como **círculos maiores**, 
  refletindo tanto maior número de casos absolutos quanto maior capacidade de notificação.  
- A **inclinação (pitch 40°)** do mapa dá perspectiva tridimensional, facilitando identificar clusters 
  de municípios vizinhos com alta incidência — evidência de espraiamento por contiguidade territorial.  
- Cidades-polo regionais funcionam como **epicentros** a partir dos quais a doença migra para 
  municípios menores ao redor — padrão visível nos círculos menores que cercam os maiores.  
- A escala logarítmica do raio evita que um único município (como São Paulo) domine visualmente 
  o mapa, permitindo enxergar a heterogeneidade dentro da própria região.  
- Esse tipo de visualização permite ao gestor de saúde identificar **corredores de transmissão** 
  ao longo de rodovias e bacias hidrográficas — informação acionável para barreiras sanitárias.
""")

st.markdown("---")
st.caption(
    "Dashboard desenvolvido para fins acadêmicos · Dados: Ministério da Saúde / covid.saude.gov.br"
)
