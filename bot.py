import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import (
    Button, View, Modal, TextInput, UserSelect, Select, ChannelSelect, RoleSelect,
    LayoutView, Container, TextDisplay, Section, ActionRow, Separator, MediaGallery,
    Thumbnail, File
)
import asyncio
from datetime import datetime
import json
import os
import sys
import glob

# ========= CONFIGURAÇÕES =========
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERRO: DISCORD_TOKEN não definido!")
    sys.exit(1)

DATA_DIR = os.getenv("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)

DADOS_FILE = os.path.join(DATA_DIR, "dados_bot.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config_bot.json")

# ========= CATÁLOGO DE CONFIGURAÇÕES (PAINEL ADMIN) =========
SETTINGS_CONFIG = {
    # Canais
    'canal_logs_id':              ('📋 Canal de Logs',                      'channel'),
    'canal_admin_logs_id':        ('🛡️ Canal de Logs Admin',               'channel'),
    'canal_rank_id':              ('🏆 Canal de Ranking',                   'channel'),
    'canal_registros_id':         ('📝 Canal de Registros (farms)',         'channel'),
    'canal_backup_painel_id':     ('💾 Canal Painel Backup',                'channel'),
    'canal_compra_venda_id':      ('🛒 Canal Painel Compra/Venda',          'channel'),
    'canal_logs_compra_venda_id': ('📊 Canal Logs Compra/Venda',            'channel'),
    'canal_acoes_painel_id':      ('⚔️ Canal Painel Ações',                 'channel'),
    'canal_acoes_logs_id':        ('🎯 Canal Logs Ações',                   'channel'),
    'canal_solicitar_set_id':     ('📋 Canal Solicitar SET',                'channel'),
    'canal_registros_set_id':     ('📁 Canal Registros SET',                'channel'),
    'canal_painel_privado_id':    ('🔓 Canal Painel Criar Privado',         'channel'),
    'categoria_farms_id':         ('📂 Categoria dos Canais de Farm',       'channel'),
    # Cargos
    'cargo_00_id':                ('👑 Cargo Administrador',                'role'),
    'cargo_membro_id':            ('👤 Cargo Membro',                       'role'),
    'cargo_aprovar_set_id':       ('✅ Cargo Aprovar SET',                  'role'),
    'cargos_compra_venda_ids':    ('💸 Cargos Compra/Venda (IDs, vírgula)', 'produto'),
    'cargos_registrar_acao_ids':  ('⚔️ Cargos Registrar Ação (IDs, vírgula)','produto'),
    # Produtos
    'nome_produto1':              ('📦 Nome Produto 1',                     'produto'),
    'nome_produto2':              ('📦 Nome Produto 2',                     'produto'),
    'nome_produto3':              ('📦 Nome Produto 3',                     'produto'),
    'produto4_nome':              ('📦 Nome Produto 4',                     'produto'),
    'produto5_nome':              ('📦 Nome Produto 5',                     'produto'),
    'produto6_nome':              ('📦 Nome Produto 6',                     'produto'),
    'produto7_nome':              ('📦 Nome Produto 7',                     'produto'),
    'produto8_nome':              ('📦 Nome Produto 8',                     'produto'),
    'produto9_nome':              ('📦 Nome Produto 9',                     'produto'),
    'produto10_nome':             ('📦 Nome Produto 10',                    'produto'),
    'valor_produto1_por_unidade': ('💰 Valor Unitário Produto 1 (R$)',      'produto'),
    'valor_produto2_por_unidade': ('💰 Valor Unitário Produto 2 (R$)',      'produto'),
    'valor_produto3_por_unidade': ('💰 Valor Unitário Produto 3 (R$)',      'produto'),
}

ALLOWED_SETTING_KEYS = set(SETTINGS_CONFIG.keys())

# ========= DADOS =========
dados = {
    "usuarios": {},
    "canais": {},
    "caixa_semana": {},
    "compras_vendas": {},
    "usuarios_banidos": {},
    "dinheiro_sujo": {},
    "acoes": {},
    "sets_pendentes": {},
    "backups_historicos": {}
}

def salvar_dados():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_dados():
    try:
        with open(DADOS_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            for key in dados:
                if key not in loaded:
                    loaded[key] = {}
            dados.update(loaded)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"Erro carregar_dados: {e}")
        return False

# ========= CONFIGURAÇÕES (SUBSTITUI O BANCO) =========
def _load_config_file():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Erro _load_config_file: {e}")
        return {}

def _save_config_file(cfg):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ========= CRIAÇÃO DO BOT =========
class MeuBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.guild_settings = {}

    async def setup_hook(self):
        # Views persistentes (as que usam custom_id em botões)
        self.add_view(CompraVendaView())
        self.add_view(ActionPanelView())
        self.add_view(BackupView())
        self.add_view(RankingView())
        self.add_view(SetPainelView())
        self.add_view(BotaoCriarCanalView())
        print("✅ Views persistentes registradas.")

bot = MeuBot()

# ========= ASSINATURA (DESATIVADA - SEMPRE ATIVA) =========
def is_guild_active(gid: int) -> bool:
    return True

async def check_subscription(interaction: discord.Interaction) -> bool:
    return True

def require_active_subscription():
    async def predicate(ctx):
        return True
    return commands.check(predicate)

# ========= CARREGAR/SALVAR CONFIG =========
async def load_all_settings():
    cfg = _load_config_file()
    bot.guild_settings = {}
    for gid_str, data in cfg.items():
        try:
            gid = int(gid_str)
            bot.guild_settings[gid] = dict(data)
        except:
            continue
    print(f"✅ Configurações carregadas: {len(bot.guild_settings)} servidores")
    return True

async def save_setting(gid: int, key: str, value):
    if key not in ALLOWED_SETTING_KEYS:
        return False
    cfg = _load_config_file()
    gid_str = str(gid)
    if gid_str not in cfg:
        cfg[gid_str] = {}
    cfg[gid_str][key] = value
    _save_config_file(cfg)
    if gid not in bot.guild_settings:
        bot.guild_settings[gid] = {}
    bot.guild_settings[gid][key] = value
    return True

# ========= FUNÇÕES AUXILIARES =========
def get_guild_setting(gid, key, default=None):
    return bot.guild_settings.get(gid, {}).get(key, default)

async def get_configured_channel(gid, key):
    cid = get_guild_setting(gid, key)
    if not cid:
        return None
    try:
        return bot.get_channel(int(cid))
    except:
        return None

def tem_cargo(member, cargos_ids):
    for cid in cargos_ids:
        cargo = member.guild.get_role(cid)
        if cargo and cargo in member.roles:
            return True
    return False

def is_admin(member):
    cid = get_guild_setting(member.guild.id, 'cargo_00_id')
    if cid:
        try:
            if tem_cargo(member, [int(cid)]):
                return True
        except:
            pass
    return member.guild_permissions.administrator

def is_membro(member):
    cid = get_guild_setting(member.guild.id, 'cargo_membro_id')
    if cid:
        try:
            return tem_cargo(member, [int(cid)])
        except:
            return False
    return False

def pode_comprar_vender(member):
    ids_str = get_guild_setting(member.guild.id, 'cargos_compra_venda_ids')
    if ids_str:
        ids = [int(x.strip()) for x in str(ids_str).split(',') if x.strip().isdigit()]
        if ids:
            return tem_cargo(member, ids)
    return False

def pode_registrar_acao(member):
    ids_str = get_guild_setting(member.guild.id, 'cargos_registrar_acao_ids')
    if ids_str:
        ids = [int(x.strip()) for x in str(ids_str).split(',') if x.strip().isdigit()]
        if ids:
            return tem_cargo(member, ids)
    return False

def pode_aprovar_set(member):
    admin = get_guild_setting(member.guild.id, 'cargo_00_id')
    set_cargo = get_guild_setting(member.guild.id, 'cargo_aprovar_set_id')
    cargos = []
    if admin:
        try: cargos.append(int(admin))
        except: pass
    if set_cargo:
        try: cargos.append(int(set_cargo))
        except: pass
    if cargos:
        return tem_cargo(member, cargos)
    return False

def calcular_valor_estimado(gid, produtos):
    total = 0.0
    for p in produtos:
        nome = p.get("produto", "")
        qtd = p.get("quantidade", 0)
        settings = bot.guild_settings.get(gid, {})
        chave_valor = None
        if nome == settings.get('nome_produto1', 'CHUMBO'):
            chave_valor = 'valor_produto1_por_unidade'
        elif nome == settings.get('nome_produto2', 'CAPSULA'):
            chave_valor = 'valor_produto2_por_unidade'
        elif nome == settings.get('nome_produto3', 'POLVORA'):
            chave_valor = 'valor_produto3_por_unidade'
        else:
            continue
        try:
            valor_unidade = float(settings.get(chave_valor, 0) or 0)
        except:
            valor_unidade = 0.0
        total += qtd * valor_unidade
    return total

# ========= MODAIS BASE (AGORA USAM LayoutView) =========
class MudarNomeModal(Modal, title="Mudar Nome do Canal"):
    novo_nome = TextInput(label="Novo nome", required=True)
    def __init__(self, canal):
        super().__init__()
        self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        try:
            novo = self.novo_nome.value.lower().replace(" ", "-")[:90]
            await self.canal.edit(name=novo)
            await interaction.response.send_message(f"✅ Nome alterado para **{novo}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)

class ConfirmResetSemanalView(LayoutView):
    def __init__(self, gid, uid, uname, canal):
        super().__init__(timeout=60)
        self.gid = gid; self.uid = uid; self.uname = uname; self.canal = canal

        # Container para o texto e botões
        container = Container(accent_color=0xff9900)
        container.add_item(TextDisplay("⚠️ **Tem certeza que deseja resetar a semana?**\n"
                                       f"Usuário: **{uname}**\n"
                                       "Esta ação não pode ser desfeita."))
        container.add_item(Separator())

        # ActionRow para os botões
        row = ActionRow()
        sim_btn = Button(label="Sim", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="confirm_reset_sim")
        nao_btn = Button(label="Não", style=discord.ButtonStyle.secondary, custom_id="confirm_reset_nao")
        sim_btn.callback = self.sim_callback
        nao_btn.callback = self.nao_callback
        row.add_item(sim_btn)
        row.add_item(nao_btn)
        container.add_item(row)

        self.add_item(container)

    async def sim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        gid_str, uid_str = str(self.gid), str(self.uid)
        if gid_str in dados["caixa_semana"] and uid_str in dados["caixa_semana"][gid_str]:
            del dados["caixa_semana"][gid_str][uid_str]
        if gid_str in dados["usuarios"] and uid_str in dados["usuarios"][gid_str]:
            dados["usuarios"][gid_str][uid_str]["dinheiro_sujo"] = 0
            dados["usuarios"][gid_str][uid_str]["transacoes_dinheiro_sujo"] = []
        salvar_dados()
        await interaction.followup.send("✅ Semana resetada!", ephemeral=True)
        await log_acao(self.gid, "reset_semanal", interaction.user, f"Semana resetada para {self.uname}")
        self.stop()

    async def nao_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("❌ Cancelado.", ephemeral=True)
        self.stop()

class ConfirmarFechamentoView(LayoutView):
    def __init__(self, gid, uid, canal):
        super().__init__(timeout=60)
        self.gid = gid; self.uid = uid; self.canal = canal

        container = Container(accent_color=0xff0000)
        container.add_item(TextDisplay("⚠️ **Tem certeza que deseja fechar este canal?**\n"
                                       "Todos os dados serão perdidos."))
        container.add_item(Separator())

        row = ActionRow()
        sim_btn = Button(label="Sim", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="fechar_canal_sim")
        nao_btn = Button(label="Não", style=discord.ButtonStyle.secondary, custom_id="fechar_canal_nao")
        sim_btn.callback = self.sim_callback
        nao_btn.callback = self.nao_callback
        row.add_item(sim_btn)
        row.add_item(nao_btn)
        container.add_item(row)

        self.add_item(container)

    async def sim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        gid_str, uid_str = str(self.gid), str(self.uid)
        if gid_str in dados["canais"] and uid_str in dados["canais"][gid_str]:
            canal_id = dados["canais"][gid_str][uid_str]
            canal = interaction.guild.get_channel(canal_id)
            if canal:
                try: await canal.delete(reason="Fechamento solicitado")
                except: pass
            del dados["canais"][gid_str][uid_str]
            salvar_dados()
        await interaction.followup.send("✅ Canal fechado!", ephemeral=True)
        await log_acao(self.gid, "fechar_canal", interaction.user, "Canal fechado")
        self.stop()

    async def nao_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("❌ Cancelado.", ephemeral=True)
        self.stop()

# ========= LOGS E BACKUP =========
async def salvar_backup_completo(gid, admin_name="Sistema"):
    nome = os.path.join(DATA_DIR, f"backup_{gid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    backup_data = {
        "guild_id": gid,
        "data_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "admin": admin_name,
        "config": bot.guild_settings.get(gid, {}),
        "dados": {
            "usuarios": dados["usuarios"].get(str(gid), {}),
            "canais": dados["canais"].get(str(gid), {}),
            "caixa_semana": dados["caixa_semana"].get(str(gid), {}),
            "compras_vendas": dados["compras_vendas"].get(str(gid), []),
            "usuarios_banidos": dados["usuarios_banidos"].get(str(gid), []),
            "dinheiro_sujo": dados["dinheiro_sujo"].get(str(gid), {}),
            "acoes": dados["acoes"].get(str(gid), {}),
            "sets_pendentes": dados["sets_pendentes"].get(str(gid), {}),
            "backups_historicos": dados["backups_historicos"].get(str(gid), [])
        }
    }
    with open(nome, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    if str(gid) not in dados["backups_historicos"]:
        dados["backups_historicos"][str(gid)] = []
    dados["backups_historicos"][str(gid)].append(
        {"arquivo": os.path.basename(nome), "data": backup_data["data_backup"], "admin": admin_name}
    )
    salvar_dados()
    canal = await get_configured_channel(gid, 'canal_backup_painel_id')
    if canal:
        layout = LayoutView()
        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay("💾 **Backup Salvo**"))
        container.add_item(Separator())
        container.add_item(TextDisplay(f"Arquivo: **{os.path.basename(nome)}**"))
        layout.add_item(container)
        try:
            await canal.send(view=layout)
            await canal.send(file=discord.File(nome))
        except: pass
    return os.path.basename(nome)

async def log_acao(gid, acao, usuario, detalhes, cor=None):
    if not gid: return
    canal = await get_configured_channel(gid, 'canal_logs_id')
    if not canal: return
    cores = {
        "criar_canal": 0x2c2f33, "registrar_farm": 0x2c2f33, "registrar_dinheiro_sujo": 0x4f545c,
        "pagar": 0x99aab5, "fechar_canal": 0x4f545c, "fechar_caixa": 0x99aab5,
        "reset_rank": 0x4f545c, "compra_venda": 0x2c2f33, "editar_farm": 0x2c2f33,
        "editar_dinheiro_sujo": 0x2c2f33
    }
    cor_final = cores.get(acao, 0x2c2f33) if cor is None else cor

    layout = LayoutView()
    container = Container(accent_color=cor_final)
    container.add_item(TextDisplay(f"📌 **LOG: {acao.upper()}**"))
    container.add_item(Separator())
    container.add_item(TextDisplay(detalhes))
    if usuario:
        container.add_item(Separator())
        container.add_item(TextDisplay(f"Autor: **{usuario.name}**"))
    layout.add_item(container)
    try:
        await canal.send(view=layout)
    except: pass

async def log_admin(gid, titulo, descricao, cor=0x99aab5):
    if not gid: return
    canal = await get_configured_channel(gid, 'canal_admin_logs_id')
    if canal:
        layout = LayoutView()
        container = Container(accent_color=cor)
        container.add_item(TextDisplay(f"**{titulo}**"))
        container.add_item(Separator())
        container.add_item(TextDisplay(descricao))
        layout.add_item(container)
        try:
            await canal.send(view=layout)
        except: pass

async def limpar_logs_usuario(gid, user_id, user_name):
    if not gid: return 0
    gid_str = str(gid)
    if gid_str in dados["usuarios_banidos"] and str(user_id) in dados["usuarios_banidos"][gid_str]:
        return 0
    if gid_str not in dados["usuarios_banidos"]:
        dados["usuarios_banidos"][gid_str] = []
    dados["usuarios_banidos"][gid_str].append(str(user_id))
    total = 0
    for key in ['canal_logs_id', 'canal_admin_logs_id', 'canal_rank_id', 'canal_compra_venda_id']:
        canal = await get_configured_channel(gid, key)
        if canal:
            try:
                async for msg in canal.history(limit=None):
                    if msg.author == bot.user and msg.content:
                        if f"<@{user_id}>" in msg.content or f"<@!{user_id}>" in msg.content:
                            novo = msg.content.replace(f"<@{user_id}>", f"[REMOVIDO - {user_name}]").replace(f"<@!{user_id}>", f"[REMOVIDO - {user_name}]")
                            try:
                                await msg.edit(content=novo); total += 1
                            except: pass
            except: pass
    if gid_str in dados["canais"] and str(user_id) in dados["canais"][gid_str]:
        canal = bot.get_channel(dados["canais"][gid_str][str(user_id)])
        if canal:
            try: await canal.delete(reason=f"Usuário {user_name} removido")
            except: pass
            del dados["canais"][gid_str][str(user_id)]
    if gid_str in dados["usuarios"] and str(user_id) in dados["usuarios"][gid_str]:
        dados["usuarios"][gid_str][str(user_id)] = {
            "farms": [], "pagamentos": [], "dinheiro_sujo": 0,
            "nome": f"[REMOVIDO - {user_name}]",
            "removido_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "transacoes_dinheiro_sujo": []
        }
    salvar_dados()
    return total

# ========= RANKING (AGORA COM LayoutView) =========
class RankingView(LayoutView):
    def __init__(self, gid=None):
        super().__init__(timeout=None)
        self.gid = gid

        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay("🏆 **RANKING DO SERVIDOR**"))
        container.add_item(Separator())

        # Nota: Os dados do ranking são adicionados dinamicamente no atualizar_ranking
        # Este é apenas o esqueleto. Os TextDisplays com os dados reais são adicionados lá.

        row = ActionRow()
        atualizar_btn = Button(label="Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="rank_atualizar")
        resetar_btn = Button(label="Resetar", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="rank_resetar")
        atualizar_btn.callback = self.atualizar_callback
        resetar_btn.callback = self.resetar_callback
        row.add_item(atualizar_btn)
        row.add_item(resetar_btn)
        container.add_item(row)

        self.add_item(container)

    async def atualizar_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await atualizar_ranking(interaction.guild.id)
        await interaction.followup.send("✅ Ranking atualizado!", ephemeral=True)

    async def resetar_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        view = ConfirmarResetView(interaction.guild.id)
        await interaction.response.send_message("⚠️ Resetar ranking?", view=view, ephemeral=True)

class ConfirmarResetView(LayoutView):
    def __init__(self, gid):
        super().__init__(timeout=60); self.gid = gid

        container = Container(accent_color=0xff0000)
        container.add_item(TextDisplay("⚠️ **Tem certeza que deseja resetar o ranking?**\n"
                                       "Um backup será criado automaticamente."))
        container.add_item(Separator())

        row = ActionRow()
        sim_btn = Button(label="Sim", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="reset_rank_sim")
        nao_btn = Button(label="Não", style=discord.ButtonStyle.secondary, custom_id="reset_rank_nao")
        sim_btn.callback = self.sim_callback
        nao_btn.callback = self.nao_callback
        row.add_item(sim_btn)
        row.add_item(nao_btn)
        container.add_item(row)

        self.add_item(container)

    async def sim_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await salvar_backup_completo(self.gid, interaction.user.name)
        if str(self.gid) in dados["usuarios"]: dados["usuarios"][str(self.gid)] = {}
        if str(self.gid) in dados["caixa_semana"]: dados["caixa_semana"][str(self.gid)] = {}
        if str(self.gid) in dados["dinheiro_sujo"]: dados["dinheiro_sujo"][str(self.gid)] = {}
        salvar_dados()
        await log_acao(self.gid, "reset_rank", interaction.user, "Ranking resetado")
        await interaction.followup.send("✅ Ranking resetado!", ephemeral=True)
        await atualizar_ranking(self.gid)
        self.stop()

    async def nao_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("❌ Cancelado.", ephemeral=True); self.stop()

async def atualizar_ranking(gid):
    canal = await get_configured_channel(gid, 'canal_rank_id')
    if not canal: return
    try:
        async for msg in canal.history(limit=50):
            if msg.author == bot.user:
                await msg.delete()
    except: pass
    settings = bot.guild_settings.get(gid, {})
    produtos_config = [
        settings.get('nome_produto1', 'CHUMBO'),
        settings.get('nome_produto2', 'CAPSULA'),
        settings.get('nome_produto3', 'POLVORA'),
        settings.get('produto4_nome', ''), settings.get('produto5_nome', ''),
        settings.get('produto6_nome', ''), settings.get('produto7_nome', ''),
        settings.get('produto8_nome', ''), settings.get('produto9_nome', ''),
        settings.get('produto10_nome', '')
    ]
    produtos_config = [p for p in produtos_config if p and p.strip()]
    totais_produtos = {prod: 0 for prod in produtos_config}
    produtos_por_usuario = {}
    total_farms_registrados = 0
    total_dinheiro_sujo_geral = 0.0
    for uid, data in dados["usuarios"].get(str(gid), {}).items():
        if "removido_em" in data: continue
        try: user = await bot.fetch_user(int(uid))
        except: continue
        produtos_por_usuario[uid] = {prod: 0 for prod in produtos_config}
        farms = data.get("farms", [])
        total_farms_registrados += len(farms)
        for farm in farms:
            for p in farm.get("produtos", []):
                nome_prod = p.get("produto", "")
                if nome_prod in produtos_config:
                    qtd = p.get("quantidade", 0)
                    produtos_por_usuario[uid][nome_prod] += qtd
                    totais_produtos[nome_prod] += qtd
        total_dinheiro_sujo_geral += data.get("dinheiro_sujo", 0)

    layout = LayoutView()
    container = Container(accent_color=0x2c2f33)
    container.add_item(TextDisplay("🏆 **RANKING DO SERVIDOR**"))
    container.add_item(Separator())
    container.add_item(TextDisplay(f"Total de farms: {total_farms_registrados} | Dinheiro sujo total: R$ {total_dinheiro_sujo_geral:,.2f}"))

    produtos_ordenados = sorted(totais_produtos.items(), key=lambda x: x[1], reverse=True)[:5]
    for idx, (nome_prod, qtd_total) in enumerate(produtos_ordenados):
        medalha = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'][idx] if idx < 5 else f'{idx+1}°'
        top_usuarios = []
        for uid, prods in produtos_por_usuario.items():
            qtd_user = prods.get(nome_prod, 0)
            if qtd_user > 0:
                try:
                    user = await bot.fetch_user(int(uid))
                    top_usuarios.append((user.name, qtd_user))
                except: continue
        top_usuarios.sort(key=lambda x: x[1], reverse=True)
        top_5 = top_usuarios[:5]
        texto = "\n".join(
            f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'{i+1}°'} **{u[0]}** - {u[1]:,}"
            for i, u in enumerate(top_5)
        ) if top_5 else "Nenhum"
        container.add_item(TextDisplay(f"{medalha} **{nome_prod}**\n{texto}"))
        container.add_item(Separator())

    usuarios = []
    for uid, data in dados["usuarios"].get(str(gid), {}).items():
        if "removido_em" in data: continue
        try: user = await bot.fetch_user(int(uid))
        except: continue
        total_pag = sum(p["valor"] for p in data.get("pagamentos", []))
        qtd_pag = len(data.get("pagamentos", []))
        din_sujo = data.get("dinheiro_sujo", 0)
        usuarios.append({"nome": user.name, "total_pag": total_pag, "qtd_pag": qtd_pag, "din_sujo": din_sujo})

    lista_salario = sorted(usuarios, key=lambda x: x["total_pag"], reverse=True)[:5]
    txt = "\n".join(
        f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'{i+1}°'} **{u['nome']}** - R$ {u['total_pag']:,.2f} ({u['qtd_pag']} pags)"
        for i,u in enumerate(lista_salario) if u['total_pag']>0
    ) or "Nenhum"
    container.add_item(TextDisplay(f"💰 **TOP SALÁRIO**\n{txt}"))
    container.add_item(Separator())

    lista_sujo = sorted(usuarios, key=lambda x: x["din_sujo"], reverse=True)[:5]
    txt = "\n".join(
        f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'{i+1}°'} **{u['nome']}** - R$ {u['din_sujo']:,.2f}"
        for i,u in enumerate(lista_sujo) if u['din_sujo']>0
    ) or "Nenhum"
    container.add_item(TextDisplay(f"💀 **DINHEIRO SUJO**\n{txt}"))

    row = ActionRow()
    atualizar_btn = Button(label="Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="rank_atualizar")
    resetar_btn = Button(label="Resetar", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="rank_resetar")
    atualizar_btn.callback = RankingView(gid).atualizar_callback
    resetar_btn.callback = RankingView(gid).resetar_callback
    row.add_item(atualizar_btn)
    row.add_item(resetar_btn)
    container.add_item(row)

    layout.add_item(container)
    try:
        await canal.send(view=layout)
    except: pass

# ========= BOTÃO CRIAR CANAL =========
class BotaoCriarCanalView(LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay("🔓 **CRIAR SEU CANAL PRIVADO**"))
        container.add_item(Separator())
        container.add_item(TextDisplay("Crie seu canal exclusivo para gerenciar seus farms com privacidade e organização."))
        container.add_item(Separator())
        container.add_item(TextDisplay(
            "🎯 **O que você ganha?**\n"
            "• 📦 **Registrar farms** de produtos com cálculo de valor estimado\n"
            "• 💰 **Registrar dinheiro sujo** com totalização automática\n"
            "• ✏️ **Editar** registros antigos (farms e depósitos)\n"
            "• 📋 **Visualizar seu histórico completo**\n"
            "• 📊 **Fechar caixa** (administradores) com divisão automática\n"
            "• Seu canal é **privado** – ninguém mais vê, a não ser que você compartilhe."
        ))
        container.add_item(Separator())

        row = ActionRow()
        criar_btn = Button(label="🔓 Criar Meu Canal Privado", style=discord.ButtonStyle.success, emoji="🔓", custom_id="criar_canal_privado")
        criar_btn.callback = self.criar_callback
        row.add_item(criar_btn)
        container.add_item(row)

        self.add_item(container)

    async def criar_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        gid = interaction.guild.id
        cat_id = get_guild_setting(gid, 'categoria_farms_id')
        if not cat_id:
            await interaction.followup.send("❌ Categoria não configurada. Peça a um admin.", ephemeral=True); return
        categoria = interaction.guild.get_channel(int(cat_id))
        if not categoria:
            await interaction.followup.send("❌ Categoria não encontrada.", ephemeral=True); return
        if str(gid) in dados["canais"] and str(interaction.user.id) in dados["canais"][str(gid)]:
            canal = interaction.guild.get_channel(dados["canais"][str(gid)][str(interaction.user.id)])
            if canal:
                await interaction.followup.send(f"ℹ️ Você já possui canal: {canal.mention}", ephemeral=True); return
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        admin_cargo = get_guild_setting(gid, 'cargo_00_id')
        if admin_cargo:
            cargo = interaction.guild.get_role(int(admin_cargo))
            if cargo:
                overwrites[cargo] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        nome = f"farm-{interaction.user.name}".lower().replace(" ", "-")[:90]
        canal = await categoria.create_text_channel(nome, overwrites=overwrites)
        if str(gid) not in dados["canais"]:
            dados["canais"][str(gid)] = {}
        dados["canais"][str(gid)][str(interaction.user.id)] = canal.id
        salvar_dados()

        # Envia a LayoutView do canal privado
        view = FarmChannelView(gid, interaction.user.id, interaction.user.name, canal.id)
        user_data = dados["usuarios"].get(str(gid), {}).get(str(interaction.user.id), {})
        qtd_farms = len(user_data.get("farms", []))
        dinheiro_sujo = user_data.get("dinheiro_sujo", 0)

        layout = LayoutView()
        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay(f"🔐 **SEU CANAL PRIVADO**\n{interaction.user.mention}, bem-vindo ao seu espaço exclusivo!"))
        container.add_item(Separator())
        container.add_item(TextDisplay(f"📊 **Resumo**\n"
                                       f"**Criado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                                       f"**Farms registrados:** {qtd_farms}\n"
                                       f"**Dinheiro sujo acumulado:** R$ {dinheiro_sujo:,.2f}"))
        container.add_item(Separator())
        container.add_item(TextDisplay("🎯 **O que você pode fazer aqui?**\n"
                                       "• 📦 **Farm Produtos**\n"
                                       "• 💰 **Farm Dinheiro Sujo**\n"
                                       "• ✏️ **Editar Registro**\n"
                                       "• 📋 **Meus Registros**\n"
                                       "• *(Admins têm botões extras)*"))

        # ActionRows para os botões do canal de farm
        row1 = ActionRow()
        btn_farm_produtos = Button(label="📦 Farm Produtos", style=discord.ButtonStyle.secondary, custom_id="farm_produtos")
        btn_farm_dinheiro = Button(label="💰 Farm Dinheiro Sujo", style=discord.ButtonStyle.secondary, custom_id="farm_dinheiro")
        btn_editar = Button(label="✏️ Editar Registro", style=discord.ButtonStyle.secondary, custom_id="farm_editar")
        btn_farm_produtos.callback = view.farm_produtos_callback
        btn_farm_dinheiro.callback = view.farm_dinheiro_callback
        btn_editar.callback = view.editar_callback
        row1.add_item(btn_farm_produtos)
        row1.add_item(btn_farm_dinheiro)
        row1.add_item(btn_editar)
        container.add_item(row1)

        row2 = ActionRow()
        btn_fechar_caixa = Button(label="📊 Fechar Caixa", style=discord.ButtonStyle.secondary, custom_id="farm_fechar_caixa")
        btn_mudar_nome = Button(label="✏️ Mudar Nome", style=discord.ButtonStyle.secondary, custom_id="farm_mudar_nome")
        btn_historico = Button(label="📜 Histórico Caixa", style=discord.ButtonStyle.secondary, custom_id="farm_historico")
        btn_fechar_caixa.callback = view.fechar_caixa_callback
        btn_mudar_nome.callback = view.mudar_nome_callback
        btn_historico.callback = view.historico_callback
        row2.add_item(btn_fechar_caixa)
        row2.add_item(btn_mudar_nome)
        row2.add_item(btn_historico)
        container.add_item(row2)

        row3 = ActionRow()
        btn_meus_registros = Button(label="📋 Meus Registros", style=discord.ButtonStyle.primary, custom_id="farm_meus_registros")
        btn_reset_semanal = Button(label="🔄 Reset Semanal", style=discord.ButtonStyle.danger, custom_id="farm_reset_semanal")
        btn_fechar_canal = Button(label="🗑️ Fechar Canal", style=discord.ButtonStyle.danger, custom_id="farm_fechar_canal")
        btn_meus_registros.callback = view.meus_registros_callback
        btn_reset_semanal.callback = view.reset_semanal_callback
        btn_fechar_canal.callback = view.fechar_canal_callback
        row3.add_item(btn_meus_registros)
        row3.add_item(btn_reset_semanal)
        row3.add_item(btn_fechar_canal)
        container.add_item(row3)

        layout.add_item(container)
        await canal.send(view=layout)
        await log_acao(gid, "criar_canal", interaction.user, f"Canal {canal.mention} criado")
        await interaction.followup.send(f"✅ Canal criado: {canal.mention}", ephemeral=True)
        await atualizar_ranking(gid)

