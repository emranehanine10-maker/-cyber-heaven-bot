# ============================================================
# CYBER HEAVEN - Discord Bot
# ============================================================
import asyncio
import functools
import random
import re
import time
import os
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
PINK = 0xe66cb6
TITLE = "CYBER HEAVEN"
FOOTER = "CYBER HEAVEN - Welcome to the family"
MAIN_IMAGE = "https://cdn.discordapp.com/attachments/1522319156614266890/1570902791667322960/903307255_1448823723986247_5560795212911455220_n.webp?ex=6af8c8bb&is=6af7773b&hm=c6365483f51bf48ef0afe790a2a3990236c2b6f702aa456835c80461f477224e&"
WELCOME_CHANNEL_ID = 1569130814355021915
RULES_CHANNEL_ID = 1510457472471535767
LEVEL_UP_CHANNEL_ID = 1568227584376836137
LOG_CHANNEL_ID = None

RULES = [
    "1. Respect kolchi, hna 3a2ila wa7da.",
    "2. No drama: ay mochkil kan7elouh b hdou2 f ticket.",
    "3. Bla spam, bla pub, bla invites.",
    "4. Bla alfaz khayba, 3onsoriya awla ihana.",
    "5. Kol channel w mawdou3o.",
    "6. Mamnou3 NSFW w ay content ma mnasbch.",
    "7. Sma3 l staff, 9rarathom nihaiya.",
    "8. Tsalya, l3ab, w 3ich f jaw dial l 3a2ila!",
]

LEVEL_ROLES = {5: "Active", 10: "VIP", 20: "Legend", 30: "Mythic"}

intents = 【entity-discord¦canonical_name=discord】.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents, help_command=None)
START = datetime.now(timezone.utc)

users = {}
afk = {}
cfg = {"log": LOG_CHANNEL_ID, "starboard": None, "suggest": None, "staff": None}
counting = {"channel": None, "current": 0}
tickets = {}
starred = set()
sent_ids = set()
replied = set()
public_def = set()
cooldowns = {}
spam = defaultdict(lambda: deque(maxlen=10))
xp_cd = {}
synced = False
INVITE_RE = re.compile(r"(【entity-discord¦canonical_name=discord】\.gg|【entity-discord¦canonical_name=discord】(app)?\.com/invite)/\w+", re.I)

def U(uid):
    if uid not in users:
        users[uid] = dict(money=500, bank=0, xp=0, level=1, streak=0, daily=None, inv=[], job=None,
                          warns=[], work_last=0.0, rob_last=0.0, boost=0.0, rps=[0, 0, 0])
    return users[uid]

def need(level):
    return 100 + level * 40

def total_xp(u):
    return sum(need(l) for l in range(1, u["level"])) + u["xp"]

def bar(cur, tot, n=10):
    tot = max(tot, 1)
    f = int(n * min(cur, tot) / tot)
    return "█" * f + "░" * (n - f)

def fmt(n):
    return f"{n:,}"

def now():
    return datetime.now(timezone.utc)

def rank_of(uid):
    ordered = sorted(users, key=lambda k: (users[k]["level"], users[k]["xp"]), reverse=True)
    return (ordered.index(uid) + 1 if uid in ordered else len(ordered) + 1), max(len(ordered), 1)

def emb(desc=None, *, title=TITLE, color=PINK, fields=None, image=None, thumb=None, author=None):
    e = discord.Embed(title=title, description=desc, color=color)
    for f in (fields or []):
        e.add_field(name=f[0], value=f[1], inline=(f[2] if len(f) > 2 else True))
    if image:
        e.set_image(url=image)
    if thumb:
        e.set_thumbnail(url=thumb)
    if author:
        e.set_author(name=author[0], icon_url=author[1])
    e.set_footer(text=FOOTER)
    return e

def parse_color(s):
    try:
        s = (s or "").strip().lstrip("#")
        if s.lower().startswith("0x"):
            s = s[2:]
        v = int(s, 16)
        return v if 0 <= v <= 0xFFFFFF else PINK
    except Exception:
        return PINK

def is_staff(m):
    p = m.guild_permissions
    return p.administrator or p.manage_messages or p.manage_guild

async def rep(i, content=None, *, embed=None, view=None, ephemeral=False):
    replied.add(i.id)
    kw = {}
    if content:
        kw["content"] = content
    if embed is not None:
        kw["embed"] = embed
    if view is not None:
        kw["view"] = view
    return await i.followup.send(ephemeral=ephemeral, **kw)

async def fail(i, text):
    if i.id in public_def:
        public_def.discard(i.id)
        try:
            await i.delete_original_response()
        except Exception:
            pass
    replied.add(i.id)
    await i.followup.send(embed=emb(text), ephemeral=True)

def safe(eph=False, perm=None, owner=False, cd=True):
    def deco(fn):
        name = fn.__name__
        @functools.wraps(fn)
        async def wrapper(interaction, *args, **kwargs):
            try:
                if interaction.id in sent_ids:
                    return
                sent_ids.add(interaction.id)
                if len(sent_ids) > 10000:
                    sent_ids.clear()
                if not interaction.guild:
                    await interaction.response.send_message(embed=emb("Had l command khdama ghir f server."), ephemeral=True)
                    return
                if cd:
                    key = (interaction.user.id, name)
                    t = time.time()
                    if t - cooldowns.get(key, 0) < 3:
                        await interaction.response.send_message(embed=emb("Hder chwiya! Tsenna 3 tawani w 3awd."), ephemeral=True)
                        return
                    cooldowns[key] = t
                if owner and interaction.user.id != interaction.guild.owner_id:
                    await interaction.response.send_message(embed=emb("Ghir mol l server"), ephemeral=True)
                    return
                if perm:
                    gp = interaction.user.guild_permissions
                    if not (gp.administrator or getattr(gp, perm, False)):
                        await interaction.response.send_message(embed=emb("Ma 3ndekch l sla7iya bach tdir hadchi."), ephemeral=True)
                        return
                e = eph or kwargs.get("show") == "private"
                await interaction.response.defer(ephemeral=e)
                if not e:
                    public_def.add(interaction.id)
                await fn(interaction, *args, **kwargs)
            except Exception as ex:
                print(f"[ERROR] /{name}: {ex!r}")
                try:
                    if interaction.response.is_done():
                        if interaction.id not in replied:
                            await fail(interaction, "Wa7ed l mochkil sra, 3awd jarreb mn ba3d.")
                    else:
                        await interaction.response.send_message(embed=emb("Wa7ed l mochkil sra, 3awd jarreb mn ba3d."), ephemeral=True)
                except Exception:
                    pass
            finally:
                public_def.discard(interaction.id)
                replied.discard(interaction.id)
        return wrapper
    return deco

def chan(guild, key, names=()):
    cid = cfg.get(key)
    c = guild.get_channel(cid) if cid else None
    if c is None:
        for n in names:
            c = discord.utils.get(guild.text_channels, name=n)
            if c:
                break
    if c is None and key in ("log", "staff"):
        c = guild.system_channel
    return c

async def send_log(guild, action, who, target=None, reason=None):
    try:
        ch = chan(guild, "log")
        if not ch:
            return
        fields = [("Action", action), ("Who", getattr(who, "mention", str(who)))]
        if target is not None:
            fields.append(("Target", getattr(target, "mention", str(target))))
        fields.append(("Reason", reason or "Bla sabab", False))
        fields.append(("Time", discord.utils.format_dt(now(), "F"), False))
        await ch.send(embed=emb(fields=fields))
    except Exception as ex:
        print(f"[LOG ERROR] {ex!r}")

async def dm(user, embed):
    try:
        await user.send(embed=embed)
        return True
    except Exception:
        return False

async def get_role(guild, name, create=True):
    r = discord.utils.get(guild.roles, name=name)
    if r is None and create:
        try:
            r = await guild.create_role(name=name, reason="CYBER HEAVEN bot")
        except Exception:
            r = None
    return r

def hier_error(i, target):
    if target.id == i.user.id:
        return "Ma tqdarch tdir hadchi f rassek."
    if target.id == i.guild.owner_id:
        return "Ma tqdarch tdir hadchi m3a mol l server."
    if i.user.id != i.guild.owner_id and target.top_role >= i.user.top_role:
        return "Role dyal had l member 3ali 3lik awla b7alk."
    if target.top_role >= i.guild.me.top_role:
        return "Role dyali sghir 3la had l member, 3ali l role dyal l bot."
    return None

async def sync_level_roles(member, level):
    target = None
    for lv in sorted(LEVEL_ROLES):
        if level >= lv:
            target = LEVEL_ROLES[lv]
    if not target:
        return
    role = await get_role(member.guild, target)
    if not role:
        return
    olds = [r for r in member.roles if r.name in LEVEL_ROLES.values() and r.name != target]
    if olds:
        await member.remove_roles(*olds, reason="Level up")
    if role not in member.roles:
        await member.add_roles(role, reason="Level up")

async def add_xp(member, amount, channel=None):
    u = U(member.id)
    if time.time() < u["boost"]:
        amount *= 2
    u["xp"] += amount
    up = False
    while u["xp"] >= need(u["level"]):
        u["xp"] -= need(u["level"])
        u["level"] += 1
        up = True
    if up:
        level_channel = None
        if member.guild:
            level_channel = member.guild.get_channel(LEVEL_UP_CHANNEL_ID)
        target_channel = level_channel if level_channel else channel
        if target_channel:
            try:
                await target_channel.send(embed=emb(f"Mabrouk {member.mention}! Wslti l **level {u['level']}**"), delete_after=15)
            except Exception:
                pass
        try:
            await sync_level_roles(member, u["level"])
        except Exception:
            pass

def get_badges(m, u):
    b = []
    if m.id == m.guild.owner_id:
        b.append("Mol l server")
    if m.premium_since:
        b.append("Booster")
    if u["level"] >= 10:
        b.append("Level 10+")
    if u["streak"] >= 7:
        b.append("Streak 7+")
    if u["money"] + u["bank"] >= 10000:
        b.append("Ghani")
    if "VIP" in u["inv"]:
        b.append("VIP")
    return b or ["Bla badges"]

def welcome_embed(member=None):
    who = member.mention if member else "l member jdid"
    return emb(f"Mar7ba bik {who} f **CYBER HEAVEN**!\nHna kolna 3a2ila wa7da: nl3bo, nhedro, nderro chill w bla drama.\nKhod raha w ntiya f dar dialk.",
               image=MAIN_IMAGE, color=PINK)

