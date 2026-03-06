import streamlit as st
from datetime import datetime, timedelta
import pytz
import os
import json
import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import poisson
from dotenv import load_dotenv
from groq import Groq
import time
import hashlib
from functools import wraps

load_dotenv()

# Configuração Dark Mode
st.set_page_config(
    page_title="Quant Elite PRO - Versão Profissional", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Dark Mode Profissional
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%);
        color: #ffffff;
    }
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        font-weight: bold;
    }
    .metric-container {
        background: #1a1a2e;
        border-left: 4px solid #667eea;
        padding: 10px;
        border-radius: 5px;
    }
    .alert-success {
        background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
    }
    .alert-warning {
        background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%);
    }
    .alert-info {
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
    }
    .dataframe {
        background: #1a1a2e;
        color: white;
    }
    /* FORÇAR TODOS OS SPAN A FICAREM VISÍVEIS */
    span {
        opacity: 1.0 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.9) !important;
    }
    /* FORÇAR TODOS OS P COM SPAN */
    p span {
        opacity: 1.0 !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 20px !important;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.9) !important;
    }
    /* FORÇAR TODOS OS ELEMENTOS DENTRO DE DIVS */
    div p span {
        opacity: 1.0 !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 22px !important;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.9) !important;
    }
</style>
""", unsafe_allow_html=True)

# Configurações API
API_KEY = os.getenv("API_FUTEBOL_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

BASE_URL = "https://v3.football.api-sports.io"
BR_TZ = pytz.timezone("America/Sao_Paulo")

# =========================
# SISTEMA DE BANCO LOCAL PROFISSIONAL
# =========================

def init_user_db():
    """Inicializa banco de dados de usuários local"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'User',
            status_pagamento BOOLEAN DEFAULT false,
            data_expiracao DATE,
            dias_restantes INTEGER DEFAULT 31,
            whatsapp TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)
    
    # Criar usuário admin padrão se não existir
    cursor.execute("SELECT * FROM users WHERE email = 'admin@quantelite.com'")
    if not cursor.fetchone():
        admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute("""
            INSERT INTO users (email, password, role, status_pagamento, dias_restantes, whatsapp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('admin@quantelite.com', admin_password, 'ADM', True, 999, '(91) 98621-5730'))
    
    conn.commit()
    conn.close()

# Inicializar banco de usuários
init_user_db()

# =========================
# FUNÇÕES DE AUTENTICAÇÃO LOCAL
# =========================

def hash_password(password):
    """Criptografa senha"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user_local(email, password):
    """Verifica credenciais do usuário localmente"""
    try:
        hashed_password = hash_password(password)
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM users WHERE email = ? AND password = ?
        """, (email, hashed_password))
        
        user = cursor.fetchone()
        
        if user:
            # Atualizar último login
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            """, (user[0],))
            
            # Verificar status de pagamento (apenas para não-admin)
            if user[3] != 'ADM' and not user[4]:
                return None  # Bloquear acesso
            
            conn.commit()
        
        conn.close()
        return user
        
    except Exception as e:
        st.error(f"❌ Erro na autenticação: {str(e)}")
        return None

def check_authentication():
    """Verifica se usuário está autenticado"""
    return 'user' in st.session_state and st.session_state.user is not None

def logout():
    """Faz logout do usuário"""
    if 'user' in st.session_state:
        del st.session_state.user
    st.rerun()

# =========================
# INTERFACE DE LOGIN PROFISSIONAL
# =========================

