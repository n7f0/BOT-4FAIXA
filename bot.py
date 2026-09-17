import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, UserSelect, Select, ChannelSelect, RoleSelect
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
        self.guild_settings = {}  # {gid: {key: value}}

    async def setup_hook(self):
        self.add_view(BotaoCriarCanalView())
        self.add_view(CompraVendaView())
        self.add_view(ActionPanelView())
        self.add_view(BackupView())
        self.add_view(RankingView())
        self.add_view(SetPainelView())
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

# ========= MODAIS BASE =========
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

class ConfirmResetSemanalView(View):
    def __init__(self, gid, uid, uname, canal):
        super().__init__(timeout=60)
        self.gid = gid; self.uid = uid; self.uname = uname; self.canal = canal
    @discord.ui.button(label="Sim", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="confirm_reset_sim")
    async def sim(self, interaction, button):
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
    @discord.ui.button(label="Não", style=discord.ButtonStyle.secondary, custom_id="confirm_reset_nao")
    async def nao(self, interaction, button):
        await interaction.response.send_message("❌ Cancelado.", ephemeral=True)
        self.stop()

class ConfirmarFechamentoView(View):
    def __init__(self, gid, uid, canal):
        super().__init__(timeout=60)
        self.gid = gid; self.uid = uid; self.canal = canal
    @discord.ui.button(label="Sim", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="fechar_canal_sim")
    async def sim(self, interaction, button):
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
    @discord.ui.button(label="Não", style=discord.ButtonStyle.secondary, custom_id="fechar_canal_nao")
    async def nao(self, interaction, button):
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
        embed = discord.Embed(title="💾 Backup salvo", description=f"Arquivo: **{os.path.basename(nome)}**", color=0x2c2f33)
        await canal.send(embed=embed)
        try:
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
    embed = discord.Embed(title=f"📌 LOG: {acao.upper()}", description=detalhes, color=cor_final, timestamp=datetime.now())
    if usuario:
        try:
            embed.set_author(name=usuario.name, icon_url=usuario.display_avatar.url)
        except: pass
    try:
        await canal.send(embed=embed)
    except: pass

async def log_admin(gid, titulo, descricao, cor=0x99aab5):
    if not gid: return
    canal = await get_configured_channel(gid, 'canal_admin_logs_id')
    if canal:
        try:
            await canal.send(embed=discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now()))
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
                    if msg.author == bot.user and (f"<@{user_id}>" in msg.content or f"<@!{user_id}>" in msg.content):
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

# ========= RANKING =========
class RankingView(View):
    def __init__(self, gid=None):
        super().__init__(timeout=None)
        self.gid = gid
    @discord.ui.button(label="Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="rank_atualizar")
    async def atualizar(self, interaction, button):
        await interaction.response.defer()
        await atualizar_ranking(interaction.guild.id)
        await interaction.followup.send("✅ Ranking atualizado!", ephemeral=True)
    @discord.ui.button(label="Resetar", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="rank_resetar")
    async def resetar(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        await interaction.response.send_message("⚠️ Resetar ranking?", view=ConfirmarResetView(interaction.guild.id), ephemeral=True)

class ConfirmarResetView(View):
    def __init__(self, gid):
        super().__init__(timeout=60); self.gid = gid
    @discord.ui.button(label="Sim", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="reset_rank_sim")
    async def sim(self, interaction, button):
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
    @discord.ui.button(label="Não", style=discord.ButtonStyle.secondary, custom_id="reset_rank_nao")
    async def nao(self, interaction, button):
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
    emb = discord.Embed(title="🏆 RANKING DO SERVIDOR", color=0x2c2f33, timestamp=datetime.now())
    emb.set_footer(text=f"Total de farms: {total_farms_registrados} | Dinheiro sujo total: R$ {total_dinheiro_sujo_geral:,.2f}")
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
        emb.add_field(name=f"{medalha} {nome_prod}", value=texto, inline=False)
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
    emb.add_field(name="💰 TOP SALÁRIO", value=txt, inline=False)
    lista_sujo = sorted(usuarios, key=lambda x: x["din_sujo"], reverse=True)[:5]
    txt = "\n".join(
        f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else f'{i+1}°'} **{u['nome']}** - R$ {u['din_sujo']:,.2f}"
        for i,u in enumerate(lista_sujo) if u['din_sujo']>0
    ) or "Nenhum"
    emb.add_field(name="💀 DINHEIRO SUJO", value=txt, inline=False)
    try:
        await canal.send(embed=emb, view=RankingView(gid))
    except: pass

# ========= BOTÃO CRIAR CANAL =========
class BotaoCriarCanalView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="🔓 Criar Meu Canal Privado", style=discord.ButtonStyle.success, emoji="🔓", custom_id="criar_canal_privado")
    async def criar(self, interaction, button):
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
        view = FarmChannelView(gid, interaction.user.id, interaction.user.name, canal.id)
        user_data = dados["usuarios"].get(str(gid), {}).get(str(interaction.user.id), {})
        qtd_farms = len(user_data.get("farms", []))
        dinheiro_sujo = user_data.get("dinheiro_sujo", 0)
        embed = discord.Embed(title="🔐 SEU CANAL PRIVADO",
            description=f"{interaction.user.mention}, bem-vindo ao seu espaço exclusivo!", color=0x2c2f33)
        embed.add_field(name="📊 Resumo",
            value=f"**Criado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                  f"**Farms registrados:** {qtd_farms}\n"
                  f"**Dinheiro sujo acumulado:** R$ {dinheiro_sujo:,.2f}", inline=False)
        embed.add_field(name="🎯 O que você pode fazer aqui?",
            value="• 📦 **Farm Produtos**\n• 💰 **Farm Dinheiro Sujo**\n• ✏️ **Editar Registro**\n• 📋 **Meus Registros**", inline=False)
        await canal.send(embed=embed, view=view)
        await log_acao(gid, "criar_canal", interaction.user, f"Canal {canal.mention} criado")
        await interaction.followup.send(f"✅ Canal criado: {canal.mention}", ephemeral=True)
        await atualizar_ranking(gid)