def rules_embed():
    return emb("**Qawanin dial CYBER HEAVEN**\n\n" + "\n".join(RULES) + f"\n\nChof dakchi f <#{RULES_CHANNEL_ID}>")

async def check_warn_thresholds(guild, member):
    n = len(U(member.id)["warns"])
    try:
        if n >= 5:
            await guild.ban(member, reason="5 warns")
            await send_log(guild, "Auto-Ban", bot.user, member, "5 warns")
            return "Auto-BAN (5 warns)"
        if n == 3:
            await member.kick(reason="3 warns")
            await send_log(guild, "Auto-Kick", bot.user, member, "3 warns")
            return "Auto-KICK (3 warns)"
    except Exception:
        return "Ma9dertch ndir l action automatique (chof permissions dial l bot)"
    return ""

async def auto_warn(message, reason, do_timeout=False):
    m = message.author
    U(m.id)["warns"].append(dict(reason=reason, by="AutoMod", level=1, time=now()))
    if do_timeout:
        try:
            await m.timeout(timedelta(minutes=1), reason=reason)
        except Exception:
            pass
    await send_log(message.guild, "AutoMod warn" + (" + timeout 1min" if do_timeout else ""), bot.user, m, reason)
    try:
        await message.channel.send(embed=emb(f"{m.mention} t3ti warn: **{reason}**"), delete_after=8)
    except Exception:
        pass
    await check_warn_thresholds(message.guild, m)

class ConfirmView(【entity-discord¦canonical_name=discord】.ui.View):
    def __init__(self, user_id, on_confirm):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.on_confirm = on_confirm
        self.done = False
        self.message = None
    async def interaction_check(self, it):
        if it.user.id != self.user_id:
            await it.response.send_message(embed=emb("Hadchi machi dialk."), ephemeral=True)
            return False
        return True
    @【entity-discord¦canonical_name=discord】.ui.button(label="Confirmer", style=【entity-discord¦canonical_name=discord】.ButtonStyle.success)
    async def yes(self, it, button):
        if self.done:
            return await it.response.defer()
        self.done = True
        for c in self.children:
            c.disabled = True
        embed = await self.on_confirm()
        await it.response.edit_message(embed=embed, view=self)
        self.stop()
    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.danger)
    async def no(self, it, button):
        if self.done:
            return await it.response.defer()
        self.done = True
        for c in self.children:
            c.disabled = True
        await it.response.edit_message(embed=emb("Tkanselat l 3amaliya."), view=self)
        self.stop()
    async def on_timeout(self):
        if self.done or not self.message:
            return
        for c in self.children:
            c.disabled = True
        try:
            await self.message.edit(embed=emb("Wa9t salla, tkanselat l 3amaliya."), view=self)
        except Exception:
            pass

@bot.event
async def on_ready():
    global synced
    print(f"Logged in as {bot.user} | servers: {len(bot.guilds)}")
    if not synced:
        synced = True
        try:
            cmds = await bot.tree.sync()
            print(f"Synced {len(cmds)} slash commands")
        except Exception as ex:
            print(f"[SYNC ERROR] {ex!r}")
    await bot.change_presence(activity=discord.Game("CYBER HEAVEN | /help"))

@bot.tree.error
async def on_tree_error(interaction, error):
    print(f"[TREE ERROR] {error!r}")
    try:
        e = emb("Wa7ed l mochkil sra, 3awd jarreb mn ba3d.")
        if interaction.response.is_done():
            await interaction.followup.send(embed=e, ephemeral=True)
        else:
            await interaction.response.send_message(embed=e, ephemeral=True)
    except Exception:
        pass

@bot.event
async def on_member_join(member):
    try:
        role = await get_role(member.guild, "Member", create=False)
        if role:
            await member.add_roles(role, reason="Auto role")
    except Exception as ex:
        print(f"[AUTOROLE] {ex!r}")
    await dm(member, welcome_embed(member))
    await dm(member, rules_embed())
    await send_log(member.guild, "Member joined", member, None, "Join")

@bot.event
async def on_member_remove(member):
    await send_log(member.guild, "Member left", member, None, "Leave")