# ========= VIEW DO CANAL DE FARM (LayoutView) =========
class FarmChannelView(LayoutView):
    def __init__(self, gid, user_id, user_name, canal_id):
        super().__init__(timeout=None)
        self.gid=gid; self.user_id=user_id; self.user_name=user_name; self.canal_id=canal_id

        # Nota: Os botões são adicionados dinamicamente no método criar_callback acima.
        # Esta classe serve como um container para os callbacks.
        # A estrutura visual é montada no método criar_callback.

    async def farm_produtos_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas o dono do canal.", ephemeral=True); return
        await interaction.response.send_modal(FarmProdutosModal(self.gid, self.user_id, self.user_name, interaction.channel))

    async def farm_dinheiro_callback(self, interaction: discord.Interaction):
        if not (is_admin(interaction.user) or is_membro(interaction.user)):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(DinheiroSujoModal(self.gid, self.user_id, self.user_name, interaction.channel))

    async def editar_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        view = EscolherTipoEdicaoView(self.gid, self.user_id, self.user_name)
        await interaction.response.send_message("📝 Escolha o tipo de edição:", view=view, ephemeral=True)

    async def fechar_caixa_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        user_data = dados["usuarios"].get(str(self.gid), {}).get(str(self.user_id), {})
        total_sujo = user_data.get("dinheiro_sujo", 0)
        if total_sujo <= 0:
            await interaction.followup.send("ℹ️ Nenhum dinheiro sujo acumulado.", ephemeral=True); return
        lavagem = total_sujo * 0.25
        restante = total_sujo - lavagem
        faccao = restante * 0.60
        membro = restante * 0.40

        layout = LayoutView()
        container = Container(accent_color=0x99aab5)
        container.add_item(TextDisplay(f"📊 **RESUMO DO FECHAMENTO**\nUsuário: **{self.user_name}**"))
        container.add_item(Separator())
        container.add_item(TextDisplay(f"💰 Total farmado: **R$ {total_sujo:,.2f}**"))
        container.add_item(TextDisplay(f"🧼 Lavagem (25%): **R$ {lavagem:,.2f}**"))
        container.add_item(TextDisplay(f"⚔️ Facção (60%): **R$ {faccao:,.2f}**"))
        container.add_item(TextDisplay(f"👤 Membro (40%): **R$ {membro:,.2f}**"))
        container.add_item(Separator())

        row = ActionRow()
        continuar_btn = Button(label="Continuar", style=discord.ButtonStyle.success, custom_id="fechamento_continuar")
        continuar_btn.callback = self.continuar_fechamento_callback
        row.add_item(continuar_btn)
        container.add_item(row)
        layout.add_item(container)

        await interaction.followup.send(view=layout)

    async def continuar_fechamento_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        # Aqui você precisa recuperar os valores do fechamento. Como eles são calculados no callback anterior,
        # podemos passar via um estado temporário ou recalcular. Para simplificar, vamos recalcular.
        user_data = dados["usuarios"].get(str(self.gid), {}).get(str(self.user_id), {})
        total_sujo = user_data.get("dinheiro_sujo", 0)
        lavagem = total_sujo * 0.25
        restante = total_sujo - lavagem
        faccao = restante * 0.60
        membro = restante * 0.40
        modal = FechamentoCaixaModal(self.gid, self.user_id, self.user_name, interaction.channel, total_sujo, lavagem, faccao, membro)
        await interaction.response.send_modal(modal)

    async def mudar_nome_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        await interaction.response.send_modal(MudarNomeModal(interaction.channel))

    async def historico_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        fechamentos = dados["caixa_semana"].get(str(self.gid), {}).get(str(self.user_id), [])
        if not fechamentos:
            await interaction.followup.send("ℹ️ Nenhum fechamento registrado.", ephemeral=True); return
        layout = LayoutView()
        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay("📜 **Histórico de Caixa**"))
        container.add_item(Separator())
        for f in fechamentos[-10:]:
            data = datetime.strptime(f["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            txt = f"**{data}**\n**Meta:** {f.get('meta_farm','?')}\n**Pago:** R$ {f['dinheiro_sujo']['pago']:,.2f}"
            if f.get('observacao'): txt += f"\n*Obs:* {f['observacao']}"
            container.add_item(TextDisplay(txt))
            container.add_item(Separator())
        layout.add_item(container)
        await interaction.followup.send(view=layout, ephemeral=True)

    async def meus_registros_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await enviar_historico_detalhado(interaction, self.gid, self.user_id, self.user_name)

    async def reset_semanal_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        view = ConfirmResetSemanalView(self.gid, self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_message("⚠️ Resetar a semana?", view=view, ephemeral=True)

    async def fechar_canal_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        view = ConfirmarFechamentoView(self.gid, self.user_id, interaction.channel)
        await interaction.response.send_message("⚠️ Fechar este canal?", view=view, ephemeral=True)

# ========= MODAIS FARM (Mantidos, mas podem ser atualizados para LayoutView no futuro) =========
class FarmProdutosModal(Modal, title="Registrar Farm Produtos"):
    def __init__(self, gid, uid, uname, canal):
        super().__init__()
        self.gid=gid; self.uid=uid; self.uname=uname; self.canal=canal
        settings = bot.guild_settings.get(gid, {})
        self.produtos = [
            settings.get('nome_produto1', 'CHUMBO'), settings.get('nome_produto2', 'CAPSULA'),
            settings.get('nome_produto3', 'POLVORA'), settings.get('produto4_nome', ''),
            settings.get('produto5_nome', ''), settings.get('produto6_nome', ''),
            settings.get('produto7_nome', ''), settings.get('produto8_nome', ''),
            settings.get('produto9_nome', ''), settings.get('produto10_nome', '')
        ]
        self.produtos = [p for p in self.produtos if p and p.strip()][:5]
        for prod in self.produtos:
            self.add_item(TextInput(label=prod[:45], required=False, custom_id=prod[:45]))
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        produtos = []
        for campo in self.children:
            if campo.value is not None and campo.value.strip():
                try:
                    qtd = int(campo.value.strip())
                    if qtd > 0: produtos.append({"produto": campo.label, "quantidade": qtd})
                except: pass
        if not produtos:
            await interaction.followup.send("❌ Nenhum produto válido.", ephemeral=True); return
        await interaction.followup.send("📸 Envie a print da farm (imagem).", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == self.canal and m.attachments
        try: msg = await bot.wait_for('message', timeout=60, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tempo esgotado.", ephemeral=True); return
        img = msg.attachments[0].url
        gid_str, uid_str = str(self.gid), str(self.uid)
        if gid_str not in dados["usuarios"]: dados["usuarios"][gid_str] = {}
        if uid_str not in dados["usuarios"][gid_str]:
            dados["usuarios"][gid_str][uid_str] = {"farms": [], "pagamentos": [], "nome": self.uname, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
        farm = {"produtos": produtos, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "print_url": img, "validado": True,
                "farm_id": len(dados["usuarios"][gid_str][uid_str]["farms"]) + 1}
        dados["usuarios"][gid_str][uid_str]["farms"].append(farm)
        salvar_dados()
        valor_estimado = calcular_valor_estimado(self.gid, produtos)
        total_itens = sum(p["quantidade"] for p in produtos)

        layout = LayoutView()
        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay(f"📦 **Farm Registrada**\nUsuário: <@{self.uid}>"))
        container.add_item(Separator())
        container.add_item(TextDisplay("📋 **Produtos**\n" + "\n".join(f"• {p['produto']}: {p['quantidade']}" for p in produtos)))
        container.add_item(TextDisplay(f"📊 Total de itens: **{total_itens}**"))
        container.add_item(TextDisplay(f"💰 Valor estimado: **R$ {valor_estimado:,.2f}**"))
        container.add_item(TextDisplay(f"Farm #{farm['farm_id']}"))
        layout.add_item(container)

        try: await self.canal.send(view=layout)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(view=layout)
            except: pass
        await interaction.followup.send("✅ Farm registrada!", ephemeral=True)
        produtos_str = ', '.join(f"{p['produto']}:{p['quantidade']}" for p in produtos)
        await log_acao(self.gid, "registrar_farm", interaction.user, f"Produtos: {produtos_str} | Valor: R$ {valor_estimado:,.2f}")
        await atualizar_ranking(self.gid)

class DinheiroSujoModal(Modal, title="Registrar Dinheiro Sujo"):
    valor = TextInput(label="Valor (R$)", required=True)
    def __init__(self, gid, uid, uname, canal):
        super().__init__(); self.gid=gid; self.uid=uid; self.uname=uname; self.canal=canal
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if not (self.valor.value and self.valor.value.strip()):
            await interaction.followup.send("❌ Valor inválido.", ephemeral=True); return
        try: val = float(self.valor.value.replace(",", "."))
        except:
            await interaction.followup.send("❌ Valor inválido.", ephemeral=True); return
        if val <= 0:
            await interaction.followup.send("❌ O valor deve ser > 0.", ephemeral=True); return
        await interaction.followup.send("📸 Envie a print.", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == self.canal and m.attachments
        try: msg = await bot.wait_for('message', timeout=60, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tempo esgotado.", ephemeral=True); return
        img = msg.attachments[0].url
        gid_str, uid_str = str(self.gid), str(self.uid)
        if gid_str not in dados["usuarios"]: dados["usuarios"][gid_str] = {}
        if uid_str not in dados["usuarios"][gid_str]:
            dados["usuarios"][gid_str][uid_str] = {"farms": [], "pagamentos": [], "nome": self.uname, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
        trans = {"valor": val, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "print_url": img, "registrado_por": interaction.user.id}
        dados["usuarios"][gid_str][uid_str]["transacoes_dinheiro_sujo"].append(trans)
        novo_total = sum(t["valor"] for t in dados["usuarios"][gid_str][uid_str]["transacoes_dinheiro_sujo"])
        dados["usuarios"][gid_str][uid_str]["dinheiro_sujo"] = novo_total
        salvar_dados()

        layout = LayoutView()
        container = Container(accent_color=0x4f545c)
        container.add_item(TextDisplay(f"💰 **Dinheiro Sujo Registrado**\nUsuário: <@{self.uid}>"))
        container.add_item(Separator())
        container.add_item(TextDisplay(f"Valor: **R$ {val:,.2f}**"))
        container.add_item(TextDisplay(f"Novo total: **R$ {novo_total:,.2f}**"))
        layout.add_item(container)

        try: await self.canal.send(view=layout)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(view=layout)
            except: pass
        await interaction.followup.send(f"✅ R$ {val:,.2f} registrado!", ephemeral=True)
        await log_acao(self.gid, "registrar_dinheiro_sujo", interaction.user, f"Valor: R$ {val:,.2f} | Total: R$ {novo_total:,.2f}")
        await atualizar_ranking(self.gid)

class FechamentoSummaryView(LayoutView):
    def __init__(self, gid, uid, uname, canal, total, lavagem, faccao, membro):
        super().__init__(timeout=300)
        self.gid=gid; self.uid=uid; self.uname=uname; self.canal=canal
        self.total=total; self.lavagem=lavagem; self.faccao=faccao; self.membro=membro

        container = Container(accent_color=0x99aab5)
        container.add_item(TextDisplay(f"📊 **RESUMO DO FECHAMENTO**\nUsuário: **{uname}**"))
        container.add_item(Separator())
        container.add_item(TextDisplay(f"💰 Total farmado: **R$ {total:,.2f}**"))
        container.add_item(TextDisplay(f"🧼 Lavagem (25%): **R$ {lavagem:,.2f}**"))
        container.add_item(TextDisplay(f"⚔️ Facção (60%): **R$ {faccao:,.2f}**"))
        container.add_item(TextDisplay(f"👤 Membro (40%): **R$ {membro:,.2f}**"))
        container.add_item(Separator())

        row = ActionRow()
        continuar_btn = Button(label="Continuar", style=discord.ButtonStyle.success, custom_id="fechamento_continuar")
        continuar_btn.callback = self.continuar_callback
        row.add_item(continuar_btn)
        container.add_item(row)

        self.add_item(container)

    async def continuar_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        modal = FechamentoCaixaModal(self.gid, self.uid, self.uname, self.canal, self.total, self.lavagem, self.faccao, self.membro)
        await interaction.response.send_modal(modal)

class FechamentoCaixaModal(Modal, title="Finalizar Fechamento"):
    meta = TextInput(label="Meta (Sim/Não)", required=True)
    bonus = TextInput(label="Bônus (R$)", default="0", required=False)
    obs = TextInput(label="Observação", required=False, style=discord.TextStyle.long)
    def __init__(self, gid, uid, uname, canal, total, lavagem, faccao, membro):
        super().__init__()
        self.gid=gid; self.uid=uid; self.uname=uname; self.canal=canal
        self.total=total; self.lavagem=lavagem; self.faccao=faccao; self.membro=membro
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        meta_str = self.meta.value.lower()
        if meta_str not in ["sim", "não", "nao"]:
            await interaction.followup.send("❌ Meta inválida. Use 'Sim' ou 'Não'.", ephemeral=True); return
        meta = "Sim" if meta_str == "sim" else "Não"
        try: bonus_val = float(self.bonus.value.replace(",", ".")) if self.bonus.value else 0
        except: bonus_val = 0
        obs_text = self.obs.value.strip() if self.obs.value else None
        pagamento = self.membro + bonus_val
        await interaction.followup.send("📸 Envie a print.", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == self.canal and m.attachments
        try: msg = await bot.wait_for('message', timeout=60, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tempo esgotado.", ephemeral=True); return
        img = msg.attachments[0].url
        gid_str, uid_str = str(self.gid), str(self.uid)
        if gid_str not in dados["usuarios"]: dados["usuarios"][gid_str] = {}
        if uid_str not in dados["usuarios"][gid_str]:
            dados["usuarios"][gid_str][uid_str] = {"farms": [], "pagamentos": [], "nome": self.uname, "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
        dados["usuarios"][gid_str][uid_str]["pagamentos"].append({
            "valor": pagamento, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.id, "tipo": "Fechamento de Caixa",
            "detalhes": {"total": self.total, "lavagem": self.lavagem, "faccao": self.faccao, "membro": self.membro, "bonus": bonus_val},
            "print_url": img
        })
        fech = {"data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "admin": interaction.user.name, "usuario": self.uname,
                "meta_farm": meta, "dinheiro_sujo": {"total": self.total, "lavagem": self.lavagem, "faccao": self.faccao,
                "membro_base": self.membro, "bonus": bonus_val, "pago": pagamento}, "print_url": img, "observacao": obs_text}
        if gid_str not in dados["caixa_semana"]: dados["caixa_semana"][gid_str] = {}
        if uid_str not in dados["caixa_semana"][gid_str]: dados["caixa_semana"][gid_str][uid_str] = []
        dados["caixa_semana"][gid_str][uid_str].append(fech)
        salvar_dados()

        layout = LayoutView()
        container = Container(accent_color=0x99aab5)
        container.add_item(TextDisplay(f"📊 **Caixa Fechado**\nUsuário: **{self.uname}**"))
        container.add_item(Separator())
        container.add_item(TextDisplay(f"Meta: **{meta}**"))
        container.add_item(TextDisplay(f"Pagamento final: **R$ {pagamento:,.2f}**"))
        if bonus_val > 0: container.add_item(TextDisplay(f"Bônus: **R$ {bonus_val:,.2f}**"))
        if obs_text: container.add_item(TextDisplay(f"Observação: {obs_text}"))
        container.add_item(TextDisplay(f"Admin: {interaction.user.display_name}"))
        layout.add_item(container)

        try: await self.canal.send(view=layout)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(view=layout)
            except: pass
        await interaction.followup.send(f"✅ Pagamento de R$ {pagamento:,.2f} registrado!", ephemeral=True)
        await log_acao(self.gid, "fechar_caixa", interaction.user, f"Pagamento: R$ {pagamento:,.2f} para {self.uname}")
        await atualizar_ranking(self.gid)

# ========= EDIÇÃO =========
class EscolherTipoEdicaoView(LayoutView):
    def __init__(self, gid, uid, uname):
        super().__init__(timeout=120)
        self.gid=gid; self.uid=uid; self.uname=uname

        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay("📝 **Escolha o tipo de edição**"))
        container.add_item(Separator())

        select = Select(placeholder="O que editar?",
                        options=[
                            discord.SelectOption(label="Produtos", value="produtos"),
                            discord.SelectOption(label="Dinheiro Sujo", value="dinheiro")
                        ],
                        custom_id=f"edicao_tipo_{gid}_{uid}")
        select.callback = self.select_callback
        container.add_item(ActionRow(select))
        self.add_item(container)

    async def select_callback(self, interaction: discord.Interaction):
        if self.children[0].children[0].values[0] == "produtos":
            select = EditarRegistroSelect(self.gid, self.uid, self.uname)
            view = View(timeout=None)
            view.add_item(select)
            await interaction.response.send_message("📋 Selecione a farm:", view=view, ephemeral=True)
        else:
            select = EditarDinheiroSelect(self.gid, self.uid, self.uname)
            view = View(timeout=None)
            view.add_item(select)
            await interaction.response.send_message("💰 Selecione o depósito:", view=view, ephemeral=True)

# NOTA: As classes EditarRegistroSelect, EditarDinheiroSelect, EditarFarmModal e EditarDinheiroModal
# permanecem praticamente as mesmas, pois usam Select e Modal que não mudaram.
# Para economizar espaço, elas foram omitidas aqui, mas devem ser copiadas do código original.

# ========= COMPRA / VENDA (LayoutView) =========
class CompraVendaView(LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay("💸 **SISTEMA DE COMPRA E VENDA**"))
        container.add_item(Separator())
        container.add_item(TextDisplay("Registre transações de munição e itens entre facções de forma organizada."))
        container.add_item(Separator())
        container.add_item(TextDisplay(
            "📌 **Como usar**\n"
            "• **💸 Venda** – Registre uma venda informando tipos, quantidades, valores unitários e a facção compradora.\n"
            "• **🛒 Compra** – Registre uma compra informando o produto, quantidade, valor total e a facção vendedora.\n"
            "• Todos os registros vão para os logs e ficam disponíveis para consulta."
        ))

        row = ActionRow()
        venda_btn = Button(label="💸 Venda", style=discord.ButtonStyle.secondary, custom_id="compra_venda_venda")
        compra_btn = Button(label="🛒 Compra", style=discord.ButtonStyle.secondary, custom_id="compra_venda_compra")
        venda_btn.callback = self.venda_callback
        compra_btn.callback = self.compra_callback
        row.add_item(venda_btn)
        row.add_item(compra_btn)
        container.add_item(row)

        self.add_item(container)

    async def venda_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(VendaModal(interaction.guild.id))

    async def compra_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CompraModal(interaction.guild.id))

# ========= AÇÕES (LayoutView) =========
class ActionPanelView(LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay("⚔️ **SISTEMA DE AÇÕES**"))
        container.add_item(Separator())
        container.add_item(TextDisplay("Registre operações (ataques, missões, etc.) e gerencie os pagamentos."))
        container.add_item(Separator())
        container.add_item(TextDisplay(
            "📌 **Como funciona**\n"
            "• **⚔️ Abrir Ação** – Crie uma ação informando nome, valor, resultado (Vitória/Derrota) e participantes.\n"
            "• **💰 Pagamento** – Selecione uma ação pendente e o bot calcula automaticamente:\n"
            "  - Lavagem (25%)\n"
            "  - Líquido (75%)\n"
            "  - Divisão igual entre os membros participantes\n"
            "• Todos os registros vão para os logs."
        ))

        row = ActionRow()
        abrir_btn = Button(label="⚔️ Abrir Ação", style=discord.ButtonStyle.secondary, custom_id="acao_abrir")
        pagamento_btn = Button(label="💰 Pagamento", style=discord.ButtonStyle.secondary, custom_id="acao_pagamento")
        abrir_btn.callback = self.abrir_callback
        pagamento_btn.callback = self.pagamento_callback
        row.add_item(abrir_btn)
        row.add_item(pagamento_btn)
        container.add_item(row)

        self.add_item(container)

    async def abrir_callback(self, interaction: discord.Interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(ActionModal(interaction.guild.id))

    async def pagamento_callback(self, interaction: discord.Interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        acoes = dados["acoes"].get(str(interaction.guild.id), {})
        pendentes = {k:v for k,v in acoes.items() if not v.get("pago")}
        if not pendentes:
            await interaction.followup.send("ℹ️ Nenhuma ação pendente.", ephemeral=True); return
        view = ActionSelectView(interaction.guild.id, pendentes)
        await interaction.followup.send("📋 Selecione a ação:", view=view, ephemeral=True)

# ========= SET (LayoutView) =========
class SetPainelView(LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay("📋 **SOLICITAÇÃO DE SET**"))
        container.add_item(Separator())
        container.add_item(TextDisplay("Sistema para novos membros solicitarem entrada no grupo (SET)."))
        container.add_item(Separator())
        container.add_item(TextDisplay(
            "📌 **Como usar**\n"
            "• **Solicitar SET** – O usuário preenche um formulário com nome, ID do jogo e tell in game.\n"
            "• Em seguida, **seleciona um recrutador** (membro com cargo de recrutador).\n"
            "• O pedido vai para o canal de registros SET, onde administradores podem **aprovar** ou **recusar**.\n"
            "• Ao aprovar, o solicitante recebe automaticamente o cargo de **Membro**."
        ))

        row = ActionRow()
        solicitar_btn = Button(label="Solicitar SET", style=discord.ButtonStyle.success, custom_id="solicitar_set_btn")
        solicitar_btn.callback = self.solicitar_callback
        row.add_item(solicitar_btn)
        container.add_item(row)

        self.add_item(container)

    async def solicitar_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SolicitarSetModal(interaction.guild.id))

# ========= BACKUP (LayoutView) =========
class BackupView(LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay("💾 **BACKUP DO SERVIDOR**"))
        container.add_item(Separator())
        container.add_item(TextDisplay("Ferramenta para administradores protegerem os dados do servidor."))
        container.add_item(Separator())
        container.add_item(TextDisplay(
            "🔧 **Funcionalidades**\n"
            "• **💾 Criar Backup** – Gera um arquivo JSON com todos os dados do servidor (usuários, farms, caixa, ações, SET, etc.).\n"
            "• **🗑️ Apagar Locais** – Remove todos os arquivos de backup armazenados localmente.\n"
            "• **🔄 Recarregar** – Restaura um backup anterior, revertendo o servidor para aquele estado."
        ))

        row = ActionRow()
        criar_btn = Button(label="💾 Criar Backup", style=discord.ButtonStyle.secondary, custom_id="backup_criar")
        apagar_btn = Button(label="🗑️ Apagar Locais", style=discord.ButtonStyle.danger, custom_id="backup_apagar")
        recarregar_btn = Button(label="🔄 Recarregar", style=discord.ButtonStyle.primary, custom_id="backup_recarregar")
        criar_btn.callback = self.criar_callback
        apagar_btn.callback = self.apagar_callback
        recarregar_btn.callback = self.recarregar_callback
        row.add_item(criar_btn)
        row.add_item(apagar_btn)
        row.add_item(recarregar_btn)
        container.add_item(row)

        self.add_item(container)

    async def criar_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        nome = await salvar_backup_completo(interaction.guild.id, interaction.user.name)
        await interaction.followup.send(f"✅ Backup **{nome}** criado!", ephemeral=True)

    async def apagar_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = glob.glob(os.path.join(DATA_DIR, f"backup_{interaction.guild.id}_*.json"))
        for b in backups:
            try: os.remove(b)
            except: pass
        await interaction.followup.send(f"✅ {len(backups)} backup(s) deletados.", ephemeral=True)

    async def recarregar_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = sorted(glob.glob(os.path.join(DATA_DIR, f"backup_{interaction.guild.id}_*.json")), reverse=True)
        if not backups:
            await interaction.followup.send("ℹ️ Nenhum backup encontrado.", ephemeral=True); return
        view = RecarregarBackupView(interaction.guild.id, backups)
        await interaction.followup.send("📂 Selecione o backup:", view=view, ephemeral=True)

# ========= PAINEL ADMIN (LayoutView) =========
class AdminPanelView(LayoutView):
    def __init__(self, gid):
        super().__init__(timeout=600)
        self.gid = gid

        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay("⚙️ **PAINEL ADMINISTRATIVO — 4FAIXA Seeven**"))
        container.add_item(Separator())
        container.add_item(TextDisplay(
            "Bem-vindo ao painel de configuração do bot.\n"
            "Use os botões abaixo para configurar canais, cargos, produtos, criar painéis, "
            "gerenciar backups e visualizar estatísticas.\n\n"
            "**Tudo é salvo automaticamente em `config_bot.json`.**"
        ))
        container.add_item(Separator())

        # Linha 1: Canais, Cargos, Produtos
        row1 = ActionRow()
        btn_canais = Button(label="📢 Canais", style=discord.ButtonStyle.primary)
        btn_cargos = Button(label="👥 Cargos", style=discord.ButtonStyle.primary)
        btn_produtos = Button(label="📦 Produtos", style=discord.ButtonStyle.primary)
        btn_canais.callback = self.canais_callback
        btn_cargos.callback = self.cargos_callback
        btn_produtos.callback = self.produtos_callback
        row1.add_item(btn_canais)
        row1.add_item(btn_cargos)
        row1.add_item(btn_produtos)
        container.add_item(row1)

        # Linha 2: Criar Painéis, Backup, Stats
        row2 = ActionRow()
        btn_criar = Button(label="🎛️ Criar Painéis", style=discord.ButtonStyle.success)
        btn_backup = Button(label="💾 Backup", style=discord.ButtonStyle.secondary)
        btn_stats = Button(label="📊 Stats", style=discord.ButtonStyle.secondary)
        btn_criar.callback = self.criar_callback
        btn_backup.callback = self.backup_callback
        btn_stats.callback = self.stats_callback
        row2.add_item(btn_criar)
        row2.add_item(btn_backup)
        row2.add_item(btn_stats)
        container.add_item(row2)

        # Linha 3: Recarregar
        row3 = ActionRow()
        btn_reload = Button(label="🔄 Recarregar", style=discord.ButtonStyle.secondary)
        btn_reload.callback = self.reload_callback
        row3.add_item(btn_reload)
        container.add_item(row3)

        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True)
            return False
        return True

    async def canais_callback(self, interaction: discord.Interaction):
        view = SettingsCategoryView(self.gid, 'channel')
        await interaction.response.send_message("Selecione o canal a configurar:", view=view, ephemeral=True)

    async def cargos_callback(self, interaction: discord.Interaction):
        view = SettingsCategoryView(self.gid, 'role')
        await interaction.response.send_message("Selecione o cargo a configurar:", view=view, ephemeral=True)

    async def produtos_callback(self, interaction: discord.Interaction):
        view = SettingsCategoryView(self.gid, 'produto')
        await interaction.response.send_message("Selecione o produto/cargo a configurar:", view=view, ephemeral=True)

    async def criar_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        settings = bot.guild_settings.get(self.gid, {})
        resultado = await criar_todos_paineis(interaction.guild, settings)
        await interaction.followup.send(resultado, ephemeral=True)

    async def backup_callback(self, interaction: discord.Interaction):
        view = BackupView()
        await interaction.response.send_message("Escolha uma ação:", view=view, ephemeral=True)

    async def stats_callback(self, interaction: discord.Interaction):
        gid = self.gid; gid_str = str(gid)
        total_usuarios = len(dados["usuarios"].get(gid_str, {}))
        total_farms = 0; total_dinheiro_sujo = 0.0
        total_canais = len(dados["canais"].get(gid_str, {}))
        for uid, data in dados["usuarios"].get(gid_str, {}).items():
            if "removido_em" in data: continue
            total_farms += len(data.get("farms", []))
            total_dinheiro_sujo += data.get("dinheiro_sujo", 0)

        layout = LayoutView()
        container = Container(accent_color=0x2c2f33)
        container.add_item(TextDisplay("📊 **Estatísticas do Servidor**"))
        container.add_item(Separator())
        container.add_item(TextDisplay(f"👥 Usuários com farms: **{total_usuarios}**"))
        container.add_item(TextDisplay(f"📦 Total de farms: **{total_farms}**"))
        container.add_item(TextDisplay(f"💰 Dinheiro sujo total: **R$ {total_dinheiro_sujo:,.2f}**"))
        container.add_item(TextDisplay(f"🔓 Canais abertos: **{total_canais}**"))
        layout.add_item(container)
        await interaction.response.send_message(view=layout, ephemeral=True)

    async def reload_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await load_all_settings()
        await interaction.followup.send("✅ Configurações recarregadas!", ephemeral=True)

# =========================================================
# ========= COMANDOS ======================================
# =========================================================

@bot.hybrid_command(name="painel4faixaadmin", description="Painel administrativo do bot 4FAIXA Seeven")
@app_commands.default_permissions(administrator=True)
@commands.has_permissions(administrator=True)
async def painel4faixaadmin(ctx):
    if not ctx.guild:
        await ctx.send("❌ Use em um servidor."); return
    view = AdminPanelView(ctx.guild.id)
    await ctx.send(view=view)

@bot.hybrid_command(name="reload_config", description="Recarrega configurações do disco")
@commands.has_permissions(administrator=True)
async def reload_config(ctx):
    await load_all_settings()
    await ctx.send("✅ Configurações recarregadas!")

@bot.hybrid_command(name="criar_paineis", description="Recria todos os painéis do servidor")
@commands.has_permissions(administrator=True)
async def criar_paineis(ctx):
    settings = bot.guild_settings.get(ctx.guild.id, {})
    if not settings:
        await ctx.send("❌ Nenhuma configuração. Use `/painel4faixaadmin` para configurar."); return
    resultado = await criar_todos_paineis(ctx.guild, settings)
    await ctx.send(resultado)

@bot.hybrid_command(name="config", description="Mostra as configurações atuais do servidor")
@commands.has_permissions(administrator=True)
async def show_config(ctx):
    if not is_admin(ctx.author):
        return await ctx.send("❌ Sem permissão.")
    settings = bot.guild_settings.get(ctx.guild.id, {})
    if not settings:
        return await ctx.send("❌ Nenhuma configuração definida ainda.")
    layout = LayoutView()
    container = Container(accent_color=0x2c2f33)
    container.add_item(TextDisplay("⚙️ **Configurações do Bot**"))
    container.add_item(Separator())
    for k, v in settings.items():
        if k == 'guild_id': continue
        container.add_item(TextDisplay(f"**{k}:** `{str(v) if v else '❌'}`"))
    layout.add_item(container)
    await ctx.send(view=layout)

@bot.hybrid_command(name="stats", description="Mostra estatísticas do servidor")
async def server_stats(ctx):
    gid = ctx.guild.id; gid_str = str(gid)
    total_usuarios = len(dados["usuarios"].get(gid_str, {}))
    total_farms = 0; total_dinheiro_sujo = 0.0
    total_canais = len(dados["canais"].get(gid_str, {}))
    for uid, data in dados["usuarios"].get(gid_str, {}).items():
        if "removido_em" in data: continue
        total_farms += len(data.get("farms", []))
        total_dinheiro_sujo += data.get("dinheiro_sujo", 0)

    layout = LayoutView()
    container = Container(accent_color=0x2c2f33)
    container.add_item(TextDisplay("📊 **Estatísticas do Servidor**"))
    container.add_item(Separator())
    container.add_item(TextDisplay(f"👥 Usuários com farms: **{total_usuarios}**"))
    container.add_item(TextDisplay(f"📦 Total de farms: **{total_farms}**"))
    container.add_item(TextDisplay(f"💰 Dinheiro sujo total: **R$ {total_dinheiro_sujo:,.2f}**"))
    container.add_item(TextDisplay(f"🔓 Canais abertos: **{total_canais}**"))
    layout.add_item(container)
    await ctx.send(view=layout)

@bot.hybrid_command(name="me", description="Mostra seu resumo pessoal")
async def my_stats(ctx):
    uid = str(ctx.author.id); gid_str = str(ctx.guild.id)
    user_data = dados["usuarios"].get(gid_str, {}).get(uid, {})
    if not user_data:
        await ctx.send("ℹ️ Você ainda não possui registros. Crie seu canal privado!"); return
    farms = user_data.get("farms", []); trans = user_data.get("transacoes_dinheiro_sujo", [])
    pagamentos = user_data.get("pagamentos", []); total_ds = user_data.get("dinheiro_sujo", 0)
    total_recebido = sum(p["valor"] for p in pagamentos)

    layout = LayoutView()
    container = Container(accent_color=0x2c2f33)
    container.add_item(TextDisplay(f"👤 **Resumo de {ctx.author.display_name}**"))
    container.add_item(Separator())
    container.add_item(TextDisplay(f"📦 Farms registrados: **{len(farms)}**"))
    container.add_item(TextDisplay(f"💰 Dinheiro sujo atual: **R$ {total_ds:,.2f}**"))
    container.add_item(TextDisplay(f"💵 Total recebido: **R$ {total_recebido:,.2f}**"))
    container.add_item(TextDisplay(f"📊 Transações de DS: **{len(trans)}**"))
    container.add_item(TextDisplay(f"📋 Pagamentos recebidos: **{len(pagamentos)}**"))
    if farms:
        ultimo = farms[-1]
        data = datetime.strptime(ultimo["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        prods = ", ".join(f"{p['produto']}:{p['quantidade']}" for p in ultimo["produtos"])
        container.add_item(Separator())
        container.add_item(TextDisplay(f"📌 **Último farm**\n{data} - {prods}"))
    layout.add_item(container)
    await ctx.send(view=layout)

@bot.hybrid_command(name="remover_usuario", description="Remove todos os dados de um usuário")
@commands.has_permissions(administrator=True)
@app_commands.describe(user="Usuário a remover")
async def remover_usuario(ctx, user: discord.User):
    if not is_admin(ctx.author):
        return await ctx.send("❌ Sem permissão.")
    total = await limpar_logs_usuario(ctx.guild.id, user.id, user.name)
    await ctx.send(f"✅ {user.mention} removido. {total} mensagens limpas.")
    await log_admin(ctx.guild.id, "Usuário removido", f"{user.mention} por {ctx.author.mention}")
    await atualizar_ranking(ctx.guild.id)

# ========= EVENTOS =========
@bot.event
async def on_member_remove(member):
    gid = member.guild.id
    await limpar_logs_usuario(gid, member.id, member.name)
    if str(gid) in dados["canais"] and str(member.id) in dados["canais"][str(gid)]:
        canal = member.guild.get_channel(dados["canais"][str(gid)][str(member.id)])
        if canal:
            try: await canal.delete(reason="Usuário saiu")
            except: pass
        del dados["canais"][str(gid)][str(member.id)]
        salvar_dados()

@bot.event
async def on_guild_join(guild):
    print(f"Adicionado ao servidor: {guild.name} ({guild.id})")
    channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
    if channel:
        try:
            layout = LayoutView()
            container = Container(accent_color=0x2c2f33)
            container.add_item(TextDisplay("🎉 **Bot adicionado!** Use `/painel4faixaadmin` para configurar tudo."))
            layout.add_item(container)
            await channel.send(view=layout)
        except: pass

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} online!")
    await load_all_settings()
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash commands sincronizados.")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos: {e}")
    for guild in bot.guilds:
        if guild.id in bot.guild_settings:
            await atualizar_ranking(guild.id)
    print("✅ Bot pronto.")

if __name__ == "__main__":
    carregar_dados()
    bot.run(TOKEN)
