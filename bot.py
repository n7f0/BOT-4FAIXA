import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import (
    Button, View, Modal, TextInput, UserSelect, Select, ChannelSelect, RoleSelect,
    LayoutView, Container, TextDisplay, Section, ActionRow, Separator,
    MediaGallery, Thumbnail
)
import asyncio
from datetime import datetime
import json
import os
import sys
import glob

# ==================== CONFIGURAÇÕES ====================
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERRO: DISCORD_TOKEN não definido!")
    sys.exit(1)

DATA_DIR = os.getenv("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)

DADOS_FILE = os.path.join(DATA_DIR, "dados_bot.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config_bot.json")

# ==================== CATÁLOGO DE CONFIGURAÇÕES ====================
# Categorias: channel | role | produto | texto | sistema
# - role  → RoleSelect multi-seleção (aceita VÁRIOS cargos)
# - produto / texto / sistema → Modal de texto
SETTINGS_CONFIG = {
    # --- Canais ---
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
    # --- Cargos (multi-seleção) ---
    'cargo_00_id':                ('👑 Cargos de Administrador',            'role'),
    'cargo_membro_id':            ('👤 Cargos de Membro',                   'role'),
    'cargo_aprovar_set_id':       ('✅ Cargos Aprovar SET',                 'role'),
    'cargos_compra_venda_ids':    ('💸 Cargos Compra/Venda',                'role'),
    'cargos_registrar_acao_ids':  ('⚔️ Cargos Registrar Ação',              'role'),
    # --- Produtos ---
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
    # --- Sistema (taxas) ---
    'taxa_lavagem':               ('💧 Taxa de Lavagem (%)',                'sistema'),
    'taxa_faccao':                ('⚔️ Taxa da Facção (%)',                 'sistema'),
    'taxa_membro':                ('👤 Taxa do Membro (%)',                 'sistema'),
    'taxa_acao_lavagem':          ('🎯 Taxa de Lavagem em Ações (%)',       'sistema'),
}

ALLOWED_SETTING_KEYS = set(SETTINGS_CONFIG.keys())

# ==================== DADOS ====================
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

# ==================== CONFIG EM DISCO ====================
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

# ==================== BOT ====================
class MeuBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.guild_settings = {}

    async def setup_hook(self):
        self.add_view(CompraVendaView())
        self.add_view(ActionPanelView())
        self.add_view(BackupView())
        self.add_view(RankingView())
        self.add_view(SetPainelView())
        self.add_view(BotaoCriarCanalView())
        print("✅ Views persistentes registradas.")

bot = MeuBot()

# ==================== ASSINATURA ====================
def is_guild_active(gid: int) -> bool:
    return True

async def check_subscription(interaction: discord.Interaction) -> bool:
    return True

def require_active_subscription():
    async def predicate(ctx):
        return True
    return commands.check(predicate)

# ==================== CONFIG HELPERS ====================
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

def get_guild_setting(gid, key, default=None):
    return bot.guild_settings.get(gid, {}).get(key, default)

def get_taxa(gid, key, default_pct):
    val = get_guild_setting(gid, key)
    if not val:
        return default_pct
    try:
        return float(str(val).replace(',', '.')) / 100.0
    except:
        return default_pct

def _parse_ids(val):
    """Converte '123,456,789' em [123, 456, 789]."""
    if not val:
        return []
    try:
        return [int(x.strip()) for x in str(val).split(',') if x.strip().isdigit()]
    except:
        return []

async def get_configured_channel(gid, key):
    cid = get_guild_setting(gid, key)
    if not cid:
        return None
    try:
        return bot.get_channel(int(cid))
    except:
        return None

# ==================== HELPER: layout de texto simples ====================
def _text_layout(text: str, accent: int = 0x5865F2) -> LayoutView:
    layout = LayoutView()
    c = Container(accent_color=accent)
    c.add_item(TextDisplay(text))
    layout.add_item(c)
    return layout

# ==================== PERMISSÕES (multi-cargo) ====================
def tem_cargo(member, cargos_ids):
    for cid in cargos_ids:
        cargo = member.guild.get_role(cid)
        if cargo and cargo in member.roles:
            return True
    return False

def is_admin(member):
    ids = _parse_ids(get_guild_setting(member.guild.id, 'cargo_00_id'))
    if ids and tem_cargo(member, ids):
        return True
    return member.guild_permissions.administrator

def is_membro(member):
    ids = _parse_ids(get_guild_setting(member.guild.id, 'cargo_membro_id'))
    if ids:
        return tem_cargo(member, ids)
    return False

def pode_comprar_vender(member):
    ids = _parse_ids(get_guild_setting(member.guild.id, 'cargos_compra_venda_ids'))
    if ids:
        return tem_cargo(member, ids)
    return False

def pode_registrar_acao(member):
    ids = _parse_ids(get_guild_setting(member.guild.id, 'cargos_registrar_acao_ids'))
    if ids:
        return tem_cargo(member, ids)
    return False

def pode_aprovar_set(member):
    admin_ids = _parse_ids(get_guild_setting(member.guild.id, 'cargo_00_id'))
    set_ids = _parse_ids(get_guild_setting(member.guild.id, 'cargo_aprovar_set_id'))
    cargos = admin_ids + set_ids
    if cargos:
        return tem_cargo(member, cargos)
    return False

# ==================== CÁLCULO ====================
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

# ==================== MODAIS BASE ====================
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

class TextEditModal(Modal):
    valor = TextInput(label="Valor", required=True)
    def __init__(self, gid, key, label):
        super().__init__(title=f"Editar: {label[:40]}")
        self.gid = gid; self.key = key; self.label_txt = label
        current = bot.guild_settings.get(gid, {}).get(key, "")
        if current:
            try: self.valor.default = str(current)
            except: pass
    async def on_submit(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        ok = await save_setting(self.gid, self.key, self.valor.value.strip())
        if ok:
            await interaction.response.send_message(
                f"✅ **{self.label_txt}** atualizado para: `{self.valor.value.strip()}`", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Erro ao salvar.", ephemeral=True)

class ChannelEditView(LayoutView):
    def __init__(self, gid, key, label):
        super().__init__(timeout=180)
        self.gid = gid; self.key = key; self.label_txt = label
        c = Container(accent_color=0x5865F2)
        c.add_item(TextDisplay(f"📢 **Selecione o novo canal para:**\n`{label}`"))
        c.add_item(Separator())
        sel = ChannelSelect(placeholder="Selecione o canal...",
                            channel_types=[discord.ChannelType.text, discord.ChannelType.category])
        sel.callback = self._cb
        c.add_item(ActionRow(sel))
        self.add_item(c)
    async def _cb(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        canal = interaction.data["values"][0]
        ok = await save_setting(self.gid, self.key, str(canal))
        if ok:
            await interaction.response.send_message(f"✅ **{self.label_txt}** → <#{canal}>", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Erro ao salvar.", ephemeral=True)

# ==================== ROLE EDIT (MULTI-SELEÇÃO) ====================
class RoleEditView(LayoutView):
    """RoleSelect com múltipla seleção (0 a 25 cargos).
    Se salvar vazio, remove a configuração."""

    def __init__(self, gid, key, label, guild: discord.Guild):
        super().__init__(timeout=300)
        self.gid = gid; self.key = key; self.label_txt = label
        self.guild = guild

        # Pré-seleciona cargos já configurados
        current_ids = _parse_ids(bot.guild_settings.get(gid, {}).get(key))
        default_roles = []
        for rid in current_ids:
            role = guild.get_role(rid)
            if role:
                default_roles.append(role)

        c = Container(accent_color=0x5865F2)
        c.add_item(TextDisplay(
            f"👥 **Configurar cargos para:**\n`{label}`\n\n"
            f"• Selecione **um ou mais** cargos\n"
            f"• Envie **vazio** para limpar a configuração"
        ))
        c.add_item(Separator())

        sel = RoleSelect(
            placeholder="Selecione um ou mais cargos...",
            min_values=0,       # permite limpar
            max_values=25,
            default_values=default_roles if default_roles else []
        )
        sel.callback = self._cb
        c.add_item(ActionRow(sel))

        # Resumo
        if default_roles:
            c.add_item(TextDisplay(
                f"**Atualmente configurados ({len(default_roles)}):** "
                + " ".join(r.mention for r in default_roles)
            ))
        else:
            c.add_item(TextDisplay("**Atualmente:** ❌ Nenhum cargo configurado"))

        self.add_item(c)

    async def _cb(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        values = interaction.data.get("values") or []

        if not values:
            # Limpar
            ok = await save_setting(self.gid, self.key, "")
            if ok:
                await interaction.response.send_message(
                    f"🗑️ **{self.label_txt}** limpo (nenhum cargo).", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Erro ao limpar.", ephemeral=True)
            return

        # Salva como string CSV
        csv = ",".join(str(v) for v in values)
        ok = await save_setting(self.gid, self.key, csv)
        if not ok:
            await interaction.response.send_message("❌ Erro ao salvar.", ephemeral=True); return

        mencoes = " ".join(f"<@&{v}>" for v in values)
        await interaction.response.send_message(
            f"✅ **{self.label_txt}** → {len(values)} cargo(s):\n{mencoes}", ephemeral=True)

# ==================== CONFIRMAÇÕES ====================
class ConfirmResetSemanalView(LayoutView):
    def __init__(self, gid, uid, uname, canal):
        super().__init__(timeout=60)
        self.gid = gid; self.uid = uid; self.uname = uname; self.canal = canal
        c = Container(accent_color=0xFF9900)
        c.add_item(TextDisplay(f"⚠️ **Resetar a semana de {uname}?**\nEsta ação não pode ser desfeita."))
        c.add_item(Separator())
        row = ActionRow()
        b_sim = Button(label="Sim", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="confirm_reset_sim")
        b_nao = Button(label="Não", style=discord.ButtonStyle.secondary, custom_id="confirm_reset_nao")
        b_sim.callback = self._sim
        b_nao.callback = self._nao
        row.add_item(b_sim); row.add_item(b_nao)
        c.add_item(row)
        self.add_item(c)
    async def _sim(self, interaction):
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
    async def _nao(self, interaction):
        await interaction.response.send_message("❌ Cancelado.", ephemeral=True); self.stop()

class ConfirmarFechamentoView(LayoutView):
    def __init__(self, gid, uid, canal):
        super().__init__(timeout=60)
        self.gid = gid; self.uid = uid; self.canal = canal
        c = Container(accent_color=0xFF0000)
        c.add_item(TextDisplay("⚠️ **Fechar este canal?**\nTodos os dados vinculados serão removidos."))
        c.add_item(Separator())
        row = ActionRow()
        b_sim = Button(label="Sim", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="fechar_canal_sim")
        b_nao = Button(label="Não", style=discord.ButtonStyle.secondary, custom_id="fechar_canal_nao")
        b_sim.callback = self._sim
        b_nao.callback = self._nao
        row.add_item(b_sim); row.add_item(b_nao)
        c.add_item(row)
        self.add_item(c)
    async def _sim(self, interaction):
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
    async def _nao(self, interaction):
        await interaction.response.send_message("❌ Cancelado.", ephemeral=True); self.stop()

class ConfirmarResetView(LayoutView):
    def __init__(self, gid):
        super().__init__(timeout=60); self.gid = gid
        c = Container(accent_color=0xFF0000)
        c.add_item(TextDisplay("⚠️ **Resetar o ranking do servidor?**\nUm backup será criado automaticamente."))
        c.add_item(Separator())
        row = ActionRow()
        b_sim = Button(label="Sim", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="reset_rank_sim")
        b_nao = Button(label="Não", style=discord.ButtonStyle.secondary, custom_id="reset_rank_nao")
        b_sim.callback = self._sim
        b_nao.callback = self._nao
        row.add_item(b_sim); row.add_item(b_nao)
        c.add_item(row)
        self.add_item(c)
    async def _sim(self, interaction):
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
    async def _nao(self, interaction):
        await interaction.response.send_message("❌ Cancelado.", ephemeral=True); self.stop()

# ==================== LOGS E BACKUP ====================
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
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("💾 **Backup Salvo**"))
        c.add_item(Separator())
        c.add_item(TextDisplay(f"Arquivo: `{os.path.basename(nome)}`\nData: {backup_data['data_backup']}"))
        layout.add_item(c)
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
        "criar_canal": 0x2C2F33, "registrar_farm": 0x2C2F33, "registrar_dinheiro_sujo": 0x4F545C,
        "pagar": 0x99AAB5, "fechar_canal": 0x4F545C, "fechar_caixa": 0x99AAB5,
        "reset_rank": 0x4F545C, "compra_venda": 0x2C2F33, "editar_farm": 0x2C2F33,
        "editar_dinheiro_sujo": 0x2C2F33
    }
    cor_final = cores.get(acao, 0x2C2F33) if cor is None else cor
    layout = LayoutView()
    c = Container(accent_color=cor_final)
    c.add_item(TextDisplay(f"📌 **LOG: {acao.upper()}**"))
    c.add_item(Separator())
    c.add_item(TextDisplay(detalhes))
    if usuario:
        c.add_item(Separator())
        c.add_item(TextDisplay(f"Autor: **{usuario.name}**"))
    layout.add_item(c)
    try:
        await canal.send(view=layout)
    except: pass

async def log_admin(gid, titulo, descricao, cor=0x99AAB5):
    if not gid: return
    canal = await get_configured_channel(gid, 'canal_admin_logs_id')
    if canal:
        layout = LayoutView()
        c = Container(accent_color=cor)
        c.add_item(TextDisplay(f"**{titulo}**"))
        c.add_item(Separator())
        c.add_item(TextDisplay(descricao))
        layout.add_item(c)
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

# ==================== RANKING ====================
class RankingView(LayoutView):
    def __init__(self, gid=None):
        super().__init__(timeout=None)
        self.gid = gid
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("🏆 **RANKING DO SERVIDOR**"))
        c.add_item(Separator())
        c.add_item(TextDisplay("Use os botões abaixo para gerenciar."))
        row = ActionRow()
        b1 = Button(label="Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="rank_atualizar")
        b2 = Button(label="Resetar", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="rank_resetar")
        b1.callback = self._atualizar
        b2.callback = self._resetar
        row.add_item(b1); row.add_item(b2)
        c.add_item(row)
        self.add_item(c)
    async def _atualizar(self, interaction):
        await interaction.response.defer()
        await atualizar_ranking(interaction.guild.id)
        await interaction.followup.send("✅ Ranking atualizado!", ephemeral=True)
    async def _resetar(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        view = ConfirmarResetView(interaction.guild.id)
        await interaction.response.send_message(view=view, ephemeral=True)

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
    total_farms = 0
    total_ds = 0.0
    for uid, data in dados["usuarios"].get(str(gid), {}).items():
        if "removido_em" in data: continue
        try: await bot.fetch_user(int(uid))
        except: continue
        produtos_por_usuario[uid] = {prod: 0 for prod in produtos_config}
        farms = data.get("farms", [])
        total_farms += len(farms)
        for farm in farms:
            for p in farm.get("produtos", []):
                nome_prod = p.get("produto", "")
                if nome_prod in produtos_config:
                    qtd = p.get("quantidade", 0)
                    produtos_por_usuario[uid][nome_prod] += qtd
                    totais_produtos[nome_prod] += qtd
        total_ds += data.get("dinheiro_sujo", 0)

    layout = LayoutView()
    c = Container(accent_color=0x2C2F33)
    c.add_item(TextDisplay("# 🏆 RANKING DO SERVIDOR"))
    c.add_item(TextDisplay(f"Total de farms: **{total_farms}** | Dinheiro sujo total: **R$ {total_ds:,.2f}**"))
    c.add_item(Separator(spacing=discord.SeparatorSpacing.large))

    produtos_ordenados = sorted(totais_produtos.items(), key=lambda x: x[1], reverse=True)[:5]
    for idx, (nome_prod, _) in enumerate(produtos_ordenados):
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
        c.add_item(TextDisplay(f"### {medalha} {nome_prod}\n{texto}"))

    c.add_item(Separator(spacing=discord.SeparatorSpacing.large))
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
    c.add_item(TextDisplay(f"### 💰 TOP SALÁRIO\n{txt}"))

    c.add_item(Separator(spacing=discord.SeparatorSpacing.large))
    lista_sujo = sorted(usuarios, key=lambda x: x["din_sujo"], reverse=True)[:5]
    txt = "\n".join(
        f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'{i+1}°'} **{u['nome']}** - R$ {u['din_sujo']:,.2f}"
        for i,u in enumerate(lista_sujo) if u['din_sujo']>0
    ) or "Nenhum"
    c.add_item(TextDisplay(f"### 💀 DINHEIRO SUJO\n{txt}"))

    c.add_item(Separator())
    row = ActionRow()
    b1 = Button(label="Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="rank_atualizar")
    b2 = Button(label="Resetar", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="rank_resetar")
    async def at(inter):
        await inter.response.defer()
        await atualizar_ranking(gid)
        await inter.followup.send("✅ Ranking atualizado!", ephemeral=True)
    async def rs(inter):
        if not is_admin(inter.user):
            await inter.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        v = ConfirmarResetView(gid)
        await inter.response.send_message(view=v, ephemeral=True)
    b1.callback = at; b2.callback = rs
    row.add_item(b1); row.add_item(b2)
    c.add_item(row)
    layout.add_item(c)
    try:
        await canal.send(view=layout)
    except: pass

# ==================== BOTÃO CRIAR CANAL ====================
class BotaoCriarCanalView(LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("# 🔓 CRIAR SEU CANAL PRIVADO"))
        c.add_item(TextDisplay("Crie seu canal exclusivo para gerenciar seus farms com privacidade e organização."))
        c.add_item(Separator(spacing=discord.SeparatorSpacing.large))
        c.add_item(TextDisplay(
            "🎯 **O que você ganha?**\n"
            "• 📦 **Registrar farms** de produtos com cálculo de valor estimado\n"
            "• 💰 **Registrar dinheiro sujo** com totalização automática\n"
            "• ✏️ **Editar** registros antigos (farms e depósitos)\n"
            "• 📋 **Visualizar seu histórico completo**\n"
            "• 📊 **Fechar caixa** (administradores) com divisão automática\n"
            "• Seu canal é **privado**."
        ))
        c.add_item(Separator())
        row = ActionRow()
        b = Button(label="🔓 Criar Meu Canal Privado", style=discord.ButtonStyle.success,
                   emoji="🔓", custom_id="criar_canal_privado")
        b.callback = self._criar
        row.add_item(b)
        c.add_item(row)
        self.add_item(c)
    async def _criar(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        gid = interaction.guild.id
        cat_id = get_guild_setting(gid, 'categoria_farms_id')
        if not cat_id:
            await interaction.followup.send("❌ Categoria não configurada.", ephemeral=True); return
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
        # Adiciona TODOS os cargos admin configurados
        for rid in _parse_ids(get_guild_setting(gid, 'cargo_00_id')):
            cargo = interaction.guild.get_role(rid)
            if cargo:
                overwrites[cargo] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        nome = f"farm-{interaction.user.name}".lower().replace(" ", "-")[:90]
        canal = await categoria.create_text_channel(nome, overwrites=overwrites)
        if str(gid) not in dados["canais"]:
            dados["canais"][str(gid)] = {}
        dados["canais"][str(gid)][str(interaction.user.id)] = canal.id
        salvar_dados()
        await enviar_painel_canal(canal, gid, interaction.user.id, interaction.user.name)
        await log_acao(gid, "criar_canal", interaction.user, f"Canal {canal.mention} criado")
        await interaction.followup.send(f"✅ Canal criado: {canal.mention}", ephemeral=True)
        await atualizar_ranking(gid)

# ==================== PAINEL DO CANAL PRIVADO ====================
async def enviar_painel_canal(canal, gid, uid, uname):
    view = FarmChannelView(gid, uid, uname)
    user_data = dados["usuarios"].get(str(gid), {}).get(str(uid), {})
    qtd_farms = len(user_data.get("farms", []))
    ds = user_data.get("dinheiro_sujo", 0)

    layout = LayoutView(timeout=None)
    c = Container(accent_color=0x2C2F33)
    c.add_item(TextDisplay(f"# 🔐 CANAL PRIVADO\n<@{uid}> bem-vindo!"))
    c.add_item(Separator(spacing=discord.SeparatorSpacing.large))
    c.add_item(TextDisplay(
        f"**📊 Resumo**\n"
        f"Criado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        f"Farms registrados: **{qtd_farms}**\n"
        f"Dinheiro sujo: **R$ {ds:,.2f}**"
    ))
    c.add_item(Separator())
    c.add_item(TextDisplay(
        "**🎯 Ações disponíveis**\n"
        "• 📦 Farm Produtos\n• 💰 Farm Dinheiro Sujo\n• ✏️ Editar Registro\n"
        "• 📊 Fechar Caixa\n• ✏️ Mudar Nome\n• 📜 Histórico Caixa\n"
        "• 📋 Meus Registros\n• 🔄 Reset Semanal\n• 🗑️ Fechar Canal"
    ))
    c.add_item(Separator())

    row1 = ActionRow()
    b1 = Button(label="📦 Farm Produtos", style=discord.ButtonStyle.secondary, custom_id="farm_produtos")
    b2 = Button(label="💰 Farm Dinheiro Sujo", style=discord.ButtonStyle.secondary, custom_id="farm_dinheiro")
    b3 = Button(label="✏️ Editar Registro", style=discord.ButtonStyle.secondary, custom_id="farm_editar")
    b1.callback = view.cb_produtos
    b2.callback = view.cb_dinheiro
    b3.callback = view.cb_editar
    row1.add_item(b1); row1.add_item(b2); row1.add_item(b3)
    c.add_item(row1)

    row2 = ActionRow()
    b4 = Button(label="📊 Fechar Caixa", style=discord.ButtonStyle.secondary, custom_id="farm_fechar_caixa")
    b5 = Button(label="✏️ Mudar Nome", style=discord.ButtonStyle.secondary, custom_id="farm_mudar_nome")
    b6 = Button(label="📜 Histórico", style=discord.ButtonStyle.secondary, custom_id="farm_historico")
    b4.callback = view.cb_fechar_caixa
    b5.callback = view.cb_mudar_nome
    b6.callback = view.cb_historico
    row2.add_item(b4); row2.add_item(b5); row2.add_item(b6)
    c.add_item(row2)

    row3 = ActionRow()
    b7 = Button(label="📋 Meus Registros", style=discord.ButtonStyle.primary, custom_id="farm_meus_registros")
    b8 = Button(label="🔄 Reset Semanal", style=discord.ButtonStyle.danger, custom_id="farm_reset_semanal")
    b9 = Button(label="🗑️ Fechar Canal", style=discord.ButtonStyle.danger, custom_id="farm_fechar_canal")
    b7.callback = view.cb_meus_registros
    b8.callback = view.cb_reset_semanal
    b9.callback = view.cb_fechar_canal
    row3.add_item(b7); row3.add_item(b8); row3.add_item(b9)
    c.add_item(row3)

    layout.add_item(c)
    await canal.send(view=layout)

class FarmChannelView(LayoutView):
    def __init__(self, gid, user_id, user_name):
        super().__init__(timeout=None)
        self.gid = gid; self.user_id = user_id; self.user_name = user_name

    async def cb_produtos(self, interaction):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas o dono do canal.", ephemeral=True); return
        await interaction.response.send_modal(FarmProdutosModal(self.gid, self.user_id, self.user_name, interaction.channel))

    async def cb_dinheiro(self, interaction):
        if not (is_admin(interaction.user) or is_membro(interaction.user)):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(DinheiroSujoModal(self.gid, self.user_id, self.user_name, interaction.channel))

    async def cb_editar(self, interaction):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        view = EscolherTipoEdicaoView(self.gid, self.user_id, self.user_name)
        await interaction.response.send_message(view=view, ephemeral=True)

    async def cb_fechar_caixa(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        user_data = dados["usuarios"].get(str(self.gid), {}).get(str(self.user_id), {})
        total_sujo = user_data.get("dinheiro_sujo", 0)
        if total_sujo <= 0:
            await interaction.followup.send("ℹ️ Nenhum dinheiro sujo acumulado.", ephemeral=True); return
        t_lav = get_taxa(self.gid, 'taxa_lavagem', 0.25)
        t_fac = get_taxa(self.gid, 'taxa_faccao', 0.60)
        t_mem = get_taxa(self.gid, 'taxa_membro', 0.40)
        lavagem = total_sujo * t_lav
        restante = total_sujo - lavagem
        faccao = restante * t_fac
        membro = restante * t_mem

        layout = LayoutView()
        c = Container(accent_color=0x99AAB5)
        c.add_item(TextDisplay(f"# 📊 RESUMO DO FECHAMENTO\n**Usuário:** {self.user_name}"))
        c.add_item(Separator())
        c.add_item(TextDisplay(
            f"💰 Total farmado: **R$ {total_sujo:,.2f}**\n"
            f"🧼 Lavagem ({int(t_lav*100)}%): **R$ {lavagem:,.2f}**\n"
            f"⚔️ Facção ({int(t_fac*100)}%): **R$ {faccao:,.2f}**\n"
            f"👤 Membro ({int(t_mem*100)}%): **R$ {membro:,.2f}**"
        ))
        c.add_item(Separator())
        row = ActionRow()
        b = Button(label="Continuar", style=discord.ButtonStyle.success, custom_id="fechamento_continuar")
        b.callback = self.cb_continuar_fechamento
        row.add_item(b)
        c.add_item(row)
        layout.add_item(c)
        await interaction.followup.send(view=layout)

    async def cb_continuar_fechamento(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        user_data = dados["usuarios"].get(str(self.gid), {}).get(str(self.user_id), {})
        total_sujo = user_data.get("dinheiro_sujo", 0)
        t_lav = get_taxa(self.gid, 'taxa_lavagem', 0.25)
        t_fac = get_taxa(self.gid, 'taxa_faccao', 0.60)
        t_mem = get_taxa(self.gid, 'taxa_membro', 0.40)
        lavagem = total_sujo * t_lav
        restante = total_sujo - lavagem
        faccao = restante * t_fac
        membro = restante * t_mem
        modal = FechamentoCaixaModal(self.gid, self.user_id, self.user_name,
                                     interaction.channel, total_sujo, lavagem, faccao, membro)
        await interaction.response.send_modal(modal)

    async def cb_mudar_nome(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        await interaction.response.send_modal(MudarNomeModal(interaction.channel))

    async def cb_historico(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        fechamentos = dados["caixa_semana"].get(str(self.gid), {}).get(str(self.user_id), [])
        if not fechamentos:
            await interaction.followup.send("ℹ️ Nenhum fechamento registrado.", ephemeral=True); return
        layout = LayoutView()
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("# 📜 Histórico de Caixa"))
        c.add_item(Separator())
        for f in fechamentos[-10:]:
            data = datetime.strptime(f["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            txt = f"**{data}**\nMeta: {f.get('meta_farm','?')}\nPago: R$ {f['dinheiro_sujo']['pago']:,.2f}"
            if f.get('observacao'): txt += f"\nObs: {f['observacao']}"
            c.add_item(TextDisplay(txt))
            c.add_item(Separator())
        layout.add_item(c)
        await interaction.followup.send(view=layout, ephemeral=True)

    async def cb_meus_registros(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await enviar_historico_detalhado(interaction, self.gid, self.user_id, self.user_name)

    async def cb_reset_semanal(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        view = ConfirmResetSemanalView(self.gid, self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_message(view=view, ephemeral=True)

    async def cb_fechar_canal(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        view = ConfirmarFechamentoView(self.gid, self.user_id, interaction.channel)
        await interaction.response.send_message(view=view, ephemeral=True)

# ==================== MODAIS DE FARM ====================
class FarmProdutosModal(Modal, title="Registrar Farm Produtos"):
    def __init__(self, gid, uid, uname, canal):
        super().__init__()
        self.gid = gid; self.uid = uid; self.uname = uname; self.canal = canal
        settings = bot.guild_settings.get(gid, {})
        prods = [
            settings.get('nome_produto1', 'CHUMBO'), settings.get('nome_produto2', 'CAPSULA'),
            settings.get('nome_produto3', 'POLVORA'), settings.get('produto4_nome', ''),
            settings.get('produto5_nome', ''), settings.get('produto6_nome', ''),
            settings.get('produto7_nome', ''), settings.get('produto8_nome', ''),
            settings.get('produto9_nome', ''), settings.get('produto10_nome', '')
        ]
        prods = [p for p in prods if p and p.strip()][:5]
        for p in prods:
            self.add_item(TextInput(label=p[:45], required=False))
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        produtos = []
        for campo in self.children:
            if campo.value is not None and campo.value.strip():
                try:
                    q = int(campo.value.strip())
                    if q > 0: produtos.append({"produto": campo.label, "quantidade": q})
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
            dados["usuarios"][gid_str][uid_str] = {"farms": [], "pagamentos": [], "nome": self.uname,
                                                   "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
        farm = {"produtos": produtos, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "print_url": img, "validado": True,
                "farm_id": len(dados["usuarios"][gid_str][uid_str]["farms"]) + 1}
        dados["usuarios"][gid_str][uid_str]["farms"].append(farm)
        salvar_dados()
        valor = calcular_valor_estimado(self.gid, produtos)
        total_itens = sum(p["quantidade"] for p in produtos)

        layout = LayoutView()
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay(f"# 📦 Farm Registrada\nUsuário: <@{self.uid}>"))
        c.add_item(Separator())
        c.add_item(TextDisplay("**Produtos:**\n" + "\n".join(f"• {p['produto']}: {p['quantidade']}" for p in produtos)))
        c.add_item(Separator())
        c.add_item(TextDisplay(f"📊 Total de itens: **{total_itens}**\n💰 Valor estimado: **R$ {valor:,.2f}**"))
        c.add_item(Separator())
        c.add_item(MediaGallery(items=[discord.MediaGalleryItem(url=img)]))
        c.add_item(TextDisplay(f"*Farm #{farm['farm_id']}*"))
        layout.add_item(c)

        try: await self.canal.send(view=layout)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(view=layout)
            except: pass
        await interaction.followup.send("✅ Farm registrada!", ephemeral=True)
        await log_acao(self.gid, "registrar_farm", interaction.user,
                       f"Valor estimado: R$ {valor:,.2f}")
        await atualizar_ranking(self.gid)

class DinheiroSujoModal(Modal, title="Registrar Dinheiro Sujo"):
    valor = TextInput(label="Valor (R$)", required=True)
    def __init__(self, gid, uid, uname, canal):
        super().__init__()
        self.gid = gid; self.uid = uid; self.uname = uname; self.canal = canal
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
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
            dados["usuarios"][gid_str][uid_str] = {"farms": [], "pagamentos": [], "nome": self.uname,
                                                   "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
        trans = {"valor": val, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 "print_url": img, "registrado_por": interaction.user.id}
        dados["usuarios"][gid_str][uid_str]["transacoes_dinheiro_sujo"].append(trans)
        novo_total = sum(t["valor"] for t in dados["usuarios"][gid_str][uid_str]["transacoes_dinheiro_sujo"])
        dados["usuarios"][gid_str][uid_str]["dinheiro_sujo"] = novo_total
        salvar_dados()

        layout = LayoutView()
        c = Container(accent_color=0x4F545C)
        c.add_item(TextDisplay(f"# 💰 Dinheiro Sujo\nUsuário: <@{self.uid}>"))
        c.add_item(Separator())
        c.add_item(TextDisplay(f"Valor: **R$ {val:,.2f}**\nNovo total: **R$ {novo_total:,.2f}**"))
        c.add_item(MediaGallery(items=[discord.MediaGalleryItem(url=img)]))
        layout.add_item(c)

        try: await self.canal.send(view=layout)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(view=layout)
            except: pass
        await interaction.followup.send(f"✅ R$ {val:,.2f} registrado!", ephemeral=True)
        await log_acao(self.gid, "registrar_dinheiro_sujo", interaction.user, f"R$ {val:,.2f}")
        await atualizar_ranking(self.gid)

class FechamentoCaixaModal(Modal, title="Finalizar Fechamento"):
    meta = TextInput(label="Meta (Sim/Não)", required=True)
    bonus = TextInput(label="Bônus (R$)", default="0", required=False)
    obs = TextInput(label="Observação", required=False, style=discord.TextStyle.long)
    def __init__(self, gid, uid, uname, canal, total, lavagem, faccao, membro):
        super().__init__()
        self.gid = gid; self.uid = uid; self.uname = uname; self.canal = canal
        self.total = total; self.lavagem = lavagem; self.faccao = faccao; self.membro = membro
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        meta_str = self.meta.value.lower()
        if meta_str not in ["sim", "não", "nao"]:
            await interaction.followup.send("❌ Meta inválida.", ephemeral=True); return
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
            dados["usuarios"][gid_str][uid_str] = {"farms": [], "pagamentos": [], "nome": self.uname,
                                                   "dinheiro_sujo": 0, "transacoes_dinheiro_sujo": []}
        dados["usuarios"][gid_str][uid_str]["pagamentos"].append({
            "valor": pagamento, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.id, "tipo": "Fechamento de Caixa",
            "detalhes": {"total": self.total, "lavagem": self.lavagem, "faccao": self.faccao,
                         "membro": self.membro, "bonus": bonus_val},
            "print_url": img
        })
        fech = {"data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "admin": interaction.user.name, "usuario": self.uname, "meta_farm": meta,
                "dinheiro_sujo": {"total": self.total, "lavagem": self.lavagem,
                                  "faccao": self.faccao, "membro_base": self.membro,
                                  "bonus": bonus_val, "pago": pagamento},
                "print_url": img, "observacao": obs_text}
        if gid_str not in dados["caixa_semana"]: dados["caixa_semana"][gid_str] = {}
        if uid_str not in dados["caixa_semana"][gid_str]: dados["caixa_semana"][gid_str][uid_str] = []
        dados["caixa_semana"][gid_str][uid_str].append(fech)
        salvar_dados()

        layout = LayoutView()
        c = Container(accent_color=0x99AAB5)
        c.add_item(TextDisplay(f"# 📊 Caixa Fechado\n**Usuário:** {self.uname}"))
        c.add_item(Separator())
        c.add_item(TextDisplay(
            f"Meta: **{meta}**\nPagamento final: **R$ {pagamento:,.2f}**"
            + (f"\nBônus: R$ {bonus_val:,.2f}" if bonus_val > 0 else "")
            + (f"\nObservação: {obs_text}" if obs_text else "")
        ))
        c.add_item(Separator())
        c.add_item(MediaGallery(items=[discord.MediaGalleryItem(url=img)]))
        c.add_item(TextDisplay(f"Admin: {interaction.user.display_name}"))
        layout.add_item(c)

        try: await self.canal.send(view=layout)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(view=layout)
            except: pass
        await interaction.followup.send(f"✅ R$ {pagamento:,.2f} registrado!", ephemeral=True)
        await log_acao(self.gid, "fechar_caixa", interaction.user, f"R$ {pagamento:,.2f} para {self.uname}")
        await atualizar_ranking(self.gid)

# ==================== EDIÇÃO ====================
class EscolherTipoEdicaoView(LayoutView):
    def __init__(self, gid, uid, uname):
        super().__init__(timeout=120)
        self.gid = gid; self.uid = uid; self.uname = uname
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("# 📝 Escolha o tipo de edição"))
        c.add_item(Separator())
        sel = Select(placeholder="O que editar?",
                     options=[
                         discord.SelectOption(label="Produtos", value="produtos", emoji="📦"),
                         discord.SelectOption(label="Dinheiro Sujo", value="dinheiro", emoji="💰"),
                     ])
        sel.callback = self._cb
        c.add_item(ActionRow(sel))
        self.add_item(c)
    async def _cb(self, interaction):
        v = interaction.data["values"][0]
        if v == "produtos":
            select = EditarRegistroSelect(self.gid, self.uid, self.uname)
            view = View(timeout=None); view.add_item(select)
            await interaction.response.send_message("📋 Selecione a farm:", view=view, ephemeral=True)
        else:
            select = EditarDinheiroSelect(self.gid, self.uid, self.uname)
            view = View(timeout=None); view.add_item(select)
            await interaction.response.send_message("💰 Selecione o depósito:", view=view, ephemeral=True)

class EditarRegistroSelect(Select):
    def __init__(self, gid, uid, uname):
        self.gid = gid; self.uid = str(uid); self.uname = uname
        farms = dados["usuarios"].get(str(gid), {}).get(self.uid, {}).get("farms", [])
        options = []
        for i, f in enumerate(farms):
            opts = ", ".join(f"{p['produto']}:{p['quantidade']}" for p in f["produtos"])
            options.append(discord.SelectOption(label=f"Farm {f.get('farm_id',i+1)} - {opts[:80]}", value=str(i)))
        if not options: options.append(discord.SelectOption(label="Nenhum registro", value="none"))
        super().__init__(options=options[:25])
    async def callback(self, interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message("ℹ️ Nenhum farm.", ephemeral=True)
        idx = int(self.values[0])
        farm = dados["usuarios"][str(self.gid)][self.uid]["farms"][idx]
        await interaction.response.send_modal(EditarFarmModal(self.gid, self.uid, self.uname, interaction.channel, idx, farm))

class EditarFarmModal(Modal, title="Editar Farm"):
    def __init__(self, gid, uid, uname, canal, idx, farm):
        super().__init__()
        self.gid = gid; self.uid = uid; self.uname = uname; self.canal = canal; self.idx = idx; self.farm = farm
        settings = bot.guild_settings.get(gid, {})
        nomes = [
            settings.get('nome_produto1', 'CHUMBO'), settings.get('nome_produto2', 'CAPSULA'),
            settings.get('nome_produto3', 'POLVORA'), settings.get('produto4_nome', ''),
            settings.get('produto5_nome', '')
        ]
        nomes = [n for n in nomes if n and n.strip()][:5]
        self.campos = []
        for nome in nomes:
            inp = TextInput(label=nome[:45], required=False)
            for p in farm["produtos"]:
                if p["produto"] == nome:
                    inp.default = str(p["quantidade"])
            self.add_item(inp)
            self.campos.append((nome, inp))
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        novos = []
        for nome, campo in self.campos:
            if campo.value is not None and campo.value.strip():
                try:
                    q = int(campo.value.strip())
                    if q > 0: novos.append({"produto": nome, "quantidade": q})
                except: pass
        if not novos:
            await interaction.followup.send("❌ Nenhum produto válido.", ephemeral=True); return
        await interaction.followup.send("📸 Envie a nova print.", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == self.canal and m.attachments
        try: msg = await bot.wait_for('message', timeout=60, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tempo esgotado.", ephemeral=True); return
        img = msg.attachments[0].url
        novo_reg = {"produtos": novos, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "print_url": img, "validado": True,
                    "farm_id": self.farm.get("farm_id", self.idx + 1)}
        dados["usuarios"][str(self.gid)][self.uid]["farms"][self.idx] = novo_reg
        salvar_dados()
        valor = calcular_valor_estimado(self.gid, novos)

        layout = LayoutView()
        c = Container(accent_color=0x99AAB5)
        c.add_item(TextDisplay(f"# ✏️ Farm Editada\nUsuário: <@{self.uid}>"))
        c.add_item(Separator())
        c.add_item(TextDisplay("**Novos produtos:**\n" + "\n".join(f"• {p['produto']}: {p['quantidade']}" for p in novos)))
        c.add_item(TextDisplay(f"Valor estimado: **R$ {valor:,.2f}**"))
        c.add_item(MediaGallery(items=[discord.MediaGalleryItem(url=img)]))
        layout.add_item(c)

        try: await self.canal.send(view=layout)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(view=layout)
            except: pass
        await interaction.followup.send("✅ Farm editada!", ephemeral=True)
        await atualizar_ranking(self.gid)

class EditarDinheiroSelect(Select):
    def __init__(self, gid, uid, uname):
        self.gid = gid; self.uid = str(uid); self.uname = uname
        trans = dados["usuarios"].get(str(gid), {}).get(self.uid, {}).get("transacoes_dinheiro_sujo", [])
        options = [discord.SelectOption(label=f"R$ {t['valor']:,.2f} - {t['data']}", value=str(i))
                   for i, t in enumerate(trans)]
        if not options: options.append(discord.SelectOption(label="Nenhum depósito", value="none"))
        super().__init__(options=options[:25])
    async def callback(self, interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message("ℹ️ Nenhum depósito.", ephemeral=True)
        idx = int(self.values[0])
        trans = dados["usuarios"][str(self.gid)][self.uid]["transacoes_dinheiro_sujo"][idx]
        await interaction.response.send_modal(EditarDinheiroModal(self.gid, self.uid, self.uname, interaction.channel, idx, trans))

class EditarDinheiroModal(Modal, title="Editar Dinheiro Sujo"):
    novo_valor = TextInput(label="Novo valor (R$)", required=True)
    def __init__(self, gid, uid, uname, canal, idx, trans):
        super().__init__()
        self.gid = gid; self.uid = uid; self.uname = uname; self.canal = canal
        self.idx = idx; self.trans = trans
        self.novo_valor.default = str(trans["valor"])
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: val = float(self.novo_valor.value.replace(",", "."))
        except:
            await interaction.followup.send("❌ Valor inválido.", ephemeral=True); return
        if val <= 0:
            await interaction.followup.send("❌ O valor deve ser > 0.", ephemeral=True); return
        await interaction.followup.send("📸 Envie a nova print.", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == self.canal and m.attachments
        try: msg = await bot.wait_for('message', timeout=60, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Tempo esgotado.", ephemeral=True); return
        img = msg.attachments[0].url
        nova = {"valor": val, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "print_url": img, "registrado_por": interaction.user.id}
        dados["usuarios"][str(self.gid)][self.uid]["transacoes_dinheiro_sujo"][self.idx] = nova
        novo_total = sum(t["valor"] for t in dados["usuarios"][str(self.gid)][self.uid]["transacoes_dinheiro_sujo"])
        dados["usuarios"][str(self.gid)][self.uid]["dinheiro_sujo"] = novo_total
        salvar_dados()

        layout = LayoutView()
        c = Container(accent_color=0x99AAB5)
        c.add_item(TextDisplay(f"# 💰 Depósito Editado\nUsuário: <@{self.uid}>"))
        c.add_item(Separator())
        c.add_item(TextDisplay(
            f"Antigo valor: R$ {self.trans['valor']:,.2f}\n"
            f"Novo valor: R$ {val:,.2f}\n"
            f"Novo total: R$ {novo_total:,.2f}"
        ))
        c.add_item(MediaGallery(items=[discord.MediaGalleryItem(url=img)]))
        layout.add_item(c)

        try: await self.canal.send(view=layout)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(view=layout)
            except: pass
        await interaction.followup.send("✅ Depósito editado!", ephemeral=True)
        await atualizar_ranking(self.gid)

async def enviar_historico_detalhado(interaction, gid, uid, uname):
    user_data = dados["usuarios"].get(str(gid), {}).get(str(uid), {})
    farms = user_data.get("farms", [])
    trans = user_data.get("transacoes_dinheiro_sujo", [])
    pagamentos = user_data.get("pagamentos", [])
    if not farms and not trans and not pagamentos:
        await interaction.followup.send("ℹ️ Nenhum registro encontrado.", ephemeral=True); return

    layout = LayoutView()
    c = Container(accent_color=0x2C2F33)
    c.add_item(TextDisplay(f"# 📋 Histórico de {uname}"))
    c.add_item(Separator(spacing=discord.SeparatorSpacing.large))

    if farms:
        c.add_item(TextDisplay("## 📦 Farms"))
        for f in farms[-10:]:
            data = datetime.strptime(f["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            prods = ", ".join(f"{p['produto']}:{p['quantidade']}" for p in f["produtos"])
            valor = calcular_valor_estimado(gid, f["produtos"])
            c.add_item(TextDisplay(f"**{data}** — Farm #{f.get('farm_id','?')}\n{prods} (R$ {valor:,.2f})"))
        c.add_item(Separator())

    if trans:
        total_ds = user_data.get("dinheiro_sujo", 0)
        c.add_item(TextDisplay(f"## 💰 Dinheiro Sujo (total: R$ {total_ds:,.2f})"))
        for t in trans[-10:]:
            data = datetime.strptime(t["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            c.add_item(TextDisplay(f"**{data}** — R$ {t['valor']:,.2f}"))
        c.add_item(Separator())

    if pagamentos:
        c.add_item(TextDisplay("## 💵 Pagamentos Recebidos"))
        for p in pagamentos[-10:]:
            data = datetime.strptime(p["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            c.add_item(TextDisplay(f"**{data}** — R$ {p['valor']:,.2f} ({p.get('tipo','Pagamento')})"))

    layout.add_item(c)
    await interaction.followup.send(view=layout, ephemeral=True)

# ==================== COMPRA / VENDA ====================
class VendaModal(Modal, title="Venda de Munição"):
    tipo = TextInput(label="Tipos (ex: PISTOLA,SUB)", required=True)
    qtd = TextInput(label="Qtds (ex: 10,20)", required=True)
    valor = TextInput(label="Valores (R$) (ex:1000,2000)", required=True)
    faccao = TextInput(label="Facção compradora", required=True)
    valor_total = TextInput(label="Valor Total da Venda (R$)", required=True)
    def __init__(self, gid):
        super().__init__(); self.gid = gid
    async def on_submit(self, interaction):
        if not pode_comprar_vender(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            tipos = [t.strip().upper() for t in self.tipo.value.replace('/', ',').split(',') if t.strip()]
            qtds = [int(q.strip()) for q in self.qtd.value.replace('/', ',').split(',') if q.strip().isdigit()]
            valores = [float(v.strip().replace(',', '.')) for v in self.valor.value.replace('/', ',').split(',') if v.strip()]
            total = float(self.valor_total.value.replace(',', '.'))
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True); return
        if not all([tipos, qtds, valores]) or not (len(tipos) == len(qtds) == len(valores)):
            await interaction.followup.send("❌ Preencha corretamente.", ephemeral=True); return
        itens = [{"tipo": t, "quantidade": q, "valor": v} for t, q, v in zip(tipos, qtds, valores)]
        registro = {"tipo": "venda", "itens": itens, "faccao_compradora": self.faccao.value,
                    "valor_total_venda": total, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "responsavel": interaction.user.name}
        if str(self.gid) not in dados["compras_vendas"]: dados["compras_vendas"][str(self.gid)] = []
        dados["compras_vendas"][str(self.gid)].append(registro)
        salvar_dados()
        canal = await get_configured_channel(self.gid, 'canal_logs_compra_venda_id')
        if canal:
            layout = LayoutView()
            c = Container(accent_color=0x2C2F33)
            c.add_item(TextDisplay("# 💸 Venda registrada"))
            c.add_item(Separator())
            c.add_item(TextDisplay(
                f"**Facção:** {self.faccao.value}\n**Total:** R$ {total:,.2f}\n**Itens:**\n"
                + "\n".join(f"• {i['tipo']} x{i['quantidade']} — R$ {i['valor']:,.2f}" for i in itens)
                + f"\n\n*Por {interaction.user.display_name}*"
            ))
            layout.add_item(c)
            try: await canal.send(view=layout)
            except: pass
        await interaction.followup.send(f"✅ Venda registrada com {len(itens)} item(ns)!", ephemeral=True)

class CompraModal(Modal, title="Compra de Produto"):
    produto = TextInput(label="Produto", required=True)
    qtd = TextInput(label="Quantidade", required=True)
    valor = TextInput(label="Valor Total (R$)", required=True)
    faccao = TextInput(label="Facção vendedora", required=True)
    responsavel = TextInput(label="Responsável", required=True)
    def __init__(self, gid):
        super().__init__(); self.gid = gid
    async def on_submit(self, interaction):
        if not pode_comprar_vender(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            q = int(self.qtd.value); v = float(self.valor.value.replace(",", "."))
        except:
            await interaction.followup.send("❌ Valores inválidos.", ephemeral=True); return
        registro = {"tipo": "compra", "produto": self.produto.value, "quantidade": q, "valor_total": v,
                    "faccao_vendedora": self.faccao.value, "responsavel": self.responsavel.value,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        if str(self.gid) not in dados["compras_vendas"]: dados["compras_vendas"][str(self.gid)] = []
        dados["compras_vendas"][str(self.gid)].append(registro)
        salvar_dados()
        canal = await get_configured_channel(self.gid, 'canal_logs_compra_venda_id')
        if canal:
            layout = LayoutView()
            c = Container(accent_color=0x2C2F33)
            c.add_item(TextDisplay("# 🛒 Compra registrada"))
            c.add_item(Separator())
            c.add_item(TextDisplay(
                f"**Produto:** {self.produto.value}\n**Qtd:** {q}\n**Valor:** R$ {v:,.2f}\n"
                f"**Facção:** {self.faccao.value}\n**Responsável:** {self.responsavel.value}\n\n*Por {interaction.user.display_name}*"
            ))
            layout.add_item(c)
            try: await canal.send(view=layout)
            except: pass
        await interaction.followup.send("✅ Compra registrada!", ephemeral=True)

class CompraVendaView(LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("# 💸 SISTEMA DE COMPRA E VENDA"))
        c.add_item(TextDisplay("Registre transações de munição e itens entre facções."))
        c.add_item(Separator(spacing=discord.SeparatorSpacing.large))
        c.add_item(TextDisplay(
            "📌 **Como usar**\n"
            "• **💸 Venda** — Tipos, quantidades, valores e facção compradora.\n"
            "• **🛒 Compra** — Produto, quantidade, valor e facção vendedora.\n"
            "• Todos os registros vão para os logs."
        ))
        c.add_item(Separator())
        row = ActionRow()
        b1 = Button(label="💸 Venda", style=discord.ButtonStyle.secondary, custom_id="compra_venda_venda")
        b2 = Button(label="🛒 Compra", style=discord.ButtonStyle.secondary, custom_id="compra_venda_compra")
        b1.callback = self._venda
        b2.callback = self._compra
        row.add_item(b1); row.add_item(b2)
        c.add_item(row)
        self.add_item(c)
    async def _venda(self, interaction):
        await interaction.response.send_modal(VendaModal(interaction.guild.id))
    async def _compra(self, interaction):
        await interaction.response.send_modal(CompraModal(interaction.guild.id))

# ==================== AÇÕES ====================
class ActionPanelView(LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("# ⚔️ SISTEMA DE AÇÕES"))
        c.add_item(TextDisplay("Registre operações e gerencie os pagamentos."))
        c.add_item(Separator(spacing=discord.SeparatorSpacing.large))
        c.add_item(TextDisplay(
            "📌 **Como funciona**\n"
            "• **⚔️ Abrir Ação** — Nome, valor, resultado e participantes.\n"
            "• **💰 Pagamento** — Calcula lavagem e divide entre os membros.\n"
            "• Os registros vão para os logs."
        ))
        c.add_item(Separator())
        row = ActionRow()
        b1 = Button(label="⚔️ Abrir Ação", style=discord.ButtonStyle.secondary, custom_id="acao_abrir")
        b2 = Button(label="💰 Pagamento", style=discord.ButtonStyle.secondary, custom_id="acao_pagamento")
        b1.callback = self._abrir
        b2.callback = self._pagamento
        row.add_item(b1); row.add_item(b2)
        c.add_item(row)
        self.add_item(c)
    async def _abrir(self, interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(ActionModal(interaction.guild.id))
    async def _pagamento(self, interaction):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        acoes = dados["acoes"].get(str(interaction.guild.id), {})
        pendentes = {k: v for k, v in acoes.items() if not v.get("pago")}
        if not pendentes:
            await interaction.followup.send("ℹ️ Nenhuma ação pendente.", ephemeral=True); return
        view = ActionSelectView(interaction.guild.id, pendentes)
        await interaction.followup.send("📋 Selecione a ação:", view=view, ephemeral=True)

class ActionModal(Modal, title="Registrar Ação"):
    nome = TextInput(label="Nome da ação", required=True)
    valor = TextInput(label="Valor (R$)", required=True)
    resultado = TextInput(label="Vitória/Derrota", required=True)
    data = TextInput(label="Data (DD/MM/AAAA)", required=True)
    def __init__(self, gid):
        super().__init__(); self.gid = gid
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: val = float(self.valor.value.replace(",", "."))
        except:
            await interaction.followup.send("❌ Valor inválido.", ephemeral=True); return
        res = self.resultado.value.lower()
        if res not in ["vitória", "vitoria", "derrota"]:
            await interaction.followup.send("❌ Resultado inválido.", ephemeral=True); return
        res = "Vitória" if res in ["vitória", "vitoria"] else "Derrota"
        try: datetime.strptime(self.data.value, "%d/%m/%Y")
        except:
            await interaction.followup.send("❌ Data inválida.", ephemeral=True); return
        info = {"nome_acao": self.nome.value, "valor": val, "resultado": res,
                "data_acao": self.data.value, "puxado_por": interaction.user.id}
        view = MemberSelectView(self.gid, info)
        await interaction.followup.send(view=view, ephemeral=True)

class MemberSelectView(LayoutView):
    def __init__(self, gid, info):
        super().__init__(timeout=120)
        self.gid = gid; self.info = info
        self.membros = [info["puxado_por"]]
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("👥 **Selecione os membros participantes**"))
        c.add_item(Separator())
        sel = UserSelect(placeholder="Membros", min_values=1, max_values=25)
        sel.callback = self._sel
        c.add_item(ActionRow(sel))
        row = ActionRow()
        b = Button(label="Confirmar", style=discord.ButtonStyle.success)
        b.callback = self._confirm
        row.add_item(b)
        c.add_item(row)
        self.add_item(c)
    async def _sel(self, interaction):
        vals = interaction.data["values"]
        self.membros = list(set([self.info["puxado_por"]] + [int(v) for v in vals]))
        await interaction.response.defer()
    async def _confirm(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        self.info["membros"] = self.membros
        await interaction.followup.send("📸 Envie as prints (digite `pronto` para terminar).", ephemeral=True)
        urls = []
        def check(m): return m.author == interaction.user and m.attachments
        while True:
            try: msg = await bot.wait_for('message', timeout=300, check=check)
            except asyncio.TimeoutError: break
            if msg.content.lower() == "pronto": break
            for att in msg.attachments:
                if att.content_type and att.content_type.startswith('image/'): urls.append(att.url)
        self.info["print_urls"] = urls; self.info["pago"] = False
        self.info["data_registro"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        aid = str(int(datetime.now().timestamp()))
        if str(self.gid) not in dados["acoes"]: dados["acoes"][str(self.gid)] = {}
        dados["acoes"][str(self.gid)][aid] = self.info
        salvar_dados()
        canal = await get_configured_channel(self.gid, 'canal_acoes_logs_id')
        if canal:
            layout = LayoutView()
            c = Container(accent_color=0x2C2F33)
            c.add_item(TextDisplay("# ⚔️ Nova Ação"))
            c.add_item(Separator())
            c.add_item(TextDisplay(
                f"**Ação:** {self.info['nome_acao']}\n"
                f"**Valor:** R$ {self.info['valor']:,.2f}\n"
                f"**Resultado:** {self.info['resultado']}\n"
                f"**Participantes:** {' '.join(f'<@{m}>' for m in self.membros)}"
            ))
            if urls:
                c.add_item(MediaGallery(items=[discord.MediaGalleryItem(url=urls[0])]))
            layout.add_item(c)
            try: await canal.send(view=layout)
            except: pass
        await interaction.followup.send("✅ Ação registrada!", ephemeral=True)
        self.stop()

class ActionSelectView(View):
    def __init__(self, gid, actions):
        super().__init__(timeout=120)
        self.add_item(ActionDropdown(gid, actions))

class ActionDropdown(Select):
    def __init__(self, gid, actions):
        self.gid = gid
        options = [discord.SelectOption(label=f"{v['nome_acao']} - R$ {v['valor']:,.0f}", value=k)
                   for k, v in actions.items()]
        super().__init__(placeholder="Escolha a ação", options=options[:25])
    async def callback(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        action = dados["acoes"][str(self.gid)][self.values[0]]
        valor = action["valor"]
        t_lav = get_taxa(self.gid, 'taxa_acao_lavagem', 0.25)
        lavagem = valor * t_lav
        liquido = valor - lavagem
        n = len(action["membros"])
        por_membro = liquido / n if n > 0 else 0

        layout = LayoutView()
        c = Container(accent_color=0x99AAB5)
        c.add_item(TextDisplay("# 📊 Resumo do Pagamento"))
        c.add_item(Separator())
        c.add_item(TextDisplay(
            f"Valor total: **R$ {valor:,.2f}**\n"
            f"Lavagem ({int(t_lav*100)}%): **R$ {lavagem:,.2f}**\n"
            f"Líquido: **R$ {liquido:,.2f}**\n"
            f"Por membro: **R$ {por_membro:,.2f}**"
        ))
        c.add_item(Separator())
        row = ActionRow()
        b = Button(label="Confirmar Pagamento", style=discord.ButtonStyle.success)
        b.callback = ConfirmPaymentView(self.gid, self.values[0], liquido, por_membro).confirm
        row.add_item(b)
        c.add_item(row)
        layout.add_item(c)
        await interaction.followup.send(view=layout, ephemeral=True)

class ConfirmPaymentView(LayoutView):
    def __init__(self, gid, aid, liquido, por_membro):
        super().__init__(timeout=120)
        self.gid = gid; self.aid = aid; self.liquido = liquido; self.por_membro = por_membro
    async def confirm(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("📸 Envie as prints (pronto para terminar).", ephemeral=True)
        urls = []
        def check(m): return m.author == interaction.user and m.attachments
        while True:
            try: msg = await bot.wait_for('message', timeout=300, check=check)
            except asyncio.TimeoutError: break
            if msg.content.lower() == "pronto": break
            for att in msg.attachments:
                if att.content_type and att.content_type.startswith('image/'): urls.append(att.url)
        action = dados["acoes"][str(self.gid)].get(self.aid)
        if action:
            action["pago"] = True
            action["pagamento"] = {"valor_liquido": self.liquido, "valor_por_membro": self.por_membro,
                                   "print_urls": urls,
                                   "data_pagamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                   "admin_id": interaction.user.id}
            salvar_dados()
            canal = await get_configured_channel(self.gid, 'canal_acoes_logs_id')
            if canal:
                layout = LayoutView()
                c = Container(accent_color=0x2C2F33)
                c.add_item(TextDisplay("# ✅ Pagamento Realizado"))
                c.add_item(Separator())
                c.add_item(TextDisplay(
                    f"**Ação:** {action['nome_acao']}\n**Valor líquido:** R$ {self.liquido:,.2f}"
                ))
                if urls:
                    c.add_item(MediaGallery(items=[discord.MediaGalleryItem(url=urls[0])]))
                layout.add_item(c)
                try: await canal.send(view=layout)
                except: pass
            await interaction.followup.send("✅ Pagamento registrado!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Ação não encontrada.", ephemeral=True)

# ==================== SET ====================
class SolicitarSetModal(Modal, title="Solicitar SET"):
    nome = TextInput(label="Seu nome", required=True)
    id_jogo = TextInput(label="ID do jogo", required=True)
    tell = TextInput(label="Tell in game", required=True)
    def __init__(self, gid):
        super().__init__(); self.gid = gid
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        self.nome_val = self.nome.value; self.id_val = self.id_jogo.value; self.tell_val = self.tell.value
        view = RecrutadorSelectView(self)
        await interaction.followup.send(view=view, ephemeral=True)

class RecrutadorSelectView(LayoutView):
    def __init__(self, modal):
        super().__init__(timeout=120)
        self.modal = modal
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("👤 **Selecione o recrutador**"))
        c.add_item(Separator())
        sel = UserSelect(placeholder="Recrutador", min_values=1, max_values=1)
        sel.callback = self._cb
        c.add_item(ActionRow(sel))
        self.add_item(c)
    async def _cb(self, interaction):
        rec_id = int(interaction.data["values"][0])
        rec = interaction.guild.get_member(rec_id)
        if not rec:
            await interaction.response.send_message("❌ Recrutador não encontrado.", ephemeral=True); return
        pid = str(int(datetime.now().timestamp()))
        if str(self.modal.gid) not in dados["sets_pendentes"]:
            dados["sets_pendentes"][str(self.modal.gid)] = {}
        dados["sets_pendentes"][str(self.modal.gid)][pid] = {
            "solicitante_id": interaction.user.id, "solicitante_nome": self.modal.nome_val,
            "id_jogo": self.modal.id_val, "tell_game": self.modal.tell_val,
            "recrutador_id": rec_id, "status": "pendente",
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        salvar_dados()
        canal = await get_configured_channel(self.modal.gid, 'canal_registros_set_id')
        if canal:
            layout = LayoutView()
            c = Container(accent_color=0x2C2F33)
            c.add_item(TextDisplay("# 📋 Nova Solicitação de SET"))
            c.add_item(Separator())
            c.add_item(TextDisplay(
                f"**Solicitante:** {self.modal.nome_val} (<@{interaction.user.id}>)\n"
                f"**ID Jogo:** {self.modal.id_val}\n**Tell:** {self.modal.tell_val}\n"
                f"**Recrutador:** {rec.mention}"
            ))
            c.add_item(TextDisplay(f"*ID: {pid}*"))
            c.add_item(Separator())
            row = ActionRow()
            b1 = Button(label="✅ Aprovar", style=discord.ButtonStyle.success, custom_id="aprovar_set_ok")
            b2 = Button(label="❌ Recusar", style=discord.ButtonStyle.danger, custom_id="aprovar_set_recusar")
            vw = AprovarSetView(self.modal.gid, pid, interaction.user.id, rec_id)
            b1.callback = vw._aprovar
            b2.callback = vw._recusar
            row.add_item(b1); row.add_item(b2)
            c.add_item(row)
            layout.add_item(c)
            try: await canal.send(view=layout)
            except: pass
        await interaction.response.send_message("✅ Solicitação enviada!", ephemeral=True)
        self.stop()

class AprovarSetView(View):
    def __init__(self, gid, pid, sol_id, rec_id):
        super().__init__(timeout=None)
        self.gid = gid; self.pid = pid; self.sol_id = sol_id; self.rec_id = rec_id
    async def _aprovar(self, interaction):
        if not pode_aprovar_set(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        pedido = dados["sets_pendentes"].get(str(self.gid), {}).get(self.pid)
        if not pedido or pedido["status"] != "pendente":
            await interaction.response.send_message("❌ Pedido já processado.", ephemeral=True); return
        view = EscolherCargoView(self.gid, self.pid, self.sol_id)
        await interaction.response.send_message(view=view, ephemeral=True)
    async def _recusar(self, interaction):
        if not pode_aprovar_set(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        pedido = dados["sets_pendentes"].get(str(self.gid), {}).get(self.pid)
        if pedido:
            pedido["status"] = "recusado"; salvar_dados()
        try:
            user = await bot.fetch_user(self.sol_id)
            await user.send(f"❌ Seu SET foi recusado por {interaction.user.mention}.")
        except: pass
        await interaction.response.send_message("❌ SET recusado.", ephemeral=True)
        try: await interaction.message.edit(view=None)
        except: pass

class EscolherCargoView(LayoutView):
    """Para aprovar SET, mostra TODOS os cargos configurados como 'cargo_membro_id'."""
    def __init__(self, gid, pid, sol_id):
        super().__init__(timeout=120)
        self.gid = gid; self.pid = pid; self.sol_id = sol_id

        membro_ids = _parse_ids(get_guild_setting(gid, 'cargo_membro_id'))
        opts = []
        for rid in membro_ids:
            role = None
            # Não temos guild aqui; placeholder — busca no cache via bot
            role = bot.get_guild(gid).get_role(rid) if bot.get_guild(gid) else None
            nome = role.name if role else f"ID {rid}"
            opts.append(discord.SelectOption(label=nome[:80], value=str(rid)))
        if not opts:
            opts = [discord.SelectOption(label="Erro: nenhum cargo configurado", value="none")]

        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("🎯 **Escolha o cargo a atribuir**"))
        c.add_item(Separator())
        sel = Select(placeholder="Cargo", options=opts[:25])
        sel.callback = self._cb
        c.add_item(ActionRow(sel))
        self.add_item(c)
    async def _cb(self, interaction):
        valor = self.children[0].children[0].values[0]
        if valor == "none":
            await interaction.response.send_message("❌ Cargo não configurado.", ephemeral=True); return
        cargo_id = int(valor)
        guild = interaction.guild
        membro = guild.get_member(self.sol_id)
        if not membro:
            await interaction.response.send_message("❌ Membro não encontrado.", ephemeral=True); return
        cargo = guild.get_role(cargo_id)
        if not cargo:
            await interaction.response.send_message("❌ Cargo não encontrado.", ephemeral=True); return
        try:
            await membro.add_roles(cargo, reason=f"SET aprovado por {interaction.user.name}")
            pedido = dados["sets_pendentes"].get(str(self.gid), {}).get(self.pid)
            if pedido:
                pedido["status"] = "aprovado"; pedido["aprovado_por"] = interaction.user.id; salvar_dados()
            try: await membro.send(f"✅ SET aprovado! Cargo {cargo.mention} atribuído.")
            except discord.Forbidden: pass
            await interaction.response.send_message(f"✅ Cargo {cargo.mention} atribuído!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)

class SetPainelView(LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("# 📋 SOLICITAÇÃO DE SET"))
        c.add_item(TextDisplay("Sistema para novos membros solicitarem entrada no grupo."))
        c.add_item(Separator(spacing=discord.SeparatorSpacing.large))
        c.add_item(TextDisplay(
            "📌 **Como usar**\n"
            "• **Solicitar SET** — Preencha nome, ID do jogo e tell in game.\n"
            "• Selecione um recrutador.\n"
            "• Admins aprovam/recusam no canal de registros SET."
        ))
        c.add_item(Separator())
        row = ActionRow()
        b = Button(label="Solicitar SET", style=discord.ButtonStyle.success, custom_id="solicitar_set_btn")
        b.callback = self._solicitar
        row.add_item(b)
        c.add_item(row)
        self.add_item(c)
    async def _solicitar(self, interaction):
        await interaction.response.send_modal(SolicitarSetModal(interaction.guild.id))

# ==================== BACKUP ====================
class BackupView(LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("# 💾 BACKUP DO SERVIDOR"))
        c.add_item(TextDisplay("Ferramenta para administradores protegerem os dados."))
        c.add_item(Separator(spacing=discord.SeparatorSpacing.large))
        c.add_item(TextDisplay(
            "🔧 **Funcionalidades**\n"
            "• 💾 Criar Backup\n• 🗑️ Apagar Locais\n• 🔄 Recarregar"
        ))
        c.add_item(Separator())
        row = ActionRow()
        b1 = Button(label="💾 Criar Backup", style=discord.ButtonStyle.secondary, custom_id="backup_criar")
        b2 = Button(label="🗑️ Apagar Locais", style=discord.ButtonStyle.danger, custom_id="backup_apagar")
        b3 = Button(label="🔄 Recarregar", style=discord.ButtonStyle.primary, custom_id="backup_recarregar")
        b1.callback = self._criar
        b2.callback = self._apagar
        b3.callback = self._recarregar
        row.add_item(b1); row.add_item(b2); row.add_item(b3)
        c.add_item(row)
        self.add_item(c)
    async def _criar(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        nome = await salvar_backup_completo(interaction.guild.id, interaction.user.name)
        await interaction.followup.send(f"✅ Backup `{nome}` criado!", ephemeral=True)
    async def _apagar(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = glob.glob(os.path.join(DATA_DIR, f"backup_{interaction.guild.id}_*.json"))
        n = 0
        for b in backups:
            try: os.remove(b); n += 1
            except: pass
        await interaction.followup.send(f"✅ {n} backup(s) deletados.", ephemeral=True)
    async def _recarregar(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = sorted(glob.glob(os.path.join(DATA_DIR, f"backup_{interaction.guild.id}_*.json")), reverse=True)
        if not backups:
            await interaction.followup.send("ℹ️ Nenhum backup encontrado.", ephemeral=True); return
        view = RecarregarBackupView(interaction.guild.id, backups)
        await interaction.followup.send(view=view, ephemeral=True)

class RecarregarBackupView(LayoutView):
    def __init__(self, gid, backups):
        super().__init__(timeout=120)
        self.gid = gid
        c = Container(accent_color=0x2C2F33)
        c.add_item(TextDisplay("# 📂 Restaurar Backup"))
        c.add_item(TextDisplay("⚠️ A restauração substituirá os dados atuais do servidor."))
        c.add_item(Separator())
        options = []
        for b in backups[:25]:
            try:
                with open(b, 'r') as f: data = json.load(f)
                label = f"{data.get('data_backup','?')} - {data.get('admin','?')}"
            except: label = os.path.basename(b)
            options.append(discord.SelectOption(label=label[:100], value=b))
        sel = Select(options=options)
        sel.callback = self._cb
        c.add_item(ActionRow(sel))
        self.add_item(c)
    async def _cb(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        arquivo = interaction.data["values"][0]
        try:
            with open(arquivo, 'r') as f: backup = json.load(f)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True); return
        if "dados" in backup:
            for key in ["usuarios", "canais", "caixa_semana", "compras_vendas", "usuarios_banidos",
                        "dinheiro_sujo", "acoes", "sets_pendentes", "backups_historicos"]:
                default = [] if key in ("compras_vendas", "usuarios_banidos") else {}
                dados[key][str(self.gid)] = backup["dados"].get(key, default)
            salvar_dados()
        if "config" in backup:
            cfg = _load_config_file()
            cfg[str(self.gid)] = backup["config"]
            _save_config_file(cfg)
            await load_all_settings()
        await interaction.followup.send("✅ Backup restaurado!", ephemeral=True)
        await atualizar_ranking(self.gid)

# ====================================================================
# ==================== PAINEL ADMIN ==================================
# ====================================================================

class AdminPanelView(LayoutView):
    def __init__(self, gid):
        super().__init__(timeout=900)
        self.gid = gid
        self._build_main()

    def _clear_and_build(self, builder):
        self.clear_items()
        builder()

    def _build_main(self):
        c = Container(accent_color=0x5865F2)
        c.add_item(TextDisplay("# ⚙️ PAINEL ADMINISTRATIVO\n## 4FAIXA Seeven"))
        c.add_item(TextDisplay(
            "Bem-vindo ao **centro de controle** do bot.\n"
            "Use o menu abaixo para navegar entre as seções."
        ))
        c.add_item(Separator(spacing=discord.SeparatorSpacing.large))
        c.add_item(TextDisplay(
            f"**Estado:** 🟢 Online\n"
            f"**Servidor:** `{self.gid}`\n"
            f"**Sessão:** expira em 15 min de inatividade"
        ))
        c.add_item(Separator())

        select = Select(
            placeholder="🎯 Escolha uma categoria...",
            options=[
                discord.SelectOption(label="Canais", value="canais", emoji="📢",
                                     description="Configure logs, ranking, painéis e registros"),
                discord.SelectOption(label="Cargos", value="cargos", emoji="👥",
                                     description="Admin, membro, aprovador de SET, compra/venda, ação"),
                discord.SelectOption(label="Produtos", value="produtos", emoji="📦",
                                     description="Nomes e valores dos produtos farmados"),
                discord.SelectOption(label="Sistema", value="sistema", emoji="⚙️",
                                     description="Taxas de lavagem, facção e membro"),
                discord.SelectOption(label="Painéis", value="paineis", emoji="🎛️",
                                     description="Publicar, atualizar ou limpar painéis"),
                discord.SelectOption(label="Backup", value="backup", emoji="💾",
                                     description="Criar, listar e restaurar backups"),
                discord.SelectOption(label="Estatísticas", value="stats", emoji="📊",
                                     description="Ver métricas do servidor"),
                discord.SelectOption(label="Manutenção", value="manutencao", emoji="🔧",
                                     description="Recarregar, limpar e resetar dados"),
            ],
        )
        select.callback = self._on_main_select
        c.add_item(ActionRow(select))
        self.add_item(c)

    async def _on_main_select(self, interaction):
        v = interaction.data["values"][0]
        handlers = {
            "canais": self._build_canais,
            "cargos": self._build_cargos,
            "produtos": self._build_produtos,
            "sistema": self._build_sistema,
            "paineis": self._build_paineis,
            "backup": self._build_backup,
            "stats": self._build_stats,
            "manutencao": self._build_manutencao,
        }
        builder = handlers.get(v)
        if not builder:
            await interaction.response.defer(); return
        self._clear_and_build(builder)
        await interaction.response.edit_message(view=self)

    async def _on_back(self, interaction):
        self._clear_and_build(self._build_main)
        await interaction.response.edit_message(view=self)

    def _add_back_row(self, c: Container):
        back = Button(label="⬅️ Voltar ao menu principal",
                      style=discord.ButtonStyle.secondary)
        back.callback = self._on_back
        c.add_item(ActionRow(back))

    def _header(self, title: str, subtitle: str = ""):
        c = Container(accent_color=0x5865F2)
        c.add_item(TextDisplay(f"## {title}"))
        if subtitle:
            c.add_item(TextDisplay(subtitle))
        c.add_item(Separator(spacing=discord.SeparatorSpacing.large))
        return c

    # ---------- 📢 CANAIS ----------
    def _build_canais(self):
        c = self._header("📢 Configuração de Canais",
                         "Selecione qual canal deseja configurar.")
        options = []
        for key, (label, cat) in SETTINGS_CONFIG.items():
            if cat != 'channel':
                continue
            current = bot.guild_settings.get(self.gid, {}).get(key)
            desc = f"✅ Canal: {current}" if current and str(current).isdigit() else "❌ Não configurado"
            options.append(discord.SelectOption(label=label[:80], value=key, description=desc[:100]))
        if options:
            sel = Select(placeholder="📢 Escolha um canal...", options=options[:25])
            sel.callback = self._on_setting_select_channel
            c.add_item(ActionRow(sel))
        self._add_back_row(c)
        self.add_item(c)

    async def _on_setting_select_channel(self, interaction):
        key = interaction.data["values"][0]
        label = SETTINGS_CONFIG[key][0]
        view = ChannelEditView(self.gid, key, label)
        await interaction.response.send_message(view=view, ephemeral=True)

    # ---------- 👥 CARGOS ----------
    def _build_cargos(self):
        c = self._header("👥 Configuração de Cargos",
                         "Escolha qual cargo deseja configurar (multi-seleção).")
        options = []
        for key, (label, cat) in SETTINGS_CONFIG.items():
            if cat != 'role':
                continue
            current = bot.guild_settings.get(self.gid, {}).get(key)
            ids = _parse_ids(current)
            if not ids:
                desc = "❌ Não configurado"
            elif len(ids) == 1:
                desc = f"✅ 1 cargo"
            else:
                desc = f"✅ {len(ids)} cargos"
            options.append(discord.SelectOption(label=label[:80], value=key, description=desc[:100]))
        if options:
            sel = Select(placeholder="👥 Escolha um cargo/lista...", options=options[:25])
            sel.callback = self._on_setting_select_role
            c.add_item(ActionRow(sel))
        self._add_back_row(c)
        self.add_item(c)

    async def _on_setting_select_role(self, interaction):
        key = interaction.data["values"][0]
        label = SETTINGS_CONFIG[key][0]
        view = RoleEditView(self.gid, key, label, interaction.guild)
        await interaction.response.send_message(view=view, ephemeral=True)

    # ---------- 📦 PRODUTOS ----------
    def _build_produtos(self):
        c = self._header("📦 Configuração de Produtos",
                         "Nomes e valores unitários dos produtos.")
        options = []
        for key, (label, cat) in SETTINGS_CONFIG.items():
            if cat != 'produto':
                continue
            current = bot.guild_settings.get(self.gid, {}).get(key)
            desc = f"✅ {str(current)[:60]}" if current else "❌ Não configurado"
            options.append(discord.SelectOption(label=label[:80], value=key, description=desc[:100]))
        if options:
            sel = Select(placeholder="📦 Escolha um produto/campo...", options=options[:25])
            sel.callback = self._on_setting_select_produto
            c.add_item(ActionRow(sel))
        self._add_back_row(c)
        self.add_item(c)

    async def _on_setting_select_produto(self, interaction):
        key = interaction.data["values"][0]
        label = SETTINGS_CONFIG[key][0]
        await interaction.response.send_modal(TextEditModal(self.gid, key, label))

    # ---------- ⚙️ SISTEMA ----------
    def _build_sistema(self):
        c = self._header("⚙️ Configurações de Sistema",
                         "Percentuais usados nos cálculos de fechamento e ações.")
        t_lav = bot.guild_settings.get(self.gid, {}).get('taxa_lavagem', '25')
        t_fac = bot.guild_settings.get(self.gid, {}).get('taxa_faccao', '60')
        t_mem = bot.guild_settings.get(self.gid, {}).get('taxa_membro', '40')
        t_acl = bot.guild_settings.get(self.gid, {}).get('taxa_acao_lavagem', '25')
        c.add_item(TextDisplay(
            f"**Resumo atual:**\n"
            f"💧 Lavagem: `{t_lav}%`\n"
            f"⚔️ Facção: `{t_fac}%`\n"
            f"👤 Membro: `{t_mem}%`\n"
            f"🎯 Lavagem em Ações: `{t_acl}%`"
        ))
        c.add_item(Separator())

        options = []
        for key, (label, cat) in SETTINGS_CONFIG.items():
            if cat != 'sistema':
                continue
            current = bot.guild_settings.get(self.gid, {}).get(key, "padrão")
            options.append(discord.SelectOption(
                label=label[:80], value=key, description=f"Atual: {current}%"))
        if options:
            sel = Select(placeholder="⚙️ Escolha uma taxa...", options=options[:25])
            sel.callback = self._on_setting_select_sistema
            c.add_item(ActionRow(sel))
        self._add_back_row(c)
        self.add_item(c)

    async def _on_setting_select_sistema(self, interaction):
        key = interaction.data["values"][0]
        label = SETTINGS_CONFIG[key][0]
        await interaction.response.send_modal(TextEditModal(self.gid, key, label))

    # ---------- 🎛️ PAINÉIS ----------
    def _build_paineis(self):
        c = self._header("🎛️ Painéis do Servidor",
                         "Publique, atualize ou remova os painéis interativos.")
        c.add_item(TextDisplay(
            "• **Publicar/Atualizar** — recria todos os painéis nos canais configurados\n"
            "• **Limpar painéis** — apaga as mensagens do bot nos canais de painel\n"
            "• **Atualizar ranking** — força a atualização do ranking"
        ))
        c.add_item(Separator())
        row = ActionRow()
        b1 = Button(label="Publicar / Atualizar", style=discord.ButtonStyle.success, emoji="🎛️")
        b2 = Button(label="Limpar Painéis", style=discord.ButtonStyle.danger, emoji="🧹")
        b3 = Button(label="Atualizar Ranking", style=discord.ButtonStyle.secondary, emoji="🏆")
        b1.callback = self._panel_publish
        b2.callback = self._panel_clear
        b3.callback = self._panel_ranking
        row.add_item(b1); row.add_item(b2); row.add_item(b3)
        c.add_item(row)
        self._add_back_row(c)
        self.add_item(c)

    async def _panel_publish(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        settings = bot.guild_settings.get(self.gid, {})
        res = await criar_todos_paineis(interaction.guild, settings)
        await interaction.followup.send(res, ephemeral=True)

    async def _panel_clear(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        settings = bot.guild_settings.get(self.gid, {})
        keys = ['canal_compra_venda_id', 'canal_painel_privado_id',
                'canal_backup_painel_id', 'canal_acoes_painel_id',
                'canal_solicitar_set_id', 'canal_rank_id']
        total = 0
        for k in keys:
            cid = settings.get(k)
            if not cid: continue
            try:
                ch = interaction.guild.get_channel(int(cid))
                if not ch: continue
                async for m in ch.history(limit=50):
                    if m.author == bot.user:
                        try: await m.delete(); total += 1
                        except: pass
            except: pass
        await interaction.followup.send(f"🧹 {total} mensagem(ns) removida(s).", ephemeral=True)

    async def _panel_ranking(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await atualizar_ranking(self.gid)
        await interaction.followup.send("🏆 Ranking atualizado!", ephemeral=True)

    # ---------- 💾 BACKUP ----------
    def _build_backup(self):
        c = self._header("💾 Backup do Servidor",
                         "Gerencie os arquivos de backup dos dados do servidor.")
        arquivos = sorted(glob.glob(os.path.join(DATA_DIR, f"backup_{self.gid}_*.json")), reverse=True)
        c.add_item(TextDisplay(f"**Backups disponíveis:** `{len(arquivos)}`"))
        c.add_item(Separator())
        row = ActionRow()
        b1 = Button(label="Criar Backup", style=discord.ButtonStyle.success, emoji="💾")
        b2 = Button(label="Listar / Restaurar", style=discord.ButtonStyle.primary, emoji="📂")
        b3 = Button(label="Apagar Todos", style=discord.ButtonStyle.danger, emoji="🗑️")
        b1.callback = self._backup_create
        b2.callback = self._backup_list
        b3.callback = self._backup_delete_all
        row.add_item(b1); row.add_item(b2); row.add_item(b3)
        c.add_item(row)
        self._add_back_row(c)
        self.add_item(c)

    async def _backup_create(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        nome = await salvar_backup_completo(self.gid, interaction.user.name)
        await interaction.followup.send(f"✅ Backup `{nome}` criado!", ephemeral=True)

    async def _backup_list(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = sorted(glob.glob(os.path.join(DATA_DIR, f"backup_{self.gid}_*.json")), reverse=True)
        if not backups:
            await interaction.followup.send("ℹ️ Nenhum backup encontrado.", ephemeral=True); return
        view = RecarregarBackupView(self.gid, backups)
        await interaction.followup.send(view=view, ephemeral=True)

    async def _backup_delete_all(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = glob.glob(os.path.join(DATA_DIR, f"backup_{self.gid}_*.json"))
        n = 0
        for b in backups:
            try: os.remove(b); n += 1
            except: pass
        await interaction.followup.send(f"🗑️ {n} backup(s) deletado(s).", ephemeral=True)

    # ---------- 📊 STATS ----------
    def _build_stats(self):
        c = self._header("📊 Estatísticas do Servidor", "Métricas gerais de uso do bot.")
        gid_str = str(self.gid)
        total_usuarios = len(dados["usuarios"].get(gid_str, {}))
        total_farms = 0; total_ds = 0.0
        total_canais = len(dados["canais"].get(gid_str, {}))
        total_pags = 0
        for uid, d in dados["usuarios"].get(gid_str, {}).items():
            if "removido_em" in d: continue
            total_farms += len(d.get("farms", []))
            total_ds += d.get("dinheiro_sujo", 0)
            total_pags += len(d.get("pagamentos", []))
        total_acoes = len(dados["acoes"].get(gid_str, {}))
        total_set = len(dados["sets_pendentes"].get(gid_str, {}))

        c.add_item(TextDisplay(
            f"👥 **Usuários ativos:** `{total_usuarios}`\n"
            f"📦 **Farms registrados:** `{total_farms}`\n"
            f"💰 **Dinheiro sujo total:** `R$ {total_ds:,.2f}`\n"
            f"💵 **Pagamentos:** `{total_pags}`\n"
            f"🔓 **Canais privados abertos:** `{total_canais}`\n"
            f"⚔️ **Ações registradas:** `{total_acoes}`\n"
            f"📋 **Sets pendentes:** `{total_set}`"
        ))
        c.add_item(Separator())
        row = ActionRow()
        b = Button(label="Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄")
        b.callback = self._refresh_stats
        row.add_item(b)
        c.add_item(row)
        self._add_back_row(c)
        self.add_item(c)

    async def _refresh_stats(self, interaction):
        self._clear_and_build(self._build_stats)
        await interaction.response.edit_message(view=self)

    # ---------- 🔧 MANUTENÇÃO ----------
    def _build_manutencao(self):
        c = self._header("🔧 Manutenção",
                         "Ferramentas avançadas. Use com cuidado.")
        c.add_item(TextDisplay(
            "• **Recarregar config** — relê `config_bot.json` do disco\n"
            "• **Resetar ranking** — apaga farms/pagamentos do servidor (faz backup antes)\n"
            "• **Sync comandos** — força re-sync dos slash commands"
        ))
        c.add_item(Separator())
        row = ActionRow()
        b1 = Button(label="Recarregar config", style=discord.ButtonStyle.primary, emoji="🔄")
        b2 = Button(label="Resetar ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
        b3 = Button(label="Sync comandos", style=discord.ButtonStyle.secondary, emoji="🔁")
        b1.callback = self._mnt_reload
        b2.callback = self._mnt_reset
        b3.callback = self._mnt_sync
        row.add_item(b1); row.add_item(b2); row.add_item(b3)
        c.add_item(row)
        self._add_back_row(c)
        self.add_item(c)

    async def _mnt_reload(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await load_all_settings()
        await interaction.followup.send("✅ Configurações recarregadas!", ephemeral=True)

    async def _mnt_reset(self, interaction):
        view = ConfirmarResetView(self.gid)
        await interaction.response.send_message(view=view, ephemeral=True)

    async def _mnt_sync(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            synced = await bot.tree.sync()
            await interaction.followup.send(f"🔁 {len(synced)} comandos sincronizados.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Apenas administradores podem usar este painel.", ephemeral=True)
            return False
        return True

# ====================================================================
# ==================== CRIAÇÃO DE PAINÉIS ============================
# ====================================================================

async def criar_todos_paineis(guild, settings):
    msgs = []

    cv_id = settings.get('canal_compra_venda_id')
    if cv_id:
        canal = guild.get_channel(int(cv_id))
        if canal:
            try:
                async for m in canal.history(limit=20):
                    if m.author == bot.user: await m.delete()
            except: pass
            try:
                await canal.send(view=CompraVendaView())
                msgs.append(f"✅ Compra/Venda → {canal.mention}")
            except: pass

    pid = settings.get('canal_painel_privado_id')
    if pid:
        canal = guild.get_channel(int(pid))
        if canal:
            try:
                async for m in canal.history(limit=20):
                    if m.author == bot.user: await m.delete()
            except: pass
            try:
                await canal.send(view=BotaoCriarCanalView())
                msgs.append(f"✅ Painel Privado → {canal.mention}")
            except: pass

    bid = settings.get('canal_backup_painel_id')
    if bid:
        canal = guild.get_channel(int(bid))
        if canal:
            try:
                async for m in canal.history(limit=20):
                    if m.author == bot.user: await m.delete()
            except: pass
            try:
                await canal.send(view=BackupView())
                msgs.append(f"✅ Backup → {canal.mention}")
            except: pass

    aid = settings.get('canal_acoes_painel_id')
    if aid:
        canal = guild.get_channel(int(aid))
        if canal:
            try:
                async for m in canal.history(limit=20):
                    if m.author == bot.user: await m.delete()
            except: pass
            try:
                await canal.send(view=ActionPanelView())
                msgs.append(f"✅ Ações → {canal.mention}")
            except: pass

    sid = settings.get('canal_solicitar_set_id')
    if sid:
        canal = guild.get_channel(int(sid))
        if canal:
            try:
                async for m in canal.history(limit=20):
                    if m.author == bot.user: await m.delete()
            except: pass
            try:
                await canal.send(view=SetPainelView())
                msgs.append(f"✅ SET → {canal.mention}")
            except: pass

    return "\n".join(msgs) if msgs else "⚠️ Nenhum canal configurado ainda."

# ====================================================================
# ==================== COMANDOS ======================================
# ====================================================================

@bot.hybrid_command(name="painel4faixaadmin",
                    description="Painel administrativo do bot 4FAIXA Seeven")
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
        await ctx.send("❌ Nenhuma configuração. Use `/painel4faixaadmin`."); return
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
    c = Container(accent_color=0x2C2F33)
    c.add_item(TextDisplay("# ⚙️ Configurações do Bot"))
    c.add_item(Separator())
    for k, v in settings.items():
        if k == 'guild_id': continue
        c.add_item(TextDisplay(f"**{k}:** `{str(v) if v else '❌'}`"))
    layout.add_item(c)
    await ctx.send(view=layout)

@bot.hybrid_command(name="stats", description="Mostra estatísticas do servidor")
async def server_stats(ctx):
    gid = ctx.guild.id; gid_str = str(gid)
    total_usuarios = len(dados["usuarios"].get(gid_str, {}))
    total_farms = 0; total_ds = 0.0
    total_canais = len(dados["canais"].get(gid_str, {}))
    for uid, data in dados["usuarios"].get(gid_str, {}).items():
        if "removido_em" in data: continue
        total_farms += len(data.get("farms", []))
        total_ds += data.get("dinheiro_sujo", 0)
    layout = LayoutView()
    c = Container(accent_color=0x2C2F33)
    c.add_item(TextDisplay("# 📊 Estatísticas do Servidor"))
    c.add_item(Separator())
    c.add_item(TextDisplay(
        f"👥 Usuários com farms: **{total_usuarios}**\n"
        f"📦 Total de farms: **{total_farms}**\n"
        f"💰 Dinheiro sujo total: **R$ {total_ds:,.2f}**\n"
        f"🔓 Canais abertos: **{total_canais}**"
    ))
    layout.add_item(c)
    await ctx.send(view=layout)

@bot.hybrid_command(name="me", description="Mostra seu resumo pessoal")
async def my_stats(ctx):
    uid = str(ctx.author.id); gid_str = str(ctx.guild.id)
    user_data = dados["usuarios"].get(gid_str, {}).get(uid, {})
    if not user_data:
        await ctx.send("ℹ️ Você ainda não possui registros."); return
    farms = user_data.get("farms", [])
    trans = user_data.get("transacoes_dinheiro_sujo", [])
    pagamentos = user_data.get("pagamentos", [])
    total_ds = user_data.get("dinheiro_sujo", 0)
    total_recebido = sum(p["valor"] for p in pagamentos)

    layout = LayoutView()
    c = Container(accent_color=0x2C2F33)
    c.add_item(TextDisplay(f"# 👤 Resumo de {ctx.author.display_name}"))
    c.add_item(Separator())
    c.add_item(TextDisplay(
        f"📦 Farms registrados: **{len(farms)}**\n"
        f"💰 Dinheiro sujo atual: **R$ {total_ds:,.2f}**\n"
        f"💵 Total recebido: **R$ {total_recebido:,.2f}**\n"
        f"📊 Transações de DS: **{len(trans)}**\n"
        f"📋 Pagamentos recebidos: **{len(pagamentos)}**"
    ))
    if farms:
        ultimo = farms[-1]
        data = datetime.strptime(ultimo["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        prods = ", ".join(f"{p['produto']}:{p['quantidade']}" for p in ultimo["produtos"])
        c.add_item(Separator())
        c.add_item(TextDisplay(f"📌 **Último farm**\n{data} — {prods}"))
    layout.add_item(c)
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

# ====================================================================
# ==================== EVENTOS =======================================
# ====================================================================

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
            c = Container(accent_color=0x2C2F33)
            c.add_item(TextDisplay("🎉 **Bot adicionado!** Use `/painel4faixaadmin` para configurar tudo."))
            layout.add_item(c)
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