# ========= VIEW DO CANAL DE FARM =========
class FarmChannelView(View):
    def __init__(self, gid, user_id, user_name, canal_id):
        super().__init__(timeout=None)
        self.gid=gid; self.user_id=user_id; self.user_name=user_name; self.canal_id=canal_id
    @discord.ui.button(label="📦 Farm Produtos", style=discord.ButtonStyle.secondary, row=0, custom_id="farm_produtos")
    async def farm_produtos(self, interaction, button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas o dono do canal.", ephemeral=True); return
        await interaction.response.send_modal(FarmProdutosModal(self.gid, self.user_id, self.user_name, interaction.channel))
    @discord.ui.button(label="💰 Farm Dinheiro Sujo", style=discord.ButtonStyle.secondary, row=0, custom_id="farm_dinheiro")
    async def farm_dinheiro(self, interaction, button):
        if not (is_admin(interaction.user) or is_membro(interaction.user)):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(DinheiroSujoModal(self.gid, self.user_id, self.user_name, interaction.channel))
    @discord.ui.button(label="✏️ Editar Registro", style=discord.ButtonStyle.secondary, row=0, custom_id="farm_editar")
    async def editar(self, interaction, button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        view = EscolherTipoEdicaoView(self.gid, self.user_id, self.user_name)
        await interaction.response.send_message("📝 Escolha o tipo de edição:", view=view, ephemeral=True)
    @discord.ui.button(label="📊 Fechar Caixa", style=discord.ButtonStyle.secondary, row=1, custom_id="farm_fechar_caixa")
    async def fechar_caixa(self, interaction, button):
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
        embed = discord.Embed(title="📊 RESUMO DO FECHAMENTO", description=f"**Usuário:** {self.user_name}", color=0x99aab5)
        embed.add_field(name="💰 Total farmado", value=f"R$ {total_sujo:,.2f}", inline=False)
        embed.add_field(name="🧼 Lavagem (25%)", value=f"R$ {lavagem:,.2f}", inline=True)
        embed.add_field(name="⚔️ Facção (60%)", value=f"R$ {faccao:,.2f}", inline=True)
        embed.add_field(name="👤 Membro (40%)", value=f"R$ {membro:,.2f}", inline=True)
        embed.set_footer(text=f"Admin: {interaction.user.display_name}")
        view = FechamentoSummaryView(self.gid, self.user_id, self.user_name, interaction.channel, total_sujo, lavagem, faccao, membro)
        await interaction.followup.send(embed=embed, view=view)
    @discord.ui.button(label="✏️ Mudar Nome", style=discord.ButtonStyle.secondary, row=1, custom_id="farm_mudar_nome")
    async def mudar_nome(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        await interaction.response.send_modal(MudarNomeModal(interaction.channel))
    @discord.ui.button(label="📜 Histórico Caixa", style=discord.ButtonStyle.secondary, row=1, custom_id="farm_historico")
    async def historico(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        fechamentos = dados["caixa_semana"].get(str(self.gid), {}).get(str(self.user_id), [])
        if not fechamentos:
            await interaction.followup.send("ℹ️ Nenhum fechamento registrado.", ephemeral=True); return
        embed = discord.Embed(title="📜 Histórico de Caixa", color=0x2c2f33)
        for f in fechamentos[-10:]:
            data = datetime.strptime(f["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            txt = f"**Meta:** {f.get('meta_farm','?')}\n**Pago:** R$ {f['dinheiro_sujo']['pago']:,.2f}"
            if f.get('observacao'): txt += f"\n*Obs:* {f['observacao']}"
            embed.add_field(name=data, value=txt, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
    @discord.ui.button(label="📋 Meus Registros", style=discord.ButtonStyle.primary, row=2, custom_id="farm_meus_registros")
    async def meus_registros(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        await enviar_historico_detalhado(interaction, self.gid, self.user_id, self.user_name)
    @discord.ui.button(label="🔄 Reset Semanal", style=discord.ButtonStyle.danger, row=2, custom_id="farm_reset_semanal")
    async def reset_semanal(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        view = ConfirmResetSemanalView(self.gid, self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_message("⚠️ Resetar a semana?", view=view, ephemeral=True)
    @discord.ui.button(label="🗑️ Fechar Canal", style=discord.ButtonStyle.danger, row=2, custom_id="farm_fechar_canal")
    async def fechar(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True); return
        view = ConfirmarFechamentoView(self.gid, self.user_id, interaction.channel)
        await interaction.response.send_message("⚠️ Fechar este canal?", view=view, ephemeral=True)

# ========= MODAIS FARM =========
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
        embed = discord.Embed(title="📦 Farm Registrada", description=f"**Usuário:** <@{self.uid}>", color=0x2c2f33, timestamp=datetime.now())
        embed.add_field(name="📋 Produtos", value="\n".join(f"• {p['produto']}: {p['quantidade']}" for p in produtos), inline=False)
        embed.add_field(name="📊 Total de itens", value=f"{total_itens}", inline=True)
        embed.add_field(name="💰 Valor estimado", value=f"R$ {valor_estimado:,.2f}", inline=True)
        embed.set_image(url=img)
        embed.set_footer(text=f"Farm #{farm['farm_id']}")
        try: await self.canal.send(embed=embed)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(embed=embed)
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
        embed = discord.Embed(title="💰 Dinheiro Sujo Registrado", description=f"**Usuário:** <@{self.uid}>", color=0x4f545c, timestamp=datetime.now())
        embed.add_field(name="Valor", value=f"R$ {val:,.2f}", inline=True)
        embed.add_field(name="Novo total", value=f"R$ {novo_total:,.2f}", inline=True)
        embed.set_image(url=img)
        try: await self.canal.send(embed=embed)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(embed=embed)
            except: pass
        await interaction.followup.send(f"✅ R$ {val:,.2f} registrado!", ephemeral=True)
        await log_acao(self.gid, "registrar_dinheiro_sujo", interaction.user, f"Valor: R$ {val:,.2f} | Total: R$ {novo_total:,.2f}")
        await atualizar_ranking(self.gid)

class FechamentoSummaryView(View):
    def __init__(self, gid, uid, uname, canal, total, lavagem, faccao, membro):
        super().__init__(timeout=300)
        self.gid=gid; self.uid=uid; self.uname=uname; self.canal=canal
        self.total=total; self.lavagem=lavagem; self.faccao=faccao; self.membro=membro
    @discord.ui.button(label="Continuar", style=discord.ButtonStyle.success, custom_id="fechamento_continuar")
    async def continuar(self, interaction, button):
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
        embed = discord.Embed(title="📊 Caixa Fechado", description=f"**Usuário:** {self.uname}", color=0x99aab5, timestamp=datetime.now())
        embed.add_field(name="Meta", value=meta, inline=True)
        embed.add_field(name="Pagamento final", value=f"R$ {pagamento:,.2f}", inline=True)
        if bonus_val > 0: embed.add_field(name="Bônus", value=f"R$ {bonus_val:,.2f}", inline=True)
        if obs_text: embed.add_field(name="Observação", value=obs_text, inline=False)
        embed.set_image(url=img)
        embed.set_footer(text=f"Admin: {interaction.user.display_name}")
        try: await self.canal.send(embed=embed)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(embed=embed)
            except: pass
        await interaction.followup.send(f"✅ Pagamento de R$ {pagamento:,.2f} registrado!", ephemeral=True)
        await log_acao(self.gid, "fechar_caixa", interaction.user, f"Pagamento: R$ {pagamento:,.2f} para {self.uname}")
        await atualizar_ranking(self.gid)

# ========= EDIÇÃO =========
class EscolherTipoEdicaoView(View):
    def __init__(self, gid, uid, uname):
        super().__init__(timeout=120)
        self.add_item(TipoEdicaoSelect(gid, uid, uname))

class TipoEdicaoSelect(Select):
    def __init__(self, gid, uid, uname):
        self.gid=gid; self.uid=uid; self.uname=uname
        options = [discord.SelectOption(label="Produtos", value="produtos"), discord.SelectOption(label="Dinheiro Sujo", value="dinheiro")]
        super().__init__(placeholder="O que editar?", options=options, custom_id=f"edicao_tipo_{gid}_{uid}")
    async def callback(self, interaction):
        if self.values[0] == "produtos":
            select = EditarRegistroSelect(self.gid, self.uid, self.uname)
            view = View(timeout=None); view.add_item(select)
            await interaction.response.send_message("📋 Selecione a farm:", view=view, ephemeral=True)
        else:
            select = EditarDinheiroSelect(self.gid, self.uid, self.uname)
            view = View(timeout=None); view.add_item(select)
            await interaction.response.send_message("💰 Selecione o depósito:", view=view, ephemeral=True)

class EditarRegistroSelect(Select):
    def __init__(self, gid, uid, uname):
        self.gid=gid; self.uid=str(uid); self.uname=uname
        farms = dados["usuarios"].get(str(gid), {}).get(self.uid, {}).get("farms", [])
        options = []
        for i, f in enumerate(farms):
            opts = ", ".join(f"{p['produto']}:{p['quantidade']}" for p in f["produtos"])
            options.append(discord.SelectOption(label=f"Farm {f.get('farm_id',i+1)} - {opts[:80]}", value=str(i)))
        if not options: options.append(discord.SelectOption(label="Nenhum registro", value="none"))
        super().__init__(options=options[:25], custom_id=f"editar_farm_select_{gid}_{uid}")
    async def callback(self, interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message("ℹ️ Nenhum farm.", ephemeral=True)
        idx = int(self.values[0])
        farm = dados["usuarios"][str(self.gid)][self.uid]["farms"][idx]
        modal = EditarFarmModal(self.gid, self.uid, self.uname, interaction.channel, idx, farm)
        await interaction.response.send_modal(modal)

class EditarFarmModal(Modal, title="Editar Farm"):
    chumbo = TextInput(label="Novo CHUMBO", required=False)
    capsula = TextInput(label="Novo CAPSULA", required=False)
    polvora = TextInput(label="Novo POLVORA", required=False)
    def __init__(self, gid, uid, uname, canal, idx, farm):
        super().__init__()
        self.gid=gid; self.uid=uid; self.uname=uname; self.canal=canal; self.idx=idx; self.farm=farm
        for p in farm["produtos"]:
            if p["produto"] == "CHUMBO": self.chumbo.default = str(p["quantidade"])
            elif p["produto"] == "CAPSULA": self.capsula.default = str(p["quantidade"])
            elif p["produto"] == "POLVORA": self.polvora.default = str(p["quantidade"])
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        novos = []
        for campo, nome in [(self.chumbo, "CHUMBO"), (self.capsula, "CAPSULA"), (self.polvora, "POLVORA")]:
            if campo.value is not None and campo.value.strip():
                try:
                    qtd = int(campo.value.strip())
                    if qtd > 0: novos.append({"produto": nome, "quantidade": qtd})
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
                    "print_url": img, "validado": True, "farm_id": self.farm.get("farm_id", self.idx + 1)}
        dados["usuarios"][str(self.gid)][self.uid]["farms"][self.idx] = novo_reg
        salvar_dados()
        valor_estimado = calcular_valor_estimado(self.gid, novos)
        embed = discord.Embed(title="✏️ Farm Editada", description=f"**Usuário:** <@{self.uid}>", color=0x99aab5, timestamp=datetime.now())
        embed.add_field(name="Novos produtos", value="\n".join(f"• {p['produto']}: {p['quantidade']}" for p in novos), inline=False)
        embed.add_field(name="Valor estimado", value=f"R$ {valor_estimado:,.2f}", inline=True)
        embed.set_image(url=img)
        try: await self.canal.send(embed=embed)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(embed=embed)
            except: pass
        await interaction.followup.send("✅ Farm editada!", ephemeral=True)
        await log_acao(self.gid, "editar_farm", interaction.user, f"Farm ID {novo_reg['farm_id']} editada")
        await atualizar_ranking(self.gid)

class EditarDinheiroSelect(Select):
    def __init__(self, gid, uid, uname):
        self.gid=gid; self.uid=str(uid); self.uname=uname
        trans = dados["usuarios"].get(str(gid), {}).get(self.uid, {}).get("transacoes_dinheiro_sujo", [])
        options = [discord.SelectOption(label=f"R$ {t['valor']:,.2f} - {t['data']}", value=str(i)) for i, t in enumerate(trans)]
        if not options: options.append(discord.SelectOption(label="Nenhum depósito", value="none"))
        super().__init__(options=options[:25], custom_id=f"editar_dinheiro_select_{gid}_{uid}")
    async def callback(self, interaction):
        if self.values[0] == "none":
            return await interaction.response.send_message("ℹ️ Nenhum depósito.", ephemeral=True)
        idx = int(self.values[0])
        trans = dados["usuarios"][str(self.gid)][self.uid]["transacoes_dinheiro_sujo"][idx]
        modal = EditarDinheiroModal(self.gid, self.uid, self.uname, interaction.channel, idx, trans)
        await interaction.response.send_modal(modal)

class EditarDinheiroModal(Modal, title="Editar Dinheiro Sujo"):
    novo_valor = TextInput(label="Novo valor (R$)", required=True)
    def __init__(self, gid, uid, uname, canal, idx, trans):
        super().__init__()
        self.gid=gid; self.uid=uid; self.uname=uname; self.canal=canal; self.idx=idx; self.trans=trans
        self.novo_valor.default = str(trans["valor"])
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if not (self.novo_valor.value and self.novo_valor.value.strip()):
            await interaction.followup.send("❌ Valor inválido.", ephemeral=True); return
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
        nova = {"valor": val, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "print_url": img, "registrado_por": interaction.user.id}
        dados["usuarios"][str(self.gid)][self.uid]["transacoes_dinheiro_sujo"][self.idx] = nova
        novo_total = sum(t["valor"] for t in dados["usuarios"][str(self.gid)][self.uid]["transacoes_dinheiro_sujo"])
        dados["usuarios"][str(self.gid)][self.uid]["dinheiro_sujo"] = novo_total
        salvar_dados()
        embed = discord.Embed(title="💰 Depósito Editado", description=f"**Usuário:** <@{self.uid}>", color=0x99aab5, timestamp=datetime.now())
        embed.add_field(name="Antigo valor", value=f"R$ {self.trans['valor']:,.2f}", inline=True)
        embed.add_field(name="Novo valor", value=f"R$ {val:,.2f}", inline=True)
        embed.add_field(name="Novo total", value=f"R$ {novo_total:,.2f}", inline=True)
        embed.set_image(url=img)
        try: await self.canal.send(embed=embed)
        except: pass
        canal_reg = await get_configured_channel(self.gid, 'canal_registros_id')
        if canal_reg:
            try: await canal_reg.send(embed=embed)
            except: pass
        await interaction.followup.send("✅ Depósito editado!", ephemeral=True)
        await log_acao(self.gid, "editar_dinheiro_sujo", interaction.user, f"Novo valor: R$ {val:,.2f}")
        await atualizar_ranking(self.gid)

async def enviar_historico_detalhado(interaction, gid, uid, uname):
    user_data = dados["usuarios"].get(str(gid), {}).get(str(uid), {})
    farms = user_data.get("farms", []); trans = user_data.get("transacoes_dinheiro_sujo", [])
    pagamentos = user_data.get("pagamentos", [])
    if not farms and not trans and not pagamentos:
        await interaction.followup.send("ℹ️ Nenhum registro encontrado.", ephemeral=True); return
    embed = discord.Embed(title=f"📋 Histórico de {uname}", color=0x2c2f33, timestamp=datetime.now())
    if farms:
        txt = ""
        for f in farms[-10:]:
            data = datetime.strptime(f["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            prods = ", ".join(f"{p['produto']}:{p['quantidade']}" for p in f["produtos"])
            valor = calcular_valor_estimado(gid, f["produtos"])
            txt += f"**{data}** - Farm #{f.get('farm_id','?')} - {prods} (R$ {valor:,.2f})\n"
        if txt: embed.add_field(name="📦 Farms", value=txt[:1024], inline=False)
    if trans:
        txt = ""
        for t in trans[-10:]:
            data = datetime.strptime(t["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            txt += f"**{data}** - R$ {t['valor']:,.2f}\n"
        total_ds = user_data.get("dinheiro_sujo", 0)
        embed.add_field(name=f"💰 Dinheiro Sujo (total: R$ {total_ds:,.2f})", value=txt[:1024], inline=False)
    if pagamentos:
        txt = ""
        for p in pagamentos[-10:]:
            data = datetime.strptime(p["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            txt += f"**{data}** - R$ {p['valor']:,.2f} ({p.get('tipo','Pagamento')})\n"
        embed.add_field(name="💵 Pagamentos Recebidos", value=txt[:1024], inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

# ========= COMPRA / VENDA =========
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
            total_venda = float(self.valor_total.value.replace(',', '.'))
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True); return
        if not all([tipos, qtds, valores]) or not (len(tipos) == len(qtds) == len(valores)):
            await interaction.followup.send("❌ Preencha corretamente.", ephemeral=True); return
        itens = [{"tipo": t, "quantidade": q, "valor": v} for t, q, v in zip(tipos, qtds, valores)]
        registro = {"tipo": "venda", "itens": itens, "faccao_compradora": self.faccao.value,
                    "valor_total_venda": total_venda, "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "responsavel": interaction.user.name}
        if str(self.gid) not in dados["compras_vendas"]: dados["compras_vendas"][str(self.gid)] = []
        dados["compras_vendas"][str(self.gid)].append(registro)
        salvar_dados()
        canal = await get_configured_channel(self.gid, 'canal_logs_compra_venda_id')
        if canal:
            embed = discord.Embed(title="💸 Venda registrada", color=0x2c2f33)
            desc = f"**Facção:** {self.faccao.value}\n**Total:** R$ {total_venda:,.2f}\n**Itens:**\n"
            for item in itens: desc += f"• {item['tipo']} x{item['quantidade']} - R$ {item['valor']:,.2f}\n"
            embed.description = desc
            embed.set_footer(text=f"Por {interaction.user.display_name}")
            try: await canal.send(embed=embed)
            except: pass
        await interaction.followup.send(f"✅ Venda registrada com {len(itens)} item(ns)!", ephemeral=True)
        await log_acao(self.gid, "compra_venda", interaction.user, f"Venda: {len(itens)} itens, total R$ {total_venda:,.2f}")

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
            qtd_v = int(self.qtd.value); valor_v = float(self.valor.value.replace(",", "."))
        except:
            await interaction.followup.send("❌ Valores inválidos.", ephemeral=True); return
        registro = {"tipo": "compra", "produto": self.produto.value, "quantidade": qtd_v, "valor_total": valor_v,
                    "faccao_vendedora": self.faccao.value, "responsavel": self.responsavel.value,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        if str(self.gid) not in dados["compras_vendas"]: dados["compras_vendas"][str(self.gid)] = []
        dados["compras_vendas"][str(self.gid)].append(registro)
        salvar_dados()
        canal = await get_configured_channel(self.gid, 'canal_logs_compra_venda_id')
        if canal:
            embed = discord.Embed(title="🛒 Compra registrada", color=0x2c2f33)
            embed.description = f"**Produto:** {self.produto.value}\n**Qtd:** {qtd_v}\n**Valor:** R$ {valor_v:,.2f}\n**Facção:** {self.faccao.value}\n**Responsável:** {self.responsavel.value}"
            embed.set_footer(text=f"Por {interaction.user.display_name}")
            try: await canal.send(embed=embed)
            except: pass
        await interaction.followup.send("✅ Compra registrada!", ephemeral=True)
        await log_acao(self.gid, "compra_venda", interaction.user, f"Compra: {qtd_v} {self.produto.value} - R$ {valor_v:,.2f}")

class CompraVendaView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="💸 Venda", style=discord.ButtonStyle.secondary, custom_id="compra_venda_venda")
    async def venda(self, interaction, button):
        await interaction.response.send_modal(VendaModal(interaction.guild.id))
    @discord.ui.button(label="🛒 Compra", style=discord.ButtonStyle.secondary, custom_id="compra_venda_compra")
    async def compra(self, interaction, button):
        await interaction.response.send_modal(CompraModal(interaction.guild.id))

# ========= AÇÕES =========
class ActionPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="⚔️ Abrir Ação", style=discord.ButtonStyle.secondary, custom_id="acao_abrir")
    async def abrir(self, interaction, button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.send_modal(ActionModal(interaction.guild.id))
    @discord.ui.button(label="💰 Pagamento", style=discord.ButtonStyle.secondary, custom_id="acao_pagamento")
    async def pagamento(self, interaction, button):
        if not pode_registrar_acao(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        acoes = dados["acoes"].get(str(interaction.guild.id), {})
        pendentes = {k:v for k,v in acoes.items() if not v.get("pago")}
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
        if res not in ["vitória","vitoria","derrota"]:
            await interaction.followup.send("❌ Resultado inválido.", ephemeral=True); return
        res = "Vitória" if res in ["vitória","vitoria"] else "Derrota"
        try: datetime.strptime(self.data.value, "%d/%m/%Y")
        except:
            await interaction.followup.send("❌ Data inválida.", ephemeral=True); return
        self.info = {"nome_acao": self.nome.value, "valor": val, "resultado": res,
                     "data_acao": self.data.value, "puxado_por": interaction.user.id}
        view = MemberSelectView(self.gid, self.info)
        await interaction.followup.send("👥 Selecione os membros:", view=view, ephemeral=True)

class MemberSelectView(View):
    def __init__(self, gid, info):
        super().__init__(timeout=120)
        self.gid=gid; self.info=info; self.membros=[info["puxado_por"]]
    @discord.ui.select(cls=UserSelect, placeholder="Membros", min_values=1, max_values=25, custom_id="member_select_acao")
    async def select(self, interaction, select):
        self.membros = list(set([self.info["puxado_por"]] + [u.id for u in select.values]))
        await interaction.response.defer()
    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.success, custom_id="member_confirm_acao")
    async def confirm(self, interaction, button):
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
            embed = discord.Embed(title="⚔️ Nova Ação", color=0x2c2f33, timestamp=datetime.now())
            embed.add_field(name="Ação", value=self.info["nome_acao"])
            embed.add_field(name="Valor", value=f"R$ {self.info['valor']:,.2f}")
            embed.add_field(name="Resultado", value=self.info["resultado"])
            embed.add_field(name="Participantes", value=" ".join(f"<@{m}>" for m in self.membros))
            if urls: embed.set_image(url=urls[0])
            try: await canal.send(embed=embed)
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
        options = [discord.SelectOption(label=f"{v['nome_acao']} - R$ {v['valor']:,.0f}", value=k) for k,v in actions.items()]
        super().__init__(placeholder="Escolha a ação", options=options, custom_id=f"action_dropdown_{gid}")
    async def callback(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        action = dados["acoes"][str(self.gid)][self.values[0]]
        valor = action["valor"]; lavagem = valor * 0.25; liquido = valor - lavagem
        n = len(action["membros"]); por_membro = liquido / n if n > 0 else 0
        embed = discord.Embed(title="📊 Resumo do Pagamento", color=0x99aab5)
        embed.add_field(name="Valor total", value=f"R$ {valor:,.2f}")
        embed.add_field(name="Lavagem (25%)", value=f"R$ {lavagem:,.2f}")
        embed.add_field(name="Líquido", value=f"R$ {liquido:,.2f}")
        embed.add_field(name="Por membro", value=f"R$ {por_membro:,.2f}")
        view = ConfirmPaymentView(self.gid, self.values[0], liquido, por_membro, action["membros"])
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class ConfirmPaymentView(View):
    def __init__(self, gid, aid, liquido, por_membro, membros):
        super().__init__(timeout=120)
        self.gid=gid; self.aid=aid; self.liquido=liquido; self.por_membro=por_membro; self.membros=membros
    @discord.ui.button(label="Confirmar Pagamento", style=discord.ButtonStyle.success, custom_id="confirm_payment_ok")
    async def confirm(self, interaction, button):
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
                "print_urls": urls, "data_pagamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "admin_id": interaction.user.id}
            salvar_dados()
            canal = await get_configured_channel(self.gid, 'canal_acoes_logs_id')
            if canal:
                embed = discord.Embed(title="✅ Pagamento Realizado", color=0x2c2f33)
                embed.add_field(name="Ação", value=action["nome_acao"])
                embed.add_field(name="Valor líquido", value=f"R$ {self.liquido:,.2f}")
                if urls: embed.set_image(url=urls[0])
                try: await canal.send(embed=embed)
                except: pass
            await interaction.followup.send("✅ Pagamento registrado!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Ação não encontrada.", ephemeral=True)
        self.stop()

# ========= SET =========
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
        await interaction.followup.send("👤 Selecione o recrutador:", view=view, ephemeral=True)

class RecrutadorSelectView(View):
    def __init__(self, modal):
        super().__init__(timeout=120); self.modal = modal
        select = UserSelect(placeholder="Recrutador", min_values=1, max_values=1, custom_id="recrutador_select")
        select.callback = self.callback
        self.add_item(select)
    async def callback(self, interaction):
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
            embed = discord.Embed(title="📋 Nova Solicitação de SET",
                description=f"**Solicitante:** {self.modal.nome_val} (<@{interaction.user.id}>)\n"
                            f"**ID Jogo:** {self.modal.id_val}\n**Tell:** {self.modal.tell_val}\n**Recrutador:** {rec.mention}",
                color=0x2c2f33, timestamp=datetime.now())
            embed.set_footer(text=f"ID: {pid}")
            view = AprovarSetView(self.modal.gid, pid, interaction.user.id, rec_id)
            try: await canal.send(embed=embed, view=view)
            except: pass
        await interaction.response.send_message("✅ Solicitação enviada!", ephemeral=True)
        self.stop()

class AprovarSetView(View):
    def __init__(self, gid, pid, sol_id, rec_id):
        super().__init__(timeout=None)
        self.gid=gid; self.pid=pid; self.sol_id=sol_id; self.rec_id=rec_id
    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.success, custom_id="aprovar_set_ok")
    async def aprovar(self, interaction, button):
        if not pode_aprovar_set(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        pedido = dados["sets_pendentes"].get(str(self.gid), {}).get(self.pid)
        if not pedido or pedido["status"] != "pendente":
            await interaction.response.send_message("❌ Pedido já processado.", ephemeral=True); return
        view = EscolherCargoView(self.gid, self.pid, self.sol_id, self.rec_id)
        await interaction.response.send_message("🎯 Escolha o cargo:", view=view, ephemeral=True)
    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.danger, custom_id="aprovar_set_recusar")
    async def recusar(self, interaction, button):
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

class EscolherCargoView(View):
    def __init__(self, gid, pid, sol_id, rec_id):
        super().__init__(timeout=120)
        self.gid=gid; self.pid=pid; self.sol_id=sol_id; self.rec_id=rec_id
        cargo_id = get_guild_setting(gid, 'cargo_membro_id')
        opts = [discord.SelectOption(label="Membro", value=str(cargo_id))] if cargo_id else [discord.SelectOption(label="Erro: cargo não configurado", value="none")]
        select = Select(placeholder="Cargo", options=opts, custom_id=f"escolher_cargo_{gid}_{pid}")
        select.callback = self.callback
        self.add_item(select)
    async def callback(self, interaction):
        if self.children[0].values[0] == "none":
            await interaction.response.send_message("❌ Cargo membro não configurado.", ephemeral=True); return
        cargo_id = int(self.children[0].values[0])
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
            canal = await get_configured_channel(self.gid, 'canal_registros_set_id')
            if canal:
                try:
                    async for msg in canal.history(limit=20):
                        if msg.author == bot.user and msg.embeds and self.pid in (msg.embeds[0].footer.text if msg.embeds[0].footer else ""):
                            await msg.edit(view=None); break
                except: pass
            await interaction.response.send_message(f"✅ Cargo {cargo.mention} atribuído!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)

class SetPainelView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Solicitar SET", style=discord.ButtonStyle.success, custom_id="solicitar_set_btn")
    async def solicitar(self, interaction, button):
        await interaction.response.send_modal(SolicitarSetModal(interaction.guild.id))

# ========= BACKUP =========
class BackupView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="💾 Criar Backup", style=discord.ButtonStyle.secondary, custom_id="backup_criar")
    async def criar(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        nome = await salvar_backup_completo(interaction.guild.id, interaction.user.name)
        await interaction.followup.send(f"✅ Backup **{nome}** criado!", ephemeral=True)
    @discord.ui.button(label="🗑️ Apagar Locais", style=discord.ButtonStyle.danger, custom_id="backup_apagar")
    async def apagar(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = glob.glob(os.path.join(DATA_DIR, f"backup_{interaction.guild.id}_*.json"))
        for b in backups:
            try: os.remove(b)
            except: pass
        await interaction.followup.send(f"✅ {len(backups)} backup(s) deletados.", ephemeral=True)
    @discord.ui.button(label="🔄 Recarregar", style=discord.ButtonStyle.primary, custom_id="backup_recarregar")
    async def recarregar(self, interaction, button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = sorted(glob.glob(os.path.join(DATA_DIR, f"backup_{interaction.guild.id}_*.json")), reverse=True)
        if not backups:
            await interaction.followup.send("ℹ️ Nenhum backup encontrado.", ephemeral=True); return
        view = RecarregarBackupView(interaction.guild.id, backups)
        await interaction.followup.send("📂 Selecione o backup:", view=view, ephemeral=True)

class RecarregarBackupView(View):
    def __init__(self, gid, backups):
        super().__init__(timeout=120); self.gid = gid
        options = []
        for b in backups[:25]:
            try:
                with open(b, 'r') as f: data = json.load(f)
                label = f"{data.get('data_backup','?')} - {data.get('admin','?')}"
            except: label = os.path.basename(b)
            options.append(discord.SelectOption(label=label[:100], value=b))
        select = Select(options=options, custom_id=f"backup_select_{gid}")
        select.callback = self.callback
        self.add_item(select)
    async def callback(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        arquivo = self.children[0].values[0]
        try:
            with open(arquivo, 'r') as f: backup = json.load(f)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True); return
        if "dados" in backup:
            for key in ["usuarios", "canais", "caixa_semana", "compras_vendas", "usuarios_banidos", "dinheiro_sujo", "acoes", "sets_pendentes", "backups_historicos"]:
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

# =========================================================
# ========= PAINEL ADMIN /painel4faixaadmin ===============
# =========================================================

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
            await interaction.response.send_message(f"✅ **{self.label_txt}** atualizado para: `{self.valor.value.strip()}`", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Erro ao salvar.", ephemeral=True)

class ChannelEditView(View):
    def __init__(self, gid, key, label):
        super().__init__(timeout=120)
        self.gid = gid; self.key = key; self.label_txt = label
        select = ChannelSelect(placeholder="Selecione o canal",
                               channel_types=[discord.ChannelType.text, discord.ChannelType.category])
        select.callback = self.callback
        self.add_item(select)
    async def callback(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        canal = interaction.data["values"][0]
        ok = await save_setting(self.gid, self.key, str(canal))
        if ok:
            await interaction.response.send_message(f"✅ **{self.label_txt}** → <#{canal}>", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Erro ao salvar.", ephemeral=True)

class RoleEditView(View):
    def __init__(self, gid, key, label):
        super().__init__(timeout=120)
        self.gid = gid; self.key = key; self.label_txt = label
        select = RoleSelect(placeholder="Selecione o cargo")
        select.callback = self.callback
        self.add_item(select)
    async def callback(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        role_id = interaction.data["values"][0]
        ok = await save_setting(self.gid, self.key, str(role_id))
        if ok:
            await interaction.response.send_message(f"✅ **{self.label_txt}** → <@&{role_id}>", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Erro ao salvar.", ephemeral=True)

class SettingsCategoryView(View):
    def __init__(self, gid, category):
        super().__init__(timeout=300)
        self.gid = gid; self.category = category
        options = []
        for key, (label, cat) in SETTINGS_CONFIG.items():
            if cat != category: continue
            current = bot.guild_settings.get(gid, {}).get(key, "não configurado")
            if current and str(current).isdigit() and category in ('channel', 'role'):
                desc = f"Atual: {current}"
            else:
                desc = f"Atual: {str(current)[:50]}"
            options.append(discord.SelectOption(label=label[:80], value=key, description=desc[:100]))
        options = options[:25]
        if options:
            select = Select(placeholder="Escolha o item...", options=options)
            select.callback = self.callback
            self.add_item(select)
    async def callback(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True); return
        key = self.children[0].values[0]
        label, cat = SETTINGS_CONFIG[key]
        if cat == 'channel':
            view = ChannelEditView(self.gid, key, label)
            await interaction.response.send_message(f"📢 Selecione o novo canal para **{label}**:", view=view, ephemeral=True)
        elif cat == 'role':
            view = RoleEditView(self.gid, key, label)
            await interaction.response.send_message(f"👥 Selecione o novo cargo para **{label}**:", view=view, ephemeral=True)
        else:
            await interaction.response.send_modal(TextEditModal(self.gid, key, label))

async def criar_todos_paineis(guild, settings):
    msgs = []
    # Compra/Venda
    cv_id = settings.get('canal_compra_venda_id')
    if cv_id:
        canal = guild.get_channel(int(cv_id))
        if canal:
            try:
                async for msg in canal.history(limit=20):
                    if msg.author == bot.user: await msg.delete()
            except: pass
            embed = discord.Embed(title="💸 SISTEMA DE COMPRA E VENDA",
                description="Registre transações de munição e itens entre facções.", color=0x2c2f33)
            embed.add_field(name="📌 Como usar",
                value="• **💸 Venda** – Tipos, quantidades, valores e facção compradora.\n"
                      "• **🛒 Compra** – Produto, quantidade, valor e facção vendedora.", inline=False)
            embed.set_footer(text="Apenas usuários com cargo autorizado.")
            try:
                await canal.send(embed=embed, view=CompraVendaView())
                msgs.append(f"✅ Compra/Venda → {canal.mention}")
            except: pass
    # Painel privado
    pid = settings.get('canal_painel_privado_id')
    if pid:
        canal = guild.get_channel(int(pid))
        if canal:
            try:
                async for msg in canal.history(limit=20):
                    if msg.author == bot.user: await msg.delete()
            except: pass
            embed = discord.Embed(title="🔓 CRIAR SEU CANAL PRIVADO",
                description="Crie seu canal exclusivo para gerenciar seus farms.", color=0x2c2f33)
            embed.add_field(name="🎯 O que você ganha?",
                value="• 📦 Registrar farms\n• 💰 Registrar dinheiro sujo\n• ✏️ Editar registros\n• 📋 Ver histórico\n• 📊 Fechar caixa (admins)", inline=False)
            embed.set_footer(text="Clique abaixo para criar!")
            try:
                await canal.send(embed=embed, view=BotaoCriarCanalView())
                msgs.append(f"✅ Painel Privado → {canal.mention}")
            except: pass
    # Backup
    bid = settings.get('canal_backup_painel_id')
    if bid:
        canal = guild.get_channel(int(bid))
        if canal:
            try:
                async for msg in canal.history(limit=20):
                    if msg.author == bot.user: await msg.delete()
            except: pass
            embed = discord.Embed(title="💾 BACKUP DO SERVIDOR",
                description="Ferramenta para admins protegerem os dados.", color=0x2c2f33)
            embed.add_field(name="🔧 Funcionalidades",
                value="• **💾 Criar Backup**\n• **🗑️ Apagar Locais**\n• **🔄 Recarregar**", inline=False)
            embed.set_footer(text="Apenas administradores.")
            try:
                await canal.send(embed=embed, view=BackupView())
                msgs.append(f"✅ Backup → {canal.mention}")
            except: pass
    # Ações
    aid = settings.get('canal_acoes_painel_id')
    if aid:
        canal = guild.get_channel(int(aid))
        if canal:
            try:
                async for msg in canal.history(limit=20):
                    if msg.author == bot.user: await msg.delete()
            except: pass
            embed = discord.Embed(title="⚔️ SISTEMA DE AÇÕES",
                description="Registre operações e gerencie pagamentos.", color=0x2c2f33)
            embed.add_field(name="📌 Como funciona",
                value="• **⚔️ Abrir Ação**\n• **💰 Pagamento** – Calcula lavagem 25% e divide entre membros", inline=False)
            embed.set_footer(text="Apenas usuários autorizados.")
            try:
                await canal.send(embed=embed, view=ActionPanelView())
                msgs.append(f"✅ Ações → {canal.mention}")
            except: pass
    # SET
    sid = settings.get('canal_solicitar_set_id')
    if sid:
        canal = guild.get_channel(int(sid))
        if canal:
            try:
                async for msg in canal.history(limit=20):
                    if msg.author == bot.user: await msg.delete()
            except: pass
            embed = discord.Embed(title="📋 SOLICITAÇÃO DE SET",
                description="Sistema para novos membros solicitarem entrada.", color=0x2c2f33)
            embed.add_field(name="📌 Como usar",
                value="• **Solicitar SET** – Preenche formulário e seleciona recrutador\n"
                      "• Admins aprovam/recusam no canal de registros SET", inline=False)
            embed.set_footer(text="Apenas admins e recrutadores.")
            try:
                await canal.send(embed=embed, view=SetPainelView())
                msgs.append(f"✅ SET → {canal.mention}")
            except: pass
    return "\n".join(msgs) if msgs else "⚠️ Nenhum canal configurado ainda. Configure os canais no painel primeiro."

class AdminPanelView(View):
    def __init__(self, gid):
        super().__init__(timeout=600)
        self.gid = gid
    async def interaction_check(self, interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Apenas administradores.", ephemeral=True)
            return False
        return True
    @discord.ui.button(label="📢 Canais", style=discord.ButtonStyle.primary, row=0)
    async def b_canais(self, interaction, button):
        view = SettingsCategoryView(self.gid, 'channel')
        await interaction.response.send_message("Selecione o canal a configurar:", view=view, ephemeral=True)
    @discord.ui.button(label="👥 Cargos", style=discord.ButtonStyle.primary, row=0)
    async def b_cargos(self, interaction, button):
        view = SettingsCategoryView(self.gid, 'role')
        await interaction.response.send_message("Selecione o cargo a configurar:", view=view, ephemeral=True)
    @discord.ui.button(label="📦 Produtos", style=discord.ButtonStyle.primary, row=0)
    async def b_produtos(self, interaction, button):
        view = SettingsCategoryView(self.gid, 'produto')
        await interaction.response.send_message("Selecione o produto/cargo a configurar:", view=view, ephemeral=True)
    @discord.ui.button(label="🎛️ Criar Painéis", style=discord.ButtonStyle.success, row=1)
    async def b_criar(self, interaction, button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        settings = bot.guild_settings.get(self.gid, {})
        resultado = await criar_todos_paineis(interaction.guild, settings)
        await interaction.followup.send(resultado, ephemeral=True)
    @discord.ui.button(label="💾 Backup", style=discord.ButtonStyle.secondary, row=1)
    async def b_backup(self, interaction, button):
        embed = discord.Embed(title="💾 BACKUP", description="Escolha uma ação:", color=0x2c2f33)
        await interaction.response.send_message(embed=embed, view=BackupView(), ephemeral=True)
    @discord.ui.button(label="📊 Stats", style=discord.ButtonStyle.secondary, row=1)
    async def b_stats(self, interaction, button):
        gid = self.gid; gid_str = str(gid)
        total_usuarios = len(dados["usuarios"].get(gid_str, {}))
        total_farms = 0; total_dinheiro_sujo = 0.0
        total_canais = len(dados["canais"].get(gid_str, {}))
        for uid, data in dados["usuarios"].get(gid_str, {}).items():
            if "removido_em" in data: continue
            total_farms += len(data.get("farms", []))
            total_dinheiro_sujo += data.get("dinheiro_sujo", 0)
        embed = discord.Embed(title="📊 Estatísticas do Servidor", color=0x2c2f33, timestamp=datetime.now())
        embed.add_field(name="👥 Usuários com farms", value=total_usuarios, inline=True)
        embed.add_field(name="📦 Total de farms", value=total_farms, inline=True)
        embed.add_field(name="💰 Dinheiro sujo total", value=f"R$ {total_dinheiro_sujo:,.2f}", inline=True)
        embed.add_field(name="🔓 Canais abertos", value=total_canais, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    @discord.ui.button(label="🔄 Recarregar", style=discord.ButtonStyle.secondary, row=2)
    async def b_reload(self, interaction, button):
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
    embed = discord.Embed(
        title="⚙️ PAINEL ADMINISTRATIVO — 4FAIXA Seeven",
        description=("Bem-vindo ao painel de configuração do bot.\n"
                     "Use os botões abaixo para configurar canais, cargos, produtos, criar painéis, "
                     "gerenciar backups e visualizar estatísticas.\n\n"
                     "**Tudo é salvo automaticamente em `config_bot.json`.**"),
        color=0x2c2f33, timestamp=datetime.now()
    )
    embed.add_field(name="📢 Canais", value="Configura onde logs/rankings/registros serão enviados.", inline=True)
    embed.add_field(name="👥 Cargos", value="Define cargo admin, membro e de aprovação SET.", inline=True)
    embed.add_field(name="📦 Produtos", value="Nomes dos produtos e valores unitários.", inline=True)
    embed.add_field(name="🎛️ Criar Painéis", value="Publica/republica os painéis nos canais configurados.", inline=False)
    embed.set_footer(text=f"Servidor: {ctx.guild.name} | ID: {ctx.guild.id}")
    await ctx.send(embed=embed, view=AdminPanelView(ctx.guild.id))

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
    embed = discord.Embed(title="⚙️ Configurações do Bot", color=0x2c2f33)
    for k, v in settings.items():
        embed.add_field(name=k, value=str(v) if v else "❌", inline=False)
    await ctx.send(embed=embed)

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
    embed = discord.Embed(title="📊 Estatísticas do Servidor", color=0x2c2f33, timestamp=datetime.now())
    embed.add_field(name="👥 Usuários com farms", value=total_usuarios, inline=True)
    embed.add_field(name="📦 Total de farms", value=total_farms, inline=True)
    embed.add_field(name="💰 Dinheiro sujo total", value=f"R$ {total_dinheiro_sujo:,.2f}", inline=True)
    embed.add_field(name="🔓 Canais abertos", value=total_canais, inline=True)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="me", description="Mostra seu resumo pessoal")
async def my_stats(ctx):
    uid = str(ctx.author.id); gid_str = str(ctx.guild.id)
    user_data = dados["usuarios"].get(gid_str, {}).get(uid, {})
    if not user_data:
        await ctx.send("ℹ️ Você ainda não possui registros. Crie seu canal privado!"); return
    farms = user_data.get("farms", []); trans = user_data.get("transacoes_dinheiro_sujo", [])
    pagamentos = user_data.get("pagamentos", []); total_ds = user_data.get("dinheiro_sujo", 0)
    total_recebido = sum(p["valor"] for p in pagamentos)
    embed = discord.Embed(title=f"👤 Resumo de {ctx.author.display_name}", color=0x2c2f33, timestamp=datetime.now())
    embed.add_field(name="📦 Farms registrados", value=len(farms), inline=True)
    embed.add_field(name="💰 Dinheiro sujo atual", value=f"R$ {total_ds:,.2f}", inline=True)
    embed.add_field(name="💵 Total recebido", value=f"R$ {total_recebido:,.2f}", inline=True)
    embed.add_field(name="📊 Transações de DS", value=len(trans), inline=True)
    embed.add_field(name="📋 Pagamentos recebidos", value=len(pagamentos), inline=True)
    if farms:
        ultimo = farms[-1]
        data = datetime.strptime(ultimo["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        prods = ", ".join(f"{p['produto']}:{p['quantidade']}" for p in ultimo["produtos"])
        embed.add_field(name="📌 Último farm", value=f"{data} - {prods}", inline=False)
    await ctx.send(embed=embed)

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
            await channel.send("🎉 **Bot adicionado!** Use `/painel4faixaadmin` para configurar tudo.")
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