def show_login():
    """Mostra tela de login profissional"""
    st.markdown(f"""
    <div style='text-align: center; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin: 50px auto; max-width: 500px;'>
        <h1 style='color: white; margin: 0; font-size: 2.5em;'>🏆 QUANT ELITE PRO</h1>
        <p style='color: white; margin: 10px 0;'>Sistema Profissional de Análise</p>
        <p style='color: white; margin: 5px 0;'>💰 Mensalidade: 31 dias de acesso</p>
        <p style='color: #38ef7d; margin: 5px 0; font-weight: bold;'>✅ Sistema Profissional</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.markdown("### 🔐 Acesso ao Sistema")
            
            email = st.text_input("📧 Email", placeholder="Digite seu email")
            password = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
            
            submitted = st.form_submit_button("🚀 Entrar", use_container_width=True)
            
            if submitted:
                if email and password:
                    user = verify_user_local(email, password)
                    
                    if user:
                        st.session_state.user = user
                        st.success(f"✅ Bem-vindo, {user[1]}!")
                        st.rerun()
                    else:
                        st.error("❌ Email, senha incorretos ou MENSALIDADE PENDENTE!")
                else:
                    st.error("❌ Preencha todos os campos!")
        
        st.markdown("---")
        st.write("📞 Suporte: (91) 98621-5730")
        st.write("💰 Mensalidade: 31 dias de acesso")
        st.write("🔐 Acesso restrito a usuários autorizados")

def get_all_users_local():
    """Obtém todos os usuários localmente"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM users ORDER BY created_at DESC
        """)
        
        users = cursor.fetchall()
        conn.close()
        return users
    except Exception as e:
        st.error(f"❌ Erro ao obter usuários: {str(e)}")
        return []
    # Verificar status do usuário
    if not st.session_state.user[4] and st.session_state.user[3] != 'ADM':
        st.error("❌ MENSALIDADE PENDENTE! Entre em contato para regularizar.")
        if st.button("🚪 Sair"):
            logout()
        st.stop()
    
    # Sidebar com informações do usuário e logout
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 👤 Usuário Logado")
        st.write(f"**{st.session_state.user[1]}**")
        st.write(f"🎭 Cargo: {st.session_state.user[3]}")
        st.write(f"💳 Status: {'✅ Pago' if st.session_state.user[4] else '❌ Pendente'}")
        
        # Mostrar informações de validade
        if st.session_state.user[3] == 'ADM':
            st.write("🗓️ Expira: **ILIMITADO**")
            st.write("⏰ Dias restantes: **∞ Ilimitado**")
        else:
            if st.session_state.user[6]:
                expiry = datetime.strptime(st.session_state.user[6], '%Y-%m-%d').date()
                days_left = (expiry - datetime.now().date()).days
                st.write(f"🗓️ Expira: {expiry}")
                st.write(f"⏰ Dias restantes: {days_left}")
                
                if days_left <= 5:
                    st.warning("⚠️ Sua assinatura expira em breve!")
                elif days_left <= 0:
                    st.error("❌ Sua assinatura expirou!")
        
        if st.button("🚪 Sair", use_container_width=True):
            logout()
        
        st.markdown("---")
        st.markdown("### 📞 Informações de Contato")
        st.write("📱 WhatsApp: (91) 98621-5730")
        st.write("💳 Chave PIX: cpf 01367822211 joilson moreira marinho")
        st.write("💰 Mensalidade: 31 dias de acesso")
        st.write("🏆 Versão Profissional - Banco Local")
        
        st.markdown("---")
    
    # Apenas administradores podem acessar o painel admin
    if st.session_state.user[3] == 'ADM':
        if st.sidebar.button("🛠️ Painel Admin", use_container_width=True):
            st.session_state.show_admin = not st.session_state.get('show_admin', False)
        
        # Mostrar painel admin ou aplicativo principal
        if st.session_state.get('show_admin', False):
            show_admin_panel()
        else:
            st.success("✅ Sistema funcionando perfeitamente!")
            st.info("🎯 Use o menu lateral para gerenciar usuários")

def show_admin_panel():
    """Painel do Administrador"""
    st.markdown(f"""
    <div style='background: linear-gradient(90deg, #e94560 0%, #0f3460 100%); padding: 20px; border-radius: 10px; margin: 20px 0;'>
        <h2 style='color: white; text-align: center; margin: 0;'>🛠️ PAINEL DO ADMINISTRADOR</h2>
        <p style='color: white; text-align: center; margin: 5px 0;'>📞 Suporte: (91) 98621-5730</p>
        <p style='color: #38ef7d; text-align: center; margin: 5px 0;'>🔒 Sistema Privado</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["👥 Gerenciar Usuários", "➕ Adicionar Usuário"])
    
    with tab1:
        st.markdown("### 📋 Lista de Usuários")
        
        users = get_all_users_local()
        
        if users:
            for user in users:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    st.write(f"👤 **{user[1]}**")
                    st.write(f"🎭 Cargo: {user[3]}")
                    st.write(f"📅 Criado: {user[8][:10]}")
                    if user[6]:
                        st.write(f"🗓️ Expira: {user[6]}")
                    st.write(f"💳 Status: {'✅ Pago' if user[4] else '❌ Pendente'}")
                
                with col2:
                    current_status = st.selectbox(
                        "Pagamento",
                        [True, False],
                        index=0 if user[4] else 1,
                        key=f"status_{user[0]}",
                        format_func=lambda x: "✅ Pago" if x else "❌ Pendente"
                    )
                
                with col3:
                    if st.button("💾", key=f"save_{user[0]}", help="Salvar alterações"):
                        update_user_status_local(user[0], current_status)
                        st.success("✅ Alterações salvas!")
                        st.rerun()
                
                with col4:
                    if user[1] != 'admin@quantelite.com':
                        if st.button("🗑️", key=f"delete_{user[0]}", help="Excluir usuário"):
                            delete_user_local(user[0])
                            st.success("✅ Usuário removido!")
                            st.rerun()
                
                st.markdown("---")
        else:
            st.info("Nenhum usuário encontrado.")
    
    with tab2:
        st.markdown("### ➕ Cadastrar Novo Usuário")
        
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_email = st.text_input("📧 Email do Usuário")
                new_password = st.text_input("🔒 Senha", type="password")
                new_role = st.selectbox("🎭 Cargo", ["User", "ADM"])
            
            with col2:
                new_whatsapp = st.text_input("📱 WhatsApp do Usuário", placeholder="(91) 98621-5730")
                new_status_pagamento = st.selectbox("💳 Status Pagamento", [True, False], 
                                                   format_func=lambda x: "✅ Pago" if x else "❌ Pendente")
                new_expiry_date = st.date_input(
                    "📅 Data de Vencimento",
                    value=datetime.now().date() + timedelta(days=31),
                    min_value=datetime.now().date(),
                    help="Data em que a assinatura do usuário expira"
                )
            
            submitted = st.form_submit_button("➕ Adicionar Usuário")
            
            if submitted:
                if new_email and new_password:
                    expiry_iso = new_expiry_date.isoformat() if new_role != 'ADM' else None
                    if add_user_local(new_email, new_password, new_role, new_status_pagamento, 
                                       new_whatsapp, expiry_iso):
                        st.success(f"✅ Usuário {new_email} criado com sucesso!")
                        if new_whatsapp:
                            st.success(f"📱 WhatsApp: {new_whatsapp}")
                        if new_role != 'ADM':
                            st.success(f"📅 Vencimento: {new_expiry_date}")
                        st.rerun()
                    else:
                        st.error("❌ Email já existe ou erro ao criar usuário!")
                else:
                    st.error("❌ Preencha todos os campos obrigatórios!")

def main():
    """Função principal que controla o fluxo da aplicação"""
    # Verificar se usuário está logado
    if not check_authentication():
        show_login()
    else:
        main_app()

if __name__ == "__main__":
    main()
