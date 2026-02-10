import streamlit as st
import pandas as pd
import io
import re

# ==========================================
# CONFIGURAÇÕES DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Importador Oficial Magis5 (ARTEMIS)",
    page_icon="📦",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        height: 3em; 
        font-weight: 600; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button:hover { transform: translateY(-2px); transition: 0.3s; }
    h1 { color: #2c3e50; }
    .stDataFrame { width: 100%; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# DEFINIÇÃO DE COLUNAS E DADOS
# ==========================================

COLUNAS_SISTEMA = [
    "SKU Externo", "Código de Barras", "Descrição", "Marca", "Categoria", 
    "Tam/Qtde", "Sabor/Cor", "NCM", "Un Comercial", "Origem do Produto", 
    "CEST", "Unidade/Fração", "Regra Padrão", "Custo", "Venda", 
    "Altura", "Largura", "Profundidade", "Peso Liquido", "Peso Bruto", 
    "URL da foto", "ID Interno"
]

OBRIGATORIAS = [
    "SKU Externo", "Código de Barras", "Descrição", "NCM", 
    "Un Comercial", "Origem do Produto", "Unidade/Fração", 
    "Regra Padrão", "Peso Liquido", "Peso Bruto"
]

MAPA_UNIDADES = {
    'ML': 1, 'LT': 2, 'GR': 3, 'KG': 4, 'UN': 5, 'DZ': 6, 'KL': 7, 
    'PC': 8, 'PT': 9, 'PR': 10, 'BDJ': 11, 'BAG': 12, 'BLD': 13, 
    'BR': 14, 'CX': 15, 'FD': 25, 'M': 28, 'M2': 29, 'M3': 30
}

CODIGOS_FRACIONADOS = [2, 4, 7, 28, 29, 30]

DE_PARA_ARTEMIS = {
    0: 11,  1: 12,  2: 13,
    3: 14, 4: 15, 5: 16, 6: 17, 7: 18, 8: 1227
}

# ==========================================
# FUNÇÕES DE LIMPEZA
# ==========================================

def limpar_sku(valor):
    if pd.isna(valor): return ""
    return re.sub(r'[^a-zA-Z0-9\-]', '', str(valor).strip())

def limpar_ncm(valor):
    if pd.isna(valor): return ""
    limpo = re.sub(r'[^0-9]', '', str(valor))
    return limpo[:8]

def limpar_dinheiro(valor):
    """
    Retorna Float se tiver valor, ou None se estiver vazio.
    Não força 0.0 aqui para permitir campos vazios depois.
    """
    if pd.isna(valor) or str(valor).strip() == "": return None
    
    s_val = str(valor).replace("R$", "").replace(" ", "").strip()
    try:
        if ',' in s_val:
            s_val = s_val.replace('.', '').replace(',', '.')
        return float(s_val)
    except:
        return None

def formatar_brasileiro(valor):
    """
    Se for None -> Retorna "" (Vazio)
    Se for Número -> Retorna "12,50"
    """
    if pd.isna(valor) or valor is None: return ""
    try:
        return f"{float(valor):.2f}".replace('.', ',')
    except:
        return ""

def converter_unidade(valor):
    if pd.isna(valor): return 5 
    try:
        return int(float(valor))
    except:
        pass
    texto = str(valor).upper().strip()
    return MAPA_UNIDADES.get(texto, 5)

def definir_unidade_fracao(codigo_unidade):
    try:
        cod = int(codigo_unidade)
        if cod in CODIGOS_FRACIONADOS: return 1 
        return 0 
    except:
        return 0

def converter_origem_artemis(valor):
    if pd.isna(valor): return 10 
    val_str = str(valor).strip().upper()
    try:
        num = int(float(valor))
        if num in DE_PARA_ARTEMIS: return DE_PARA_ARTEMIS[num]
        if num in DE_PARA_ARTEMIS.values() or num == 10: return num
    except:
        pass
    if "NACIONAL" in val_str:
        if "MAIS DE 40" in val_str: return 14
        if "MENOS DE 40" in val_str: return 16
        if "BASICOS" in val_str or "BÁSICOS" in val_str: return 15
        return 11
    if "ESTRANGEIRA" in val_str or "IMPORTAD" in val_str:
        if "SEM SIMILAR" in val_str: return 17 if "DIRETA" in val_str else 18
        if "DIRETA" in val_str: return 12
        if "INTERNO" in val_str: return 13
        return 12 
    return 10

# ==========================================
# APP PRINCIPAL
# ==========================================

def main():
    st.title("Normalizador Magis5 - Padrão ARTEMIS")
    st.markdown("Validação de Planilhas com regras fiscais e formatação BR Inteligente.")
    
    col_up, col_info = st.columns([2, 1])
    
    with col_info:
        st.info("ℹ️ **Regras Ativas**")
        st.write("✅  **Decimal:** Vírgula (ex: 10,50)")
        st.write("✅ **Vazios:** Campos opcionais ficam em branco")
        st.write("✅ **Unidade:** Automática (KG=1, UN=0)")
        st.write("✅ **Origem:** Formatado com nosso gabarito 11-18 ou 1227 ou 10 se não identificado")

    with col_up:
        uploaded_file = st.file_uploader("📂 Carregue a planilha (.xlsx ou .csv)", type=['xlsx', 'csv'])

    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                try:
                    df_cliente = pd.read_csv(uploaded_file, encoding='utf-8', sep=';')
                except:
                    df_cliente = pd.read_csv(uploaded_file, encoding='latin1', sep=',')
            else:
                df_cliente = pd.read_excel(uploaded_file)
            
            df_cliente = df_cliente.dropna(how='all', axis=1)
            
            st.success(f"Arquivo carregado! {len(df_cliente)} produtos.")
            st.markdown("---")
            
            with st.form("form_map"):
                st.subheader("Mapeamento de Colunas")
                cols = st.columns(3)
                mapa = {}
                opcoes = ["(Vazio)"] + list(df_cliente.columns)
                
                for i, col_sis in enumerate(COLUNAS_SISTEMA):
                    prefix = "🔴" if col_sis in OBRIGATORIAS else "⚪"
                    idx_padrao = 0
                    for idx, opt in enumerate(opcoes):
                        if opt.lower() in col_sis.lower():
                            idx_padrao = idx
                            break
                    sel = cols[i % 3].selectbox(f"{prefix} {col_sis}", options=opcoes, index=idx_padrao)
                    if sel != "(Vazio)":
                        mapa[col_sis] = sel
                
                st.markdown("<br>", unsafe_allow_html=True)
                submit = st.form_submit_button("PROCESSAR DADOS", type="primary")

            if submit:
                processar(df_cliente, mapa)

        except Exception as e:
            st.error(f"Erro: {e}")

def processar(df_origem, mapa):
    df_final = pd.DataFrame(columns=COLUNAS_SISTEMA)
    
    for col_sis, col_cli in mapa.items():
        df_final[col_sis] = df_origem[col_cli]
    
    with st.status("Aplicando validações...", expanded=True) as status:
        
        # 1. ORIGEM
        if 'Origem do Produto' in df_final.columns:
            df_final['Origem do Produto'] = df_final['Origem do Produto'].apply(converter_origem_artemis)
        else:
            df_final['Origem do Produto'] = 11
            
        # 2. SKU
        df_final['SKU Externo'] = df_final['SKU Externo'].apply(limpar_sku)
        df_final = df_final[df_final['SKU Externo'] != ""]
        
        # 3. NCM
        if 'NCM' in df_final.columns:
            df_final['NCM'] = df_final['NCM'].apply(limpar_ncm)
            
        # 4. UNIDADES
        if 'Un Comercial' in df_final.columns:
            df_final['Un Comercial'] = df_final['Un Comercial'].apply(converter_unidade)
            df_final['Unidade/Fração'] = df_final['Un Comercial'].apply(definir_unidade_fracao)
        else:
             df_final['Unidade/Fração'] = 0

        # 5. VALORES (LÓGICA AJUSTADA AQUI)
        colunas_numericas = ['Custo', 'Venda', 'Peso Liquido', 'Peso Bruto', 'Altura', 'Largura', 'Profundidade']
        
        st.write("Formatando valores e respeitando campos vazios...")
        for col in colunas_numericas:
            if col in df_final.columns:
                # 1. Converte para Float ou None (sem forçar zero ainda)
                df_final[col] = df_final[col].apply(limpar_dinheiro)

                # 2. SÓ preenche com 0.0 se for OBRIGATÓRIA e estiver vazia
                if col in OBRIGATORIAS:
                     df_final[col] = df_final[col].fillna(0.0)
                
                # 3. Formata (None vira "", Float vira "10,50")
                df_final[col] = df_final[col].apply(formatar_brasileiro)
        
        status.update(label="Concluído!", state="complete", expanded=False)

    st.markdown("### Visualização (50 primeiras linhas)")
    st.dataframe(df_final.head(50))
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Importacao')
        ws = writer.sheets['Importacao']
        for i, col in enumerate(df_final.columns):
            ws.set_column(i, i, 18)
            
    st.download_button(
        label="⬇️ BAIXAR PLANILHA FINAL",
        data=buffer,
        file_name="importacao_magis5_br.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

if __name__ == "__main__":
    main()