@bot.event
async def on_raw_reaction_add(payload):
    try:
        if str(payload.emoji) != "⭐" or not payload.guild_id or payload.message_id in starred:
            return
        guild = bot.get_guild(payload.guild_id)
        ch = guild.get_channel(payload.channel_id)
        sb = chan(guild, "starboard", ("starboard",))
        if not sb or ch.id == sb.id:
            return
        msg = await ch.fetch_message(payload.message_id)
        r = discord.utils.get(msg.reactions, emoji="⭐")
        if r and r.count >= 3:
            starred.add(msg.id)
            e = emb(msg.content or "(bla text)", fields=[("Source", f"[Mur l message]({msg.jump_url})", False)],
                    author=(msg.author.display_name, msg.author.display_avatar.url))
            if msg.attachments and (msg.attachments[0].content_type or "").startswith("image"):
                e.set_image(url=msg.attachments[0].url)
            await sb.send(content=f"⭐ {r.count} | {ch.mention}", embed=e)
    except Exception as ex:
        print(f"[STARBOARD] {ex!r}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    try:
        m = message.author
        admin = m.guild_permissions.administrator
        if not admin:
            if INVITE_RE.search(message.content):
                try:
                    await message.delete()
                except Exception:
                    pass
                await auto_warn(message, "Invite link ma m3roufch")
                return
            dq = spam[m.id]
            t = time.time()
            dq.append(t)
            if len([x for x in dq if t - x <= 5]) >= 5:
                dq.clear()
                try:
                    await message.channel.purge(limit=10, check=lambda x: x.author.id == m.id)
                except Exception:
                    pass
                await auto_warn(message, "Spam (5 messages f 5 tawani)", do_timeout=True)
                return
        if counting["channel"] == message.channel.id:
            txt = message.content.strip()
            if txt.isdigit() and int(txt) == counting["current"] + 1:
                counting["current"] += 1
                try:
                    await message.add_reaction("✅")
                except Exception:
                    pass
            else:
                try:
                    await message.delete()
                except Exception:
                    pass
                counting["current"] = 0
                await message.channel.send(embed=emb(f"{m.mention} ghalat! L3d tbda mn **1**"), delete_after=6)
            return
        if m.id in afk:
            del afk[m.id]
            await message.channel.send(embed=emb(f"Mar7ba bik raja3ti {m.mention}, tm7a l AFK dialk."), delete_after=8)
        for mem in message.mentions:
            a = afk.get(mem.id)
            if a:
                if a["until"] and now() > a["until"]:
                    del afk[mem.id]
                    continue
                await message.channel.send(embed=emb(f"{mem.display_name} AFK daba: **{a['reason']}**"), delete_after=10)
        if time.time() - xp_cd.get(m.id, 0) >= 30:
            xp_cd[m.id] = time.time()
            await add_xp(m, random.randint(5, 15), message.channel)
    except Exception as ex:
        print(f"[ON_MESSAGE] {ex!r}")

HELP = {
    "3ama": ["`/help` - hadi", "`/ping` - latency w status", "`/profile` - profile dialk", "`/avatar` `/banner` - tswira",
             "`/userinfo` `/serverinfo` - ma3lomat", "`/top` `/rank` - classement", "`/afk` - ghib b khbar",
             "`/ticket` `/suggest` `/report` `/remind` `/ask` `/lyrics` `/nowplaying`"],
    "flous": ["`/daily` `/balance` `/deposit` `/withdraw` `/transfer`", "`/gamble` `/work` `/rob`",
              "`/shop` `/buy` `/inventory` `/use`"],
    "al3ab": ["`/8ball` `/rps` `/coinflip` `/dice` `/slot`", "`/truth` `/dare` `/joke` `/meme` `/ship` `/hug`",
              "`/quiz` `/giveaway` `/poll` `/counting_setup`"],
    "idara": ["`/kick` `/ban` `/unban` `/timeout` `/untimeout`", "`/warn` `/warnings` `/clearwarns`",
              "`/clear` `/lock` `/unlock` `/slowmode`", "`/send` `/send_rules` `/send_welcome` `/announce` `/setup`",
              "`/close_ticket` `/add_user`"],
}

@bot.tree.command(name="help", description="Chof ga3 l commands dial l bot")
@app_commands.describe(category="Khtar l9ism li bghiti")
@safe()
async def help_cmd(i: discord.Interaction, category: Literal['3ama', 'flous', 'al3ab', 'idara', 'kolchi'] = 'kolchi'):
    cats = list(HELP) if category == 'kolchi' else [category]
    fields = [(c.upper(), "\n".join(HELP[c]), False) for c in cats]
    await rep(i, embed=emb("Hado homa l commands dial **CYBER HEAVEN**", fields=fields, thumb=MAIN_IMAGE))

@bot.tree.command(name="ping", description="Chof sor3a dial l bot w status dyalo")
@safe()
async def ping_cmd(i: discord.Interaction):
    up = int((now() - START).total_seconds())
    d, rem = divmod(up, 86400)
    h, rem = divmod(rem, 3600)
    mi, s = divmod(rem, 60)
    await rep(i, embed=emb(fields=[("Latency", f"{round(bot.latency * 1000)} ms"), ("Uptime", f"{d}d {h}h {mi}m {s}s"),
                                    ("Status", "Online"), ("Servers", str(len(bot.guilds)))]))

@bot.tree.command(name="profile", description="Chof profile dialek")
@app_commands.describe(member="Chkoun bghiti tchof profile dyalo", show="Public awla private")
@safe()
async def profile_cmd(i: discord.Interaction, member: discord.Member = None, show: Literal['public', 'private'] = 'public'):
    m = member or i.user
    u = U(m.id)
    nxt = need(u["level"])
    roles = [r.mention for r in reversed(m.roles) if r != i.guild.default_role][:10]
    await rep(i, embed=emb(f"Profile dial {m.mention}", thumb=m.display_avatar.url, fields=[
        ("Flous", f"Wallet: **{fmt(u['money'])}**\nBank: **{fmt(u['bank'])}**"),
        ("Level", f"**{u['level']}**"),
        ("XP", f"{bar(u['xp'], nxt)} {u['xp']}/{nxt}", False),
        ("Warnings", str(len(u["warns"]))),
        ("Joined", discord.utils.format_dt(m.joined_at, "D") if m.joined_at else "?"),
        ("Roles", " ".join(roles) or "Walo", False),
        ("Badges", " | ".join(get_badges(m, u)), False)]))

@bot.tree.command(name="avatar", description="Chof avatar dial chi wa7ed b7jem kbir")
@app_commands.describe(member="Chkoun", size="7jem tswira")
@safe()
async def avatar_cmd(i: discord.Interaction, member: discord.Member = None, size: Literal[128, 256, 512, 1024] = 512):
    m = member or i.user
    url = m.display_avatar.with_size(size).url
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Download", url=url))
    await rep(i, embed=emb(f"Avatar dial {m.mention} ({size}px)", image=url), view=view)

@bot.tree.command(name="banner", description="Chof banner dial chi wa7ed ila kayn")
@app_commands.describe(member="Chkoun")
@safe()
async def banner_cmd(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    u = await bot.fetch_user(m.id)
    if not u.banner:
        return await fail(i, "Had l member ma 3ndoch banner.")
    await rep(i, embed=emb(f"Banner dial {m.mention}", image=u.banner.url))

@bot.tree.command(name="userinfo", description="Kol ma3lomat 3la chi member")
@app_commands.describe(member="Chkoun")
@safe()
async def userinfo_cmd(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    act = m.activity.name if m.activity else "Walo"
    await rep(i, embed=emb(f"Info dial {m.mention}", thumb=m.display_avatar.url, fields=[
        ("ID", str(m.id)), ("Created", discord.utils.format_dt(m.created_at, "D")),
        ("Joined", discord.utils.format_dt(m.joined_at, "D") if m.joined_at else "?"),
        ("Highest role", m.top_role.mention), ("Status", str(m.status)), ("Activity", act)]))

@bot.tree.command(name="serverinfo", description="Chof ma3lomat dial server")
@safe()
async def serverinfo_cmd(i: 【entity-discord¦canonical_name=discord】.Interaction):
    g = i.guild
    online = len([x for x in g.members if x.status != 【entity-discord¦canonical_name=discord】.Status.offline])
    bots = len([x for x in g.members if x.bot])
    await rep(i, embed=emb(f"**{g.name}**", thumb=g.icon.url if g.icon else None, fields=[
        ("ID", str(g.id)), ("Owner", f"<@{g.owner_id}>"), ("Created", discord.utils.format_dt(g.created_at, "D")),
        ("Members", str(g.member_count)), ("Online", str(online)), ("Bots", str(bots)),
        ("Channels", str(len(g.channels))), ("Roles", str(len(g.roles))), ("Boosts", str(g.premium_subscription_count))]))

@bot.tree.command(name="top", description="Classement dial l members")
@app_commands.describe(type="Nou3 dial classement", limit="3dad dial l members")
@safe()
async def top_cmd(i: 【entity-discord¦canonical_name=discord】.Interaction, type: Literal['level', 'flous', 'xp', 'warnings'] = 'level',
                  limit: Literal[5, 10, 20] = 10):
    keyf = {"level": lambda u: (u["level"], u["xp"]), "flous": lambda u: u["money"] + u["bank"],
            "xp": total_xp, "warnings": lambda u: len(u["warns"])}[type]
    shown = {"level": lambda u: f"Level {u['level']}", "flous": lambda u: f"{fmt(u['money'] + u['bank'])} flous",
             "xp": lambda u: f"{fmt(total_xp(u))} XP", "warnings": lambda u: f"{len(u['warns'])} warns"}[type]
    ordered = sorted(users.items(), key=lambda kv: keyf(kv[1]), reverse=True)[:limit]
    if not ordered:
        return await rep(i, embed=emb("Ba9i walo f classement, bda thder w tl3eb!"))
    lines = [f"**{n}.** <@{uid}> - {shown(u)}" for n, (uid, u) in enumerate(ordered, 1)]
    await rep(i, embed=emb(f"**Top {limit} - {type}**\n\n" + "\n".join(lines)))

@bot.tree.command(name="rank", description="Chof rank card dialek")
@safe()
async def rank_cmd(i: discord.Interaction):
    u = U(i.user.id)
    nxt = need(u["level"])
    pos, tot = rank_of(i.user.id)
    await rep(i, embed=emb(f"Rank dial {i.user.mention}", thumb=i.user.display_avatar.url, fields=[
        ("Level", str(u["level"])), ("Rank", f"#{pos} / {tot}"),
        ("XP", f"{bar(u['xp'], nxt, 15)}\n{u['xp']}/{nxt}", False),
        ("Level jay", f"Baqi lik **{nxt - u['xp']}** XP", False)]))

@bot.tree.command(name="afk", description="Dir rassek AFK w l bot ghadi yjawb 3lik")
@app_commands.describe(reason="Sbab", duration="Chhal ghadi tghib", custom_minutes="Dqayq ila khtarti custom")
@safe()
async def afk_cmd(i: discord.Interaction, reason: str = "Ma 3ndi sabab",
                  duration: Literal['10min', '1h', '1day', 'custom'] = '1h',
                  custom_minutes: app_commands.Range[int, 1, 10080] = 30):
    mins = {'10min': 10, '1h': 60, '1day': 1440, 'custom': custom_minutes}[duration]
    afk[i.user.id] = {"reason": reason, "until": now() + timedelta(minutes=mins)}
    await rep(i, embed=emb(f"{i.user.mention} daba AFK: **{reason}** ({mins} dqiqa)"))

JOBS = {
    "police": ["Mseki lik wa7ed hrami w t3awnti.", "Dert patrouille f lil w khlstti."],
    "doctor": ["3alajti 3 marda f l mostachfa.", "Dert 3amaliya najha."],
    "teacher": ["Chr7ti dars l 30 talib.", "Sa77ti 100 copie."],
    "gamer": ["Rbe7ti tournoi f lo3ba.", "Dert stream dial gaming."],
    "hacker": ["Sddti server dial chi chrika (white hat).", "L9iti bug w tkhlsti 3liha."],
    "streamer": ["Dert live dial 4 sa3at.", "Chi donation jat f stream."],
}
SHOP = {
    "VIP": ("Role VIP", 5000, "Role VIP f server"),
    "Legend": ("Role Legend", 10000, "Role Legend f server"),
    "Color": ("Custom Color", 2000, "Role b lon 3chwa2i"),
    "XPBoost": ("XP Boost", 3000, "x2 XP l 1 sa3a"),
    "Shield": ("Shield", 1500, "Kay7mik mn rob mra wa7da"),
}
ItemChoice = Literal['VIP', 'Legend', 'Color', 'XPBoost', 'Shield']

@bot.tree.command(name="daily", description="Khod flous dial lyoum")
@safe()
async def daily_cmd(i: discord.Interaction):
    u = U(i.user.id)
    today = now().date()
    if u["daily"] == today:
        tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        left = int((tomorrow - now()).total_seconds())
        h, rem = divmod(left, 3600)
        return await fail(i, f"Derti daily lyoum deja! Rje3 mn b3d **{h}h {rem // 60}m**")
    u["streak"] = u["streak"] + 1 if u["daily"] == today - timedelta(days=1) else 1
    base = random.randint(100, 300)
    sb = u["streak"] * 20
    b7 = 500 if u["streak"] % 7 == 0 else 0
    total = base + sb + b7
    u["money"] += total
    u["daily"] = today
    await rep(i, embed=emb(f"Khditi **{total}** flous!", fields=[
        ("Base", str(base)), ("Streak bonus", str(sb)), ("Bonus 7 ayam", str(b7)), ("Streak", f"{u['streak']} yawm", False)]))

@bot.tree.command(name="balance", description="Chof flous dialek")
@app_commands.describe(member="Chkoun", show="Wallet awla bank awla juj")
@safe()
async def balance_cmd(i: 【entity-discord¦canonical_name=discord】.Interaction, member: 【entity-discord¦canonical_name=discord】.Member = None, show: Literal['wallet', 'bank', 'both'] = 'both'):
    m = member or i.user
    u = U(m.id)
    fields = []
    if show in ("wallet", "both"):
        fields.append(("Wallet", fmt(u["money"])))
    if show in ("bank", "both"):
        fields.append(("Bank", fmt(u["bank"])))
    await rep(i, embed=emb(f"Flous dial {m.mention}", fields=fields))

@bot.tree.command(name="deposit", description="Dkhel flous mn wallet l bank")
@app_commands.describe(amount="Chhal")
@safe()
async def deposit_cmd(i: discord.Interaction, amount: Literal['100', '500', '1000', 'all']):
    u = U(i.user.id)
    amt = u["money"] if amount == "all" else int(amount)
    if amt <= 0 or amt > u["money"]:
        return await fail(i, "Ma 3ndekch had l mablagh f wallet.")
    u["money"] -= amt
    u["bank"] += amt
    await rep(i, embed=emb(f"Dkhlti **{fmt(amt)}** l bank.", fields=[("Wallet", fmt(u["money"])), ("Bank", fmt(u["bank"]))]))

@bot.tree.command(name="withdraw", description="Khrej flous mn bank l wallet")
@app_commands.describe(amount="Chhal")
@safe()
async def withdraw_cmd(i: discord.Interaction, amount: app_commands.Range[int, 1, 100000000]):
    u = U(i.user.id)
    if amount > u["bank"]:
        return await fail(i, "Ma 3ndekch had l mablagh f bank.")
    u["bank"] -= amount
    u["money"] += amount
    await rep(i, embed=emb(f"Khrjti **{fmt(amount)}** mn bank.", fields=[("Wallet", fmt(u["money"])), ("Bank", fmt(u["bank"]))]))

@bot.tree.command(name="transfer", description="Sift flous l chi wa7ed")
@app_commands.describe(member="Chkoun", amount="Chhal", message="Message ikhtiyari")
@safe()
async def transfer_cmd(i: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, 100000000],
                       message: str = None):
    if member.bot or member.id == i.user.id:
        return await fail(i, "Ma tqdarch tsift l rassek awla l bot.")
    u = U(i.user.id)
    if amount > u["money"]:
        return await fail(i, "Ma 3ndekch flous kafyin f wallet.")
    async def do():
        s, r = U(i.user.id), U(member.id)
        if amount > s["money"]:
            return emb("Flous ma b9awch kafyin.")
        s["money"] -= amount
        r["money"] += amount
        note = f"\nMessage: {message}" if message else ""
        return emb(f"{i.user.mention} sift **{fmt(amount)}** l {member.mention}{note}")
    view = ConfirmView(i.user.id, do)
    view.message = await rep(i, embed=emb(f"Wach mTa2ked bghiti tsift **{fmt(amount)}** l {member.mention}?"), view=view)

@bot.tree.command(name="gamble", description="Lo3b b flous dialek")
@app_commands.describe(amount="Chhal", game="Lo3ba", pick="coinflip: ras/ktaba | dice: 1-6 | roulette: red/black")
@safe()
async def gamble_cmd(i: discord.Interaction, amount: app_commands.Range[int, 1, 1000000],
                     game: Literal['coinflip', 'dice', 'slot', 'roulette'], pick: str = None):
    u = U(i.user.id)
    if amount > u["money"]:
        return await fail(i, "Ma 3ndekch flous kafyin f wallet.")
    pick = (pick or "").strip().lower()
    mult, detail = 0, ""
    if game == "coinflip":
        pick = pick if pick in ("ras", "ktaba") else random.choice(["ras", "ktaba"])
        res = random.choice(["ras", "ktaba"])
        mult = 2 if res == pick else 0
        detail = f"Khtarti **{pick}** w tla3 **{res}**"
    elif game == "dice":
        if not pick.isdigit() or not 1 <= int(pick) <= 6:
            return await fail(i, "F dice khtar raqm mn 1 l 6 f `pick`.")
        res = random.randint(1, 6)
        mult = 5 if res == int(pick) else 0
        detail = f"Khtarti **{pick}** w tla3 **{res}**"
    elif game == "slot":
        res = [random.choice(["🍒", "🍋", "🍇", "💎"]) for _ in range(3)]
        mult = 10 if len(set(res)) == 1 else 0
        detail = " | ".join(res)
    else:
        if pick not in ("red", "black"):
            return await fail(i, "F roulette khtar `red` awla `black` f `pick`.")
        n = random.randint(0, 36)
        reds = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        col = "green" if n == 0 else ("red" if n in reds else "black")
        mult = 2 if col == pick else 0
        detail = f"Khtarti **{pick}** w tla3 **{n} ({col})**"
    net = amount * (mult - 1)
    u["money"] += net
    txt = f"Rbe7ti **{fmt(amount * mult)}** (x{mult})" if mult else f"Khsarti **{fmt(amount)}**"
    await rep(i, embed=emb(f"**{game}**\n{detail}\n\n{txt}", fields=[("Wallet", fmt(u["money"]))]))

@bot.tree.command(name="work", description="Khdem w rbe7 flous (cooldown sa3a)")
@app_commands.describe(job="Khtar khdmtek")
@safe()
async def work_cmd(i: discord.Interaction, job: Literal['police', 'doctor', 'teacher', 'gamer', 'hacker', 'streamer']):
    u = U(i.user.id)
    left = 3600 - (time.time() - u["work_last"])
    if left > 0:
        return await fail(i, f"3ayyiti! Rje3 mn b3d **{int(left // 60)} dqiqa**.")
    earn = random.randint(50, 200)
    u["money"] += earn
    u["job"] = job
    u["work_last"] = time.time()
    await rep(i, embed=emb(f"{random.choice(JOBS[job])}\nKhditi **{earn}** flous.", fields=[("Job", job)]))
    await add_xp(i.user, 15)

@bot.tree.command(name="rob", description="7awel tsre9 chi wa7ed (khatar!)")
@app_commands.describe(member="Chkoun", stealth="low: 40% | high: 60% w ghrama kbira")
@safe()
async def rob_cmd(i: discord.Interaction, member: discord.Member, stealth: Literal['low', 'high'] = 'low'):
    if member.bot or member.id == i.user.id:
        return await fail(i, "Ma tqdarch tsre9 l rassek awla l bot.")
    u, v = U(i.user.id), U(member.id)
    left = 300 - (time.time() - u["rob_last"])
    if left > 0:
        return await fail(i, f"Tsenna **{int(left)} tanya** 9bal ma t3awd tsre9.")
    if u["money"] < 50:
        return await fail(i, "Khassek 3la l9el 50 flous bach t9der t7awel.")
    if v["money"] < 100:
        return await fail(i, "Had l member ma 3ndoch flous kafyin.")
    u["rob_last"] = time.time()
    chance, fpct, spct = (0.40, 0.10, 0.30) if stealth == "low" else (0.60, 0.25, 0.50)
    if "Shield" in v["inv"]:
        v["inv"].remove("Shield")
        fine = min(u["money"], 50)
        u["money"] -= fine
        return await rep(i, embed=emb(f"{member.mention} 3ndo **Shield**! Tkssr l shield w khsarti **{fine}** flous."))
    if random.random() < chance:
        stolen = max(1, int(v["money"] * random.uniform(0.1, spct)))
        v["money"] -= stolen
        u["money"] += stolen
        await rep(i, embed=emb(f"Najaht! Srti **{fmt(stolen)}** mn {member.mention}"))
    else:
        fine = min(u["money"], max(50, int(u["money"] * fpct)))
        u["money"] -= fine
        v["money"] += fine
        await rep(i, embed=emb(f"T7bst! Khlst ghrama **{fmt(fine)}** l {member.mention}"))

@bot.tree.command(name="shop", description="Chof l7anout")
@safe()
async def shop_cmd(i: discord.Interaction):
    fields = [(f"{v[0]} - {fmt(v[1])}", v[2], False) for v in SHOP.values()]
    await rep(i, embed=emb("**L7anout dial CYBER HEAVEN**\nUsi `/buy` bach tchri", fields=fields))

@bot.tree.command(name="buy", description="Chri chi 7aja mn l7anout")
@app_commands.describe(item="Chno bghiti")
@safe()
async def buy_cmd(i: discord.Interaction, item: ItemChoice):
    u = U(i.user.id)
    label, price, _ = SHOP[item]
    if item in ("VIP", "Legend") and item in u["inv"]:
        return await fail(i, "3ndek had l role deja.")
    if u["money"] < price:
        return await fail(i, f"Khassek **{fmt(price - u['money'])}** flous zyada.")
    u["money"] -= price
    u["inv"].append(item)
    note = ""
    if item in ("VIP", "Legend"):
        role = await get_role(i.guild, item)
        try:
            await i.user.add_roles(role)
            note = f"\nT3ti role **{item}**!"
        except Exception:
            note = "\nChriti walakin ma9dertch n3tik role (3ali role dial l bot)."
    await rep(i, embed=emb(f"Chriti **{label}** b {fmt(price)} flous.{note}", fields=[("Wallet", fmt(u["money"]))]))

@bot.tree.command(name="inventory", description="Chof l7wayj dialek")
@app_commands.describe(member="Chkoun")
@safe()
async def inventory_cmd(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    c = Counter(U(m.id)["inv"])
    desc = "\n".join(f"{SHOP[k][0]} x{n}" for k, n in c.items()) or "Inventory khawi."
    await rep(i, embed=emb(f"Inventory dial {m.mention}\n\n{desc}"))

@bot.tree.command(name="use", description="St3mel chi 7aja mn inventory")
@app_commands.describe(item="Chno bghiti tst3mel")
@safe()
async def use_cmd(i: discord.Interaction, item: ItemChoice):
    u = U(i.user.id)
    if item not in u["inv"]:
        return await fail(i, "Ma 3ndekch had l 7aja f inventory.")
    if item in ("VIP", "Legend"):
        role = await get_role(i.guild, item)
        await i.user.add_roles(role)
        return await rep(i, embed=emb(f"Role **{item}** tfa3l 3lik."))
    if item == "Color":
        name = f"Color-{i.user.name}"[:90]
        col = discord.Colour(random.randint(0, 0xFFFFFF))
        role = discord.utils.get(i.guild.roles, name=name)
        if role:
            await role.edit(colour=col)
        else:
            role = await i.guild.create_role(name=name, colour=col)
        await i.user.add_roles(role)
        u["inv"].remove("Color")
        return await rep(i, embed=emb(f"T3ti lon jdid: **#{col.value:06x}**", color=col.value))
    if item == "XPBoost":
        u["inv"].remove("XPBoost")
        u["boost"] = time.time() + 3600
        return await rep(i, embed=emb("XP Boost tfa3l: **x2 XP** l 1 sa3a!"))
    await rep(i, embed=emb("Shield dima tfa3l automatically, ghadi y7mik mn rob jay."))

BALL = ["Iyeh, 100%", "Bla chak", "Akid", "Ra bayna", "Ymkn", "3ndi ghir 50/50", "Ma3raftch, 3awd s9sini mn ba3d",
        "Rkez w 3awd", "Ma tkhmmch bzaf, ghadi tdwi", "Ma3ndich jawab daba", "La, ma tdirhch", "Jawabi: la",
        "Ma kaynch chi chance", "Machi hiya hadik", "Hmmm, ana ma kan3tqdch", "Dir li bghiti w tawakkal",
        "Kolchi ghadi ymchi l khir", "Sir 3la rasek", "Sbr w ghadi tchof", "Lmouhim tkoun m3a l 3a2ila"]
TRUTHS = ["Achno akbar khta3 dertiha f 7yatek?", "Chkoun akhir wa7ed kteb lik f tilifoun?", "Achno akthar 7aja kat5afha?",
          "Wach 3mrek kdbti 3la chi sa7bek? 3la ach?", "Achno akthar lo3ba katb3ha f tilifoun dialk?",
          "Achno ahsan dikra 3ndek m3a l friends?", "Chkoun l member li kat7eb b3da f server?",
          "Achno akthar klma kat9olha?", "Wach kat3ref chi secret w ma 9ltihch?", "Achno hlm dialk f 7yatek?"]
DARES = ["Sift voice message kat7der b sout dial robot.", "Beddel smiyt dialk f server l 10 dqayq.",
         "Kteb chi poeme 3la l 3a2ila dial CYBER HEAVEN.", "Hder b Darija 3la tari9a dial chi charakter m3roufa.",
         "Sift sora dial akhir 7aja akhditi f tilifoun.", "Dir 10 push-ups w sift chi dalil.",
         "Kteb 5 7ajat katbghihom f had server.", "Gol nokta w ma tdhekch.",
         "Beddel avatar dialk l 1 sa3a.", "3ayet l a7ssan wa7ed f friends w gol lih mar7ba."]
JOKES = {
    "dahk": ["Wa7ed 9al l sa7bo: ana dayr regime. 9al lih: kifach? 9al: kan3ti rassi l jou3 7ta ykhlsou l flous.",
             "Chno 9al l bi9a l l bi9a? Ma3raftch, 7it mdawwekh b l 7ar.",
             "L mo3alim sa2el: chkoun fikom 9ra? Talib: Ana, walakin ghir lfaryda."],
    "darija": ["Wa7ed kay9ol: l3bt l loto 20 3am, w daba rbe7t: dakchi li kan khsni, l 9ana3a.",
               "Mra 9alt l ra jel: tilifoun w ana, 3la ina wa7ed kat7eb? 9al: 3la lli 3ndo batterie 100%.",
               "Tatay m3a l 3a2ila 7ta f l 9ayd, w kolchi 3ayt: sir 7ewwes 3la s3ad."],
    "dark": ["Ana w l wifi 3ndna nafs l 7al: dima kan3ti w kaytqta3 b3d chwiya.",
             "9alo li l7yat qasya, walakin l batterie dial tilifoun dyali aqsa.",
             "L ghd 3ndi imtihan, w ana kanqra b7al li ghadi n3ich f dunya khra."],
    "programming": ["Chno l far9 bin programmer w l kitab? L kitab 3ndo documentation.",
                    "Programmer 9al l mra: sir jib 7lib, w ila l9iti 3 byod jib 6. Rja3 b 6 7lib.",
                    "Bug f code? Ma3 7ta bug, hadi feature jdida."],
}
MEMES = [("【entity-Drake¦canonical_name=Drake】 approves had l meme", "https://i.imgflip.com/30b1gx.jpg"),
         ("One does not simply... tkhrj mn CYBER HEAVEN", "https://i.imgflip.com/1bij.jpg"),
         ("Distracted boyfriend f server dial friends", "https://i.imgflip.com/1ur9b0.jpg"),
         ("Two buttons: lo3b / nam", "https://i.imgflip.com/1g8my4.jpg"),
         ("Change my mind: CYBER HEAVEN a7sen server", "https://i.imgflip.com/24y43o.jpg")]
HUGS = {
    "hug": ["{a} 3anaq {b} b 9wa!", "{a} 3tat 7odn kbir l {b}."],
    "kiss": ["{a} 7et bsa 3la ras {b}.", "{a} bsa {b} b 7obb."],
    "slap": ["{a} 3tat sfa3a khfifa l {b} (ghir mzah!).", "{a} sf3 {b} b 9alam dial hawa."],
    "pat": ["{a} ma7a 3la ras {b}.", "{a} tbpat 3la ktef {b}: ghadi ykoun kolchi mzyan."],
}
QUIZ = {
    "general": {"easy": ("Chhal fiha mn nhar f simana?", ["5", "6", "7", "8"], 2),
                "medium": ("Achno hiya 3asimat l Maghrib?", ["Casablanca", "Rabat", "Fes", "Marrakech"], 1),
                "hard": ("Chhal fih mn 3dad awwli bin 1 w 20?", ["6", "7", "8", "9"], 2)},
    "gaming": {"easy": ("Ina lo3ba fiha Creeper w Steve?", ["Roblox", "Minecraft", "Fortnite", "FIFA"], 1),
               "medium": ("Chkoun l chrika li sna3at PlayStation?", ["Sony", "Microsoft", "Nintendo", "Sega"], 0),
               "hard": ("Ina lo3ba fiha Triforce?", ["Mario", "Zelda", "Metroid", "Pokemon"], 1)},
    "anime": {"easy": ("Chkoun l batal dial anime Naruto?", ["Sasuke", "Naruto Uzumaki", "Kakashi", "Itachi"], 1),
              "medium": ("F One Piece, chkoun captain dial Straw Hat?", ["Zoro", "Sanji", "Monkey D. Luffy", "Usopp"], 2),
              "hard": ("Chkoun l mo2alif dial Dragon Ball?", ["Akira Toriyama", "Eiichiro Oda", "Masashi Kishimoto", "Hajime Isayama"], 0)},
    "football": {"easy": ("Chhal mn la3ib f lfari9 f terrain (m3a l goalkeeper)?", ["9", "10", "11", "12"], 2),
                 "medium": ("Chkoun rbe7 coupe du monde 2022?", ["France", "Argentina", "Brazil", "Morocco"], 1),
                 "hard": ("Chkoun awal mantakhab 3arabi w ifriqi wsel nsf nihai f coupe du monde?", ["Algeria", "Egypt", "Morocco", "Tunisia"], 2)},
}
COUNTER = {"hjar": "wra9", "wra9": "m9as", "m9as": "hjar"}

@bot.tree.command(name="8ball", description="Sowel l 8ball w ghadi tjawbek")
@app_commands.describe(question="Soualek")
@safe()
async def eightball_cmd(i: discord.Interaction, question: str):
    await rep(i, embed=emb(fields=[("Souwal", question, False), ("Jawab", random.choice(BALL), False)]))

@bot.tree.command(name="rps", description="Hjar wra9 m9as m3a l bot")
@app_commands.describe(choice="Khtar", difficulty="Sahl awla s3ib")
@safe()
async def rps_cmd(i: discord.Interaction, choice: Literal['hjar', 'wra9', 'm9as'], difficulty: Literal['easy', 'hard'] = 'easy'):
    u = U(i.user.id)
    bot_pick = COUNTER[choice] if (difficulty == "hard" and random.random() < 0.4) else random.choice(list(COUNTER))
    if bot_pick == choice:
        u["rps"][2] += 1
        res = "T3adol!"
    elif COUNTER[bot_pick] == choice:
        u["rps"][0] += 1
        res = "Rbe7ti!"
    else:
        u["rps"][1] += 1
        res = "Khsarti!"
    w, l, d = u["rps"]
    await rep(i, embed=emb(f"Nta: **{choice}** | Bot: **{bot_pick}**\n\n**{res}**", fields=[("Record", f"{w}W / {l}L / {d}D")]))

@bot.tree.command(name="coinflip", description="Rmi l 3omla")
@app_commands.describe(choice="Ras awla ktaba")
@safe()
async def coinflip_cmd(i: discord.Interaction, choice: Literal['ras', 'ktaba']):
    res = random.choice(["ras", "ktaba"])
    await rep(i, embed=emb(f"Khtarti **{choice}** w tla3 **{res}**\n\n" + ("Rbe7ti!" if res == choice else "Khsarti!")))

@bot.tree.command(name="dice", description="Rmi zhar")
@app_commands.describe(sides="3dad l wjouh", guess="Chno kat dhen ghay tla3")
@safe()
async def dice_cmd(i: discord.Interaction, sides: Literal[6, 12, 20] = 6, guess: app_commands.Range[int, 1, 20] = None):
    res = random.randint(1, sides)
    txt = f"Tla3 **{res}** (d{sides})"
    if guess:
        txt += "\n" + ("Dhenti s7i7!" if guess == res else f"Dhenti {guess}, ghalat.")
    await rep(i, embed=emb(txt))

@bot.tree.command(name="slot", description="Slot machine mjaniya")
@safe()
async def slot_cmd(i: discord.Interaction):
    res = [random.choice(["🍒", "🍋", "🍇", "💎", "7️⃣"]) for _ in range(3)]
    await rep(i, embed=emb(" | ".join(res) + "\n\n" + ("JACKPOT!" if len(set(res)) == 1 else "Hder 3awd jarreb!")))

@bot.tree.command(name="truth", description="Souwal dial l7a9i9a")
@safe()
async def truth_cmd(i: discord.Interaction):
    await rep(i, embed=emb(f"**Truth:** {random.choice(TRUTHS)}"))

@bot.tree.command(name="dare", description="Ta7addi 3chwa2i")
@safe()
async def dare_cmd(i: discord.Interaction):
    await rep(i, embed=emb(f"**Dare:** {random.choice(DARES)}"))

@bot.tree.command(name="joke", description="Nokta hzzla")
@app_commands.describe(type="Nou3 dial nokta")
@safe()
async def joke_cmd(i: discord.Interaction, type: Literal['dahk', 'darija', 'dark', 'programming'] = 'darija'):
    await rep(i, embed=emb(f"**{type}**\n\n{random.choice(JOKES[type])}"))

@bot.tree.command(name="meme", description="Meme 3chwa2i")
@safe()
async def meme_cmd(i: discord.Interaction):
    txt, url = random.choice(MEMES)
    await rep(i, embed=emb(txt, image=url))

@bot.tree.command(name="ship", description="Chhal l7ob bin juj members")
@app_commands.describe(member1="L member lawal", member2="L member tani (ikhtiyari)")
@safe()
async def ship_cmd(i: discord.Interaction, member1: discord.Member, member2: discord.Member = None):
    a, b = member1, member2 or i.user
    p = random.Random(min(a.id, b.id) * 31 + max(a.id, b.id)).randint(0, 100)
    msg = ("Bla ma tfkr, tzwjou!" if p >= 90 else "Chemistry zwina!" if p >= 70 else "Fiha chi chance..." if p >= 40
           else "Khass tkhdmou chwiya 3la l friendship." if p >= 20 else "Mzyan ykounou ghir sa7ab.")
    await rep(i, embed=emb(f"{a.mention} + {b.mention}\n\n{bar(p, 100, 20)} **{p}%**\n{msg}"))

@bot.tree.command(name="hug", description="Sift hug awla bsa awla sfa3a")
@app_commands.describe(member="Chkoun", type="Nou3")
@safe()
async def hug_cmd(i: discord.Interaction, member: discord.Member, type: Literal['hug', 'kiss', 'slap', 'pat'] = 'hug'):
    await rep(i, embed=emb(random.choice(HUGS[type]).format(a=i.user.mention, b=member.mention)))

class QuizView(discord.ui.View):
    def __init__(self, uid, opts, correct):
        super().__init__(timeout=30)
        self.uid, self.opts, self.correct = uid, opts, correct
        self.answered = False
        self.message = None
        for idx, o in enumerate(opts):
            b = discord.ui.Button(label=f"{'ABCD'[idx]}. {o}"[:80], style=discord.ButtonStyle.secondary)
            b.callback = self.make_cb(idx)
            self.add_item(b)
    def make_cb(self, idx):
        async def cb(it):
            if it.user.id != self.uid:
                return await it.response.send_message(embed=emb("Had l quiz machi dialk."), ephemeral=True)
            if self.answered:
                return await it.response.defer()
            self.answered = True
            ok = idx == self.correct
            for n, c in enumerate(self.children):
                c.disabled = True
                c.style = (discord.ButtonStyle.success if n == self.correct
                           else discord.ButtonStyle.danger if n == idx else discord.ButtonStyle.secondary)
            if ok:
                U(self.uid)["money"] += 100
            await it.response.edit_message(embed=emb("Jawab s7i7! Rbe7ti **100** flous." if ok else
                                                     f"Jawab ghalat. S7i7 howa **{self.opts[self.correct]}**"), view=self)
            self.stop()
        return cb
    async def on_timeout(self):
        if self.answered or not self.message:
            return
        for n, c in enumerate(self.children):
            c.disabled = True
            if n == self.correct:
                c.style = discord.ButtonStyle.success
        try:
            await self.message.edit(embed=emb(f"Wa9t salla! L jawab kan **{self.opts[self.correct]}**"), view=self)
        except Exception:
            pass

@bot.tree.command(name="quiz", description="Quiz b 4 ikhtiyarat w 30 tanya")
@app_commands.describe(category="L9ism", difficulty="Sa3ouba")
@safe()
async def quiz_cmd(i: discord.Interaction, category: Literal['general', 'gaming', 'anime', 'football'] = 'general',
                   difficulty: Literal['easy', 'medium', 'hard'] = 'easy'):
    q, opts, correct = QUIZ[category][difficulty]
    view = QuizView(i.user.id, opts, correct)
    view.message = await rep(i, embed=emb(f"**{category} - {difficulty}**\n\n{q}\n\nGhadi tkhd 100 flous ila jawabti s7i7 f 30 tanya."), view=view)

DEL_SECS = {"0": 0, "1day": 86400, "7days": 604800}
TO_MINS = {"1min": 1, "10min": 10, "1h": 60, "1day": 1440}

async def delayed_unban(guild, uid, secs):
    await asyncio.sleep(secs)
    try:
        await guild.unban(discord.Object(id=uid), reason="Temp ban salla")
        await send_log(guild, "Auto-Unban", bot.user, f"<@{uid}>", "Temp ban salla")
    except Exception:
        pass

@bot.tree.command(name="kick", description="Tred chi member mn server")
@app_commands.describe(member="Chkoun", reason="Sabab", delete_messages="Mse7 l messages dialo")
@app_commands.default_permissions(kick_members=True)
@safe(eph=True, perm="kick_members")
async def kick_cmd(i: discord.Interaction, member: discord.Member, reason: str = "Bla sabab",
                   delete_messages: Literal['0', '1day', '7days'] = '0'):
    err = hier_error(i, member)
    if err:
        return await fail(i, err)
    await dm(member, emb(f"T9ad tkicka mn **{i.guild.name}**\nSabab: {reason}"))
    if delete_messages != "0":
        await i.guild.ban(member, reason=reason, delete_message_seconds=DEL_SECS[delete_messages])
        await i.guild.unban(member, reason="Kick m3a delete messages")
    else:
        await member.kick(reason=reason)
    await send_log(i.guild, "Kick", i.user, member, reason)
    await rep(i, embed=emb(f"T kicka **{member}**\nSabab: {reason}"), ephemeral=True)

@bot.tree.command(name="ban", description="Bani chi member (mo2aqqat awla dayim)")
@app_commands.describe(member="Chkoun", reason="Sabab", duration="Moda", delete_messages="Mse7 l messages")
@app_commands.default_permissions(ban_members=True)
@safe(eph=True, perm="ban_members")
async def ban_cmd(i: discord.Interaction, member: discord.Member, reason: str = "Bla sabab",
                  duration: Literal['1day', '7days', 'permanent'] = 'permanent',
                  delete_messages: Literal['0', '1day', '7days'] = '0'):
    err = hier_error(i, member)
    if err:
        return await fail(i, err)
    await dm(member, emb(f"T9ad tbanna mn **{i.guild.name}** ({duration})\nSabab: {reason}"))
    await i.guild.ban(member, reason=reason, delete_message_seconds=DEL_SECS[delete_messages])
    if duration != "permanent":
        asyncio.create_task(delayed_unban(i.guild, member.id, DEL_SECS[duration]))
    await send_log(i.guild, f"Ban ({duration})", i.user, member, reason)
    await rep(i, embed=emb(f"T banna **{member}** ({duration})\nSabab: {reason}"), ephemeral=True)

@bot.tree.command(name="unban", description="Fek l ban b ID")
@app_commands.describe(user_id="ID dial l user")
@app_commands.default_permissions(ban_members=True)
@safe(eph=True, perm="ban_members")
async def unban_cmd(i: discord.Interaction, user_id: str):
    if not user_id.strip().isdigit():
        return await fail(i, "ID khassha ykoun ghir arqam.")
    await i.guild.unban(discord.Object(id=int(user_id)), reason=f"Unban by {i.user}")
    await send_log(i.guild, "Unban", i.user, f"<@{user_id}>", "Unban")
    await rep(i, embed=emb(f"T fek l ban 3la <@{user_id}>"), ephemeral=True)

@bot.tree.command(name="timeout", description="3te timeout l chi member")
@app_commands.describe(member="Chkoun", duration="Moda", reason="Sabab")
@app_commands.default_permissions(moderate_members=True)
@safe(eph=True, perm="moderate_members")
async def timeout_cmd(i: discord.Interaction, member: discord.Member, duration: Literal['1min', '10min', '1h', '1day'],
                      reason: str = "Bla sabab"):
    err = hier_error(i, member)
    if err:
        return await fail(i, err)
    await member.timeout(timedelta(minutes=TO_MINS[duration]), reason=reason)
    await send_log(i.guild, f"Timeout ({duration})", i.user, member, reason)
    await rep(i, embed=emb(f"{member.mention} f timeout l **{duration}**\nSabab: {reason}"), ephemeral=True)

@bot.tree.command(name="untimeout", description="Fek timeout 3la chi member")
@app_commands.describe(member="Chkoun")
@app_commands.default_permissions(moderate_members=True)
@safe(eph=True, perm="moderate_members")
async def untimeout_cmd(i: discord.Interaction, member: discord.Member):
    await member.timeout(None, reason=f"Untimeout by {i.user}")
    await send_log(i.guild, "Untimeout", i.user, member, "Timeout tfek")
    await rep(i, embed=emb(f"T fek timeout 3la {member.mention}"), ephemeral=True)

@bot.tree.command(name="warn", description="3te warn l chi member")
@app_commands.describe(member="Chkoun", reason="Sabab", level="Daraja dial warn")
@app_commands.default_permissions(moderate_members=True)
@safe(eph=True, perm="moderate_members")
async def warn_cmd(i: discord.Interaction, member: discord.Member, reason: str, level: Literal[1, 2, 3] = 1):
    err = hier_error(i, member)
    if err:
        return await fail(i, err)
    u = U(member.id)
    u["warns"].append(dict(reason=reason, by=str(i.user), level=level, time=now()))
    await dm(member, emb(f"T3titi warn f **{i.guild.name}**\nSabab: {reason}\nDaraja: {level}"))
    await send_log(i.guild, f"Warn (level {level})", i.user, member, reason)
    action = await check_warn_thresholds(i.guild, member)
    hist = "\n".join(f"{n}. {w['reason']} (L{w['level']})" for n, w in enumerate(u["warns"][-5:], 1))
    await rep(i, embed=emb(f"{member.mention} t3ta warn. Total: **{len(u['warns'])}**",
                            fields=[("Historique", hist, False)] + ([("Action", action, False)] if action else [])), ephemeral=True)

@bot.tree.command(name="warnings", description="Chof warns dial chi member")
@app_commands.describe(member="Chkoun")
@app_commands.default_permissions(moderate_members=True)
@safe(eph=True, perm="moderate_members")
async def warnings_cmd(i: discord.Interaction, member: discord.Member):
    w = U(member.id)["warns"]
    if not w:
        return await rep(i, embed=emb(f"{member.mention} ma 3ndo ta warn."), ephemeral=True)
    lines = [f"**{n}.** {x['reason']} - L{x['level']} - {discord.utils.format_dt(x['time'], 'd')} - {x['by']}"
             for n, x in enumerate(w[-15:], 1)]
    await rep(i, embed=emb(f"Warns dial {member.mention} ({len(w)})\n\n" + "\n".join(lines)), ephemeral=True)

@bot.tree.command(name="clearwarns", description="Mse7 ga3 warns dial chi member")
@app_commands.describe(member="Chkoun")
@app_commands.default_permissions(moderate_members=True)
@safe(eph=True, perm="moderate_members")
async def clearwarns_cmd(i: discord.Interaction, member: discord.Member):
    U(member.id)["warns"].clear()
    await send_log(i.guild, "Clear warns", i.user, member, "Warns tms7o")
    await rep(i, embed=emb(f"T mse7o ga3 warns dial {member.mention}"), ephemeral=True)

@bot.tree.command(name="clear", description="Mse7 messages mn channel")
@app_commands.describe(amount="3dad", user="Mse7 ghir dial had l member", contains="Mse7 ghir li fihom had l klma")
@app_commands.default_permissions(manage_messages=True)
@safe(eph=True, perm="manage_messages")
async def clear_cmd(i: discord.Interaction, amount: Literal[5, 10, 20, 50, 100], user: discord.Member = None,
                    contains: str = None):
    cnt = 0
    def check(m):
        nonlocal cnt
        if cnt >= amount:
            return False
        if user and m.author.id != user.id:
            return False
        if contains and contains.lower() not in m.content.lower():
            return False
        cnt += 1
        return True
    deleted = await i.channel.purge(limit=500 if (user or contains) else amount, check=check)
    await send_log(i.guild, f"Clear ({len(deleted)})", i.user, i.channel, f"user={user} contains={contains}")
    await rep(i, embed=emb(f"T mse7o **{len(deleted)}** message."), ephemeral=True)

@bot.tree.command(name="lock", description="Sed channel (hd mat9dr ykteb)")
@app_commands.describe(channel="Channel", reason="Sabab")
@app_commands.default_permissions(manage_channels=True)
@safe(eph=True, perm="manage_channels")
async def lock_cmd(i: discord.Interaction, channel: discord.TextChannel = None, reason: str = "Bla sabab"):
    ch = channel or i.channel
    ow = ch.overwrites_for(i.guild.default_role)
    ow.send_messages = False
    await ch.set_permissions(i.guild.default_role, overwrite=ow, reason=reason)
    await ch.send(embed=emb(f"Had channel tsedd.\nSabab: {reason}"))
    await send_log(i.guild, "Lock", i.user, ch, reason)
    await rep(i, embed=emb(f"T sedd {ch.mention}"), ephemeral=True)

@bot.tree.command(name="unlock", description="7ell channel")
@app_commands.describe(channel="Channel")
@app_commands.default_permissions(manage_channels=True)
@safe(eph=True, perm="manage_channels")
async def unlock_cmd(i: discord.Interaction, channel: discord.TextChannel = None):
    ch = channel or i.channel
    ow = ch.overwrites_for(i.guild.default_role)
    ow.send_messages = None
    await ch.set_permissions(i.guild.default_role, overwrite=ow)
    await ch.send(embed=emb("Had channel tfet7at men jdid."))
    await send_log(i.guild, "Unlock", i.user, ch, "Unlock")
    await rep(i, embed=emb(f"T fte7 {ch.mention}"), ephemeral=True)

@bot.tree.command(name="slowmode", description="7et slowmode l channel")
@app_commands.describe(channel="Channel", seconds="Tawani")
@app_commands.default_permissions(manage_channels=True)
@safe(eph=True, perm="manage_channels")
async def slowmode_cmd(i: 【entity-discord¦canonical_name=discord】.Interaction, seconds: Literal[0, 5, 10, 30, 60], channel: 【entity-discord¦canonical_name=discord】.TextChannel = None):
    ch = channel or i.channel
    await ch.edit(slowmode_delay=seconds)
    await send_log(i.guild, f"Slowmode {seconds}s", i.user, ch, "Slowmode")
    await rep(i, embed=emb(f"Slowmode f {ch.mention}: **{seconds}s**"), ephemeral=True)

async def post_embed(room, message, color, image, title, ping, btn_text, btn_link):
    e = emb(message.replace("\\n", "\n"), title=title or TITLE, color=color)
    if image and image.strip().lower().startswith("http"):
        e.set_image(url=image.strip())
    kw = {"embed": e, "allowed_mentions": discord.AllowedMentions(everyone=True)}
    content = {"everyone": "|| @everyone ||", "here": "|| @here ||"}.get(ping)
    if content:
        kw["content"] = content
    if btn_text and btn_link and btn_link.strip().lower().startswith("http"):
        v = discord.ui.View()
        v.add_item(discord.ui.Button(label=btn_text[:80], url=btn_link.strip()))
        kw["view"] = v
    return await room.send(**kw)

@bot.tree.command(name="send", description="Sift embed l chi channel (ghir mol l server)")
@app_commands.describe(message="L message", room="Channel", couleur="Lon hex, b7al e66cb6", image_link="Lien dial tswira",
                       title="3onwan", ping="Ping", button_text="Smiyt zer", button_link="Lien dial zer")
@safe(eph=True, owner=True)
async def send_cmd(i: discord.Interaction, message: str, room: discord.TextChannel, couleur: str = "e66cb6",
                   image_link: str = None, title: str = "CYBER HEAVEN",
                   ping: Literal['none', 'everyone', 'here'] = 'none', button_text: str = None, button_link: str = None):
    try:
        await post_embed(room, message, parse_color(couleur), image_link, title, ping, button_text, button_link)
    except 【entity-discord¦canonical_name=discord】.Forbidden:
        return await fail(i, "Ma 3ndich sla7iya nkteb f had channel.")
    await rep(i, embed=emb(f"Sift l message l #{room.name} - mra wahda safi!"), ephemeral=True)

@bot.tree.command(name="send_rules", description="Sift l qawanin l channel dial rules")
@app_commands.default_permissions(administrator=True)
@safe(eph=True, perm="administrator")
async def send_rules_cmd(i: discord.Interaction):
    ch = i.guild.get_channel(RULES_CHANNEL_ID)
    if not ch:
        return await fail(i, "Ma l9itch channel dial rules, chof l ID.")
    await ch.send(content="|| @everyone ||", embed=rules_embed(), allowed_mentions=discord.AllowedMentions(everyone=True))
    await rep(i, embed=emb(f"Sift l qawanin l #{ch.name} - mra wahda safi!"), ephemeral=True)

@bot.tree.command(name="send_welcome", description="Sift welcome embed l channel dial welcome")
@app_commands.default_permissions(administrator=True)
@safe(eph=True, perm="administrator")
async def send_welcome_cmd(i: discord.Interaction):
    ch = i.guild.get_channel(WELCOME_CHANNEL_ID)
    if not ch:
        return await fail(i, "Ma l9itch channel dial welcome, chof l ID.")
    await ch.send(embed=welcome_embed())
    await rep(i, embed=emb(f"Sift welcome l #{ch.name} - mra wahda safi!"), ephemeral=True)

@bot.tree.command(name="announce", description="Sift i3lan m3a @everyone")
@app_commands.describe(message="L i3lan", room="Channel", couleur="Lon hex", image_link="Lien dial tswira")
@app_commands.default_permissions(administrator=True)
@safe(eph=True, perm="administrator")
async def announce_cmd(i: discord.Interaction, message: str, room: discord.TextChannel, couleur: str = "e66cb6",
                       image_link: str = None):
    try:
        await post_embed(room, message, parse_color(couleur), image_link, "ANNOUNCEMENT - CYBER HEAVEN", "everyone", None, None)
    except discord.Forbidden:
        return await fail(i, "Ma 3ndich sla7iya nkteb f had channel.")
    await rep(i, embed=emb(f"Sift l i3lan l #{room.name} - mra wahda safi!"), ephemeral=True)

@bot.tree.command(name="setup", description="7ded channels dial log, starboard, suggestions, staff")
@app_commands.describe(type="Ina channel", channel="Channel")
@app_commands.default_permissions(administrator=True)
@safe(eph=True, perm="administrator")
async def setup_cmd(i: discord.Interaction, type: Literal['log', 'starboard', 'suggest', 'staff'], channel: discord.TextChannel):
    cfg[type] = channel.id
    await rep(i, embed=emb(f"Channel dial **{type}** daba howa {channel.mention}"), ephemeral=True)

async def close_ticket_channel(channel, closer):
    t = tickets.get(channel.id)
    if t is None:
        return "Hada machi ticket."
    if closer.id != t["owner"] and not is_staff(closer):
        return "Ghir sa7eb ticket awla l staff y9dro ysedo."
    if t.get("closing"):
        return "Ticket kaytsedd deja."
    t["closing"] = True
    await channel.send(embed=emb("Had ticket ghadi ytsedd f 5 tawani..."))
    await asyncio.sleep(5)
    tickets.pop(channel.id, None)
    await channel.delete(reason=f"Ticket closed by {closer}")
    return None

class TicketView(【entity-discord¦canonical_name=discord】.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @【entity-discord¦canonical_name=discord】.ui.button(label="Close", style=【entity-discord¦canonical_name=discord】.ButtonStyle.danger)
    async def close(self, it, button):
        t = tickets.get(it.channel.id)
        if not t or (it.user.id != t["owner"] and not is_staff(it.user)) or t.get("closing"):
            return await it.response.send_message(embed=emb("Ma9drtich ntsedd had ticket."), ephemeral=True)
        await it.response.defer()
        await close_ticket_channel(it.channel, it.user)
    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success)
    async def claim(self, it, button):
        t = tickets.get(it.channel.id)
        if not t or not is_staff(it.user):
            return await it.response.send_message(embed=emb("Ghir l staff y9dro ycl3imo."), ephemeral=True)
        if t.get("claimed"):
            return await it.response.send_message(embed=emb("Ticket deja claimed."), ephemeral=True)
        t["claimed"] = it.user.id
        await it.response.send_message(embed=emb(f"{it.user.mention} claima had ticket."))

@bot.tree.command(name="ticket", description="7el ticket private m3a l staff")
@app_commands.describe(reason="Sabab")
@safe(eph=True)
async def ticket_cmd(i: discord.Interaction, reason: Literal['support', 'report', 'suggestion', 'other'] = 'support'):
    for cid, t in tickets.items():
        if t["owner"] == i.user.id and i.guild.get_channel(cid):
            return await fail(i, f"3ndek ticket m7loula deja: <#{cid}>")
    ow = {i.guild.default_role: discord.PermissionOverwrite(view_channel=False),
          i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
          i.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)}
    for r in i.guild.roles:
        if r != i.guild.default_role and (r.permissions.manage_messages or r.permissions.administrator):
            ow[r] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    name = re.sub(r"[^a-z0-9-]", "", i.user.name.lower()) or str(i.user.id)
    ch = await i.guild.create_text_channel(f"ticket-{name}", overwrites=ow, category=i.channel.category,
                                           reason=f"Ticket by {i.user}")
    tickets[ch.id] = {"owner": i.user.id, "claimed": None}
    await ch.send(content=i.user.mention, embed=emb(f"Mar7ba bik {i.user.mention}!\nSabab: **{reason}**\nL staff ghadi yjawbek 9riban.\nSed ticket b zer **Close**."),
                  view=TicketView())
    await send_log(i.guild, "Ticket opened", i.user, ch, reason)
    await rep(i, embed=emb(f"T7ell ticket dialk: {ch.mention}"), ephemeral=True)

@bot.tree.command(name="close_ticket", description="Sed ticket")
@safe(eph=True)
async def close_ticket_cmd(i: discord.Interaction):
    await rep(i, embed=emb("Ok, kan7awel nsedd ticket..."), ephemeral=True)
    err = await close_ticket_channel(i.channel, i.user)
    if err:
        await i.followup.send(embed=emb(err), ephemeral=True)

@bot.tree.command(name="add_user", description="Zid member l ticket")
@app_commands.describe(member="Chkoun")
@safe(eph=True)
async def add_user_cmd(i: discord.Interaction, member: discord.Member):
    t = tickets.get(i.channel.id)
    if not t:
        return await fail(i, "Had l command khdama ghir f ticket.")
    if i.user.id != t["owner"] and not is_staff(i.user):
        return await fail(i, "Ghir sa7eb ticket awla l staff y9dro yzido nas.")
    await i.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
    await rep(i, embed=emb(f"T zad {member.mention} l ticket."), ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.entries = set()
    @discord.ui.button(label="Join (0)", style=discord.ButtonStyle.primary)
    async def join(self, it, button):
        if it.user.id in self.entries:
            self.entries.discard(it.user.id)
        else:
            self.entries.add(it.user.id)
        button.label = f"Join ({len(self.entries)})"
        await it.response.edit_message(view=self)

async def finish_giveaway(msg, view, prize, winners, secs, host):
    await asyncio.sleep(secs)
    try:
        for c in view.children:
            c.disabled = True
        ids = list(view.entries)
        picked = random.sample(ids, min(winners, len(ids))) if ids else []
        text = ", ".join(f"<@{w}>" for w in picked) if picked else "Hta wa7ed ma charek"
        await msg.edit(embed=emb(f"**Giveaway salla!**\nPrize: **{prize}**\nWinners: {text}"), view=view)
        if picked:
            await msg.channel.send(content=text, embed=emb(f"Mabrouk! Rbe7ti **{prize}**"),
                                   allowed_mentions=discord.AllowedMentions(users=True))
    except Exception as ex:
        print(f"[GIVEAWAY] {ex!r}")

@bot.tree.command(name="giveaway", description="Dir giveaway b zer Join")
@app_commands.describe(prize="Jaiza", duration_minutes="Moda b dqayq", winners="3dad dial rabi7in")
@app_commands.default_permissions(manage_guild=True)
@safe(eph=True, perm="manage_guild")
async def giveaway_cmd(i: discord.Interaction, prize: str, duration_minutes: Literal[5, 15, 60, 1440],
                       winners: Literal[1, 2, 3] = 1):
    end = now() + timedelta(minutes=duration_minutes)
    view = GiveawayView()
    e = emb(f"**GIVEAWAY**\nPrize: **{prize}**\nWinners: **{winners}**\nKheyt: {discord.utils.format_dt(end, 'R')}\nHost: {i.user.mention}\n\nDghat 3la **Join**!")
    msg = await i.channel.send(embed=e, view=view)
    asyncio.create_task(finish_giveaway(msg, view, prize, winners, duration_minutes * 60, i.user))
    await rep(i, embed=emb("T lanca giveaway!"), ephemeral=True)

class PollView(discord.ui.View):
    def __init__(self, question, options):
        super().__init__(timeout=None)
        self.q, self.opts, self.votes = question, options, {}
        for idx, o in enumerate(options):
            b = discord.ui.Button(label=o[:80], style=discord.ButtonStyle.secondary)
            b.callback = self.make_cb(idx)
            self.add_item(b)
    def make_cb(self, idx):
        async def cb(it):
            self.votes[it.user.id] = idx
            await it.response.edit_message(embed=self.embed())
        return cb
    def embed(self, ended=False):
        counts = Counter(self.votes.values())
        total = len(self.votes)
        lines = []
        for n, o in enumerate(self.opts):
            c = counts.get(n, 0)
            pct = round(100 * c / total) if total else 0
            lines.append(f"**{o}**\n{bar(c, max(total, 1), 12)} {c} ({pct}%)")
        head = "**POLL SALLA**" if ended else "**POLL**"
        return emb(f"{head}\n{self.q}\n\n" + "\n\n".join(lines) + f"\n\nTotal: **{total}** vote")

async def finish_poll(msg, view, secs):
    await asyncio.sleep(secs)
    try:
        for c in view.children:
            c.disabled = True
        await msg.edit(embed=view.embed(ended=True), view=view)
    except Exception as ex:
        print(f"[POLL] {ex!r}")

@bot.tree.command(name="poll", description="Dir sondage b zrar")
@app_commands.describe(question="Souwal", option1="Ikhtiyar 1", option2="Ikhtiyar 2", option3="Ikhtiyar 3 (ikhtiyari)",
                       option4="Ikhtiyar 4 (ikhtiyari)", duration="Moda")
@app_commands.default_permissions(manage_messages=True)
@safe(eph=True, perm="manage_messages")
async def poll_cmd(i: discord.Interaction, question: str, option1: str, option2: str, option3: str = None,
                   option4: str = None, duration: Literal['1h', '6h', '24h'] = '24h'):
    opts = [o for o in (option1, option2, option3, option4) if o]
    view = PollView(question, opts)
    msg = await i.channel.send(embed=view.embed(), view=view)
    asyncio.create_task(finish_poll(msg, view, {"1h": 3600, "6h": 21600, "24h": 86400}[duration]))
    await rep(i, embed=emb("T lanca poll!"), ephemeral=True)

@bot.tree.command(name="counting_setup", description="7ded channel dial counting game")
@app_commands.describe(channel="Channel")
@app_commands.default_permissions(manage_channels=True)
@safe(eph=True, perm="manage_channels")
async def counting_setup_cmd(i: discord.Interaction, channel: discord.TextChannel):
    counting["channel"] = channel.id
    counting["current"] = 0
    await channel.send(embed=emb("**Counting game!** Bda t3ed mn **1**. Ay ghalta = restart."))
    await rep(i, embed=emb(f"Counting f {channel.mention} bda!"), ephemeral=True)

class VoteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.votes = {}
    def refresh(self):
        c = Counter(self.votes.values())
        self.up.label = f"Upvote ({c.get(1, 0)})"
        self.down.label = f"Downvote ({c.get(-1, 0)})"
    @discord.ui.button(label="Upvote (0)", style=discord.ButtonStyle.success)
    async def up(self, it, button):
        self.votes[it.user.id] = 1
        self.refresh()
        await it.response.edit_message(view=self)
    @discord.ui.button(label="Downvote (0)", style=discord.ButtonStyle.danger)
    async def down(self, it, button):
        self.votes[it.user.id] = -1
        self.refresh()
        await it.response.edit_message(view=self)

@bot.tree.command(name="suggest", description="Sift fikra l server")
@app_commands.describe(idea="L fikra dialk")
@safe(eph=True)
async def suggest_cmd(i: discord.Interaction, idea: str):
    ch = chan(i.guild, "suggest", ("suggestions", "suggestion")) or i.channel
    e = emb(f"**Suggestion jdida**\n\n{idea}", fields=[("Mn 3end", i.user.mention)], author=(i.user.display_name, i.user.display_avatar.url))
    await ch.send(embed=e, view=VoteView())
    await rep(i, embed=emb(f"Sift l fikra dialk l {ch.mention}"), ephemeral=True)

@bot.tree.command(name="report", description="Dir report 3la chi member b secret")
@app_commands.describe(member="Chkoun", reason="Sabab", proof_image="Sora dalil (ikhtiyari)")
@safe(eph=True)
async def report_cmd(i: discord.Interaction, member: discord.Member, reason: str, proof_image: discord.Attachment = None):
    ch = chan(i.guild, "staff", ("staff", "reports", "report", "mod-chat"))
    if not ch:
        return await fail(i, "Ma kayn ta channel dial staff, golo l admin y7ded wa7ed b /setup.")
    e = emb("**Report jdid (anonymous)**", fields=[("Member", f"{member.mention} ({member.id})"), ("Sabab", reason, False)])
    if proof_image and (proof_image.content_type or "").startswith("image"):
        e.set_image(url=proof_image.url)
    await ch.send(embed=e)
    await rep(i, embed=emb("Sift l report l staff b secret. Chokran!"), ephemeral=True)

async def do_remind(user, channel, secs, text):
    await asyncio.sleep(secs)
    e = emb(f"**Tfkir:** {text}")
    if not await dm(user, e):
        try:
            await channel.send(content=user.mention, embed=e)
        except Exception:
            pass

@bot.tree.command(name="remind", description="Tfkerni mn b3d chwiya")
@app_commands.describe(time="Mnin", message="Chno nfkrek")
@safe(eph=True)
async def remind_cmd(i: discord.Interaction, time: Literal['10min', '1h', '1day'], message: str):
    secs = {"10min": 600, "1h": 3600, "1day": 86400}[time]
    asyncio.create_task(do_remind(i.user, i.channel, secs, message))
    await rep(i, embed=emb(f"Ghadi nfkrek mn b3d **{time}**: {message}"), ephemeral=True)

@bot.tree.command(name="lyrics", description="Lyrics placeholder dial chi 8nya")
@app_commands.describe(song="Smiyt l 8nya")
@safe()
async def lyrics_cmd(i: discord.Interaction, song: str):
    await rep(i, embed=emb(f"**{song}**\n\n(Placeholder) La la la... Hadi lyrics mzyoufa, l bot ma kayqraych music.\nCherchi 3la lyrics l7a9i9iya f chi site rasmi."))

@bot.tree.command(name="nowplaying", description="Chno kayn kayched l bot (placeholder)")
@safe()
async def nowplaying_cmd(i: discord.Interaction):
    await rep(i, embed=emb("**Now playing (placeholder)**\nL bot ma kayd5ol f voice, hadi ghir tajriba text."))

ASK = ["Hmmm, sowelek mzyan, w jawabi: iyeh!", "Ana ghir bot, walakin kan9ol lik: sbr w ghadi tchof.",
       "Fkr mra khra, w ghadi t7es b l jawab.", "Chwiya dial l 9ahwa w ghadi yt7el kolchi.",
       "Sma3 l 3a2ila dialk, homa a3rf mni.", "Jawab l 7a9i9i: ma3raftch, walakin n7eb nrbe7 m3ak.",
       "Dir li katchof mzyan, w tawakkal 3la Allah.", "Hadchi kay7tajj chwiya dial sbr.",
       "Kter mn l ma w qell mn l khoof.", "Sowel wa7ed mn l admins, homa y3rfo mzyan.",
       "Ana kan9ol: sir f tari9ek!", "Jawab 3ndi: ila l9iti l fa2ida, dirha.",
       "Iyeh w la f nafs l wa9t, hh.", "Mchi l9it l jawab f google, w ana hna.", "Lyom nhar zwin, mat7mlch hmm."]

@bot.tree.command(name="ask", description="Sowel l bot w ghadi yjawbek b tari9a mdarbliya")
@app_commands.describe(question="Soualek")
@safe()
async def ask_cmd(i: discord.Interaction, question: str):
    await rep(i, embed=emb(fields=[("Souwal", question, False), ("Jawab", random.choice(ASK), False)]))

# ============================================
# TOKEN - RAILWAY VERSION - MAT7ATCH TOKEN HNA
# TOKEN kayt7at f Railway > Variables > TOKEN
# ============================================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("TOKEN makaynch f Railway Variables! Zido f Railway > Variables > TOKEN")
else:
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("Token ghalet, chof wach lsa9tih mzyan f Railway")
