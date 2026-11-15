
import os
import random
import re
import time
import asyncio
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

PINK = 0xe66cb6
TITLE = "CYBER HEAVEN"
FOOTER = "CYBER HEAVEN - Welcome to the family"
MAIN_IMAGE = "https://cdn.discordapp.com/attachments/1522319156614266890/1570902791667322960/903307255_1448823723986247_5560795212911455220_n.webp?ex=6af8c8bb&is=6af7773b&hm=c6365483f51bf48ef0afe790a2a3990236c2b6f702aa456835c80461f477224e&"
WELCOME_CHANNEL_ID = 1569130814355021915
RULES_CHANNEL_ID = 1510457472471535767
LEVEL_UP_CHANNEL_ID = 1568227584376836137

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

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents, help_command=None)
START = datetime.now(timezone.utc)

users = {}
afk = {}
cfg = {"log": None, "starboard": None, "suggest": None, "staff": None}
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
INVITE_RE = re.compile(r"(discord\.gg|discord(app)?\.com/invite)/\w+", re.I)

def U(uid):
    if uid not in users:
        users[uid] = dict(money=500, bank=0, xp=0, level=1, streak=0, daily=None, inv=[], job=None, warns=[], work_last=0.0, rob_last=0.0, boost=0.0, rps=[0,0,0])
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
        import functools
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
        level_channel = member.guild.get_channel(LEVEL_UP_CHANNEL_ID) if member.guild else None
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
    return emb(f"Mar7ba bik {who} f **CYBER HEAVEN**!\nHna kolna 3a2ila wa7da: nl3bo, nhedro, nderro chill w bla drama.\nKhod raha w ntiya f dar dialk.", image=MAIN_IMAGE, color=PINK)

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
        return "Ma9dertch ndir l action automatique"
    return ""

async def auto_warn(message, reason, do_timeout=False):
    m = message.author
    U(m.id)["warns"].append(dict(reason=reason, by="AutoMod", level=1, time=now()))
    if do_timeout:
        try:
            await m.timeout(timedelta(minutes=1), reason=reason)
        except Exception:
            pass
    await send_log(message.guild, "AutoMod warn", bot.user, m, reason)
    try:
        await message.channel.send(embed=emb(f"{m.mention} t3ti warn: **{reason}**"), delete_after=8)
    except Exception:
        pass
    await check_warn_thresholds(message.guild, m)

class ConfirmView(discord.ui.View):
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
    @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.success)
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
                await auto_warn(message, "Spam", do_timeout=True)
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
    "3ama": ["`/help`", "`/ping`", "`/profile`", "`/avatar` `/banner`", "`/userinfo` `/serverinfo`", "`/top` `/rank`", "`/afk`", "`/ticket` `/suggest` `/report` `/remind` `/ask`"],
    "flous": ["`/daily` `/balance` `/deposit` `/withdraw` `/transfer`", "`/gamble` `/work` `/rob`", "`/shop` `/buy` `/inventory` `/use`"],
    "al3ab": ["`/8ball` `/rps` `/coinflip` `/dice` `/slot`", "`/truth` `/dare` `/joke` `/meme` `/ship` `/hug`", "`/quiz` `/giveaway` `/poll` `/counting_setup`"],
    "idara": ["`/kick` `/ban` `/unban` `/timeout` `/untimeout`", "`/warn` `/warnings` `/clearwarns`", "`/clear` `/lock` `/unlock` `/slowmode`", "`/send` `/send_rules` `/send_welcome` `/announce` `/setup`", "`/close_ticket` `/add_user`"],
}

@bot.tree.command(name="help", description="Chof ga3 l commands dial l bot")
@app_commands.describe(category="Khtar l9ism li bghiti")
@safe()
async def help_cmd(i: discord.Interaction, category: Literal['3ama', 'flous', 'al3ab', 'idara', 'kolchi'] = 'kolchi'):
    cats = list(HELP) if category == 'kolchi' else [category]
    fields = [(c.upper(), "\n".join(HELP[c]), False) for c in cats]
    await rep(i, embed=emb("Hado homa l commands dial **CYBER HEAVEN**", fields=fields, thumb=MAIN_IMAGE))

@bot.tree.command(name="ping", description="Chof sor3a dial l bot")
@safe()
async def ping_cmd(i: discord.Interaction):
    up = int((now() - START).total_seconds())
    d, rem = divmod(up, 86400)
    h, rem = divmod(rem, 3600)
    mi, s = divmod(rem, 60)
    await rep(i, embed=emb(fields=[("Latency", f"{round(bot.latency * 1000)} ms"), ("Uptime", f"{d}d {h}h {mi}m {s}s"), ("Status", "Online"), ("Servers", str(len(bot.guilds)))]))

@bot.tree.command(name="profile", description="Chof profile dialek")
@safe()
async def profile_cmd(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    u = U(m.id)
    nxt = need(u["level"])
    roles = [r.mention for r in reversed(m.roles) if r != i.guild.default_role][:10]
    await rep(i, embed=emb(f"Profile dial {m.mention}", thumb=m.display_avatar.url, fields=[("Flous", f"Wallet: **{fmt(u['money'])}**\nBank: **{fmt(u['bank'])}**"), ("Level", f"**{u['level']}**"), ("XP", f"{bar(u['xp'], nxt)} {u['xp']}/{nxt}", False), ("Warnings", str(len(u["warns"]))), ("Roles", " ".join(roles) or "Walo", False), ("Badges", " | ".join(get_badges(m, u)), False)]))

@bot.tree.command(name="avatar", description="Chof avatar dial chi wa7ed")
@safe()
async def avatar_cmd(i: discord.Interaction, member: discord.Member = None, size: Literal[128, 256, 512, 1024] = 512):
    m = member or i.user
    url = m.display_avatar.with_size(size).url
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Download", url=url))
    await rep(i, embed=emb(f"Avatar dial {m.mention} ({size}px)", image=url), view=view)

@bot.tree.command(name="userinfo", description="Kol ma3lomat 3la chi member")
@safe()
async def userinfo_cmd(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    await rep(i, embed=emb(f"Info dial {m.mention}", thumb=m.display_avatar.url, fields=[("ID", str(m.id)), ("Created", discord.utils.format_dt(m.created_at, "D")), ("Joined", discord.utils.format_dt(m.joined_at, "D") if m.joined_at else "?"), ("Highest role", m.top_role.mention), ("Status", str(m.status))]))

@bot.tree.command(name="serverinfo", description="Chof ma3lomat dial server")
@safe()
async def serverinfo_cmd(i: discord.Interaction):
    g = i.guild
    online = len([x for x in g.members if x.status != discord.Status.offline])
    bots = len([x for x in g.members if x.bot])
    await rep(i, embed=emb(f"**{g.name}**", thumb=g.icon.url if g.icon else None, fields=[("ID", str(g.id)), ("Owner", f"<@{g.owner_id}>"), ("Members", str(g.member_count)), ("Online", str(online)), ("Bots", str(bots)), ("Channels", str(len(g.channels))), ("Roles", str(len(g.roles)))]))

@bot.tree.command(name="top", description="Classement dial l members")
@safe()
async def top_cmd(i: discord.Interaction, type: Literal['level', 'flous', 'xp', 'warnings'] = 'level', limit: Literal[5, 10, 20] = 10):
    keyf = {"level": lambda u: (u["level"], u["xp"]), "flous": lambda u: u["money"] + u["bank"], "xp": total_xp, "warnings": lambda u: len(u["warns"])}[type]
    shown = {"level": lambda u: f"Level {u['level']}", "flous": lambda u: f"{fmt(u['money'] + u['bank'])} flous", "xp": lambda u: f"{fmt(total_xp(u))} XP", "warnings": lambda u: f"{len(u['warns'])} warns"}[type]
    ordered = sorted(users.items(), key=lambda kv: keyf(kv[1]), reverse=True)[:limit]
    if not ordered:
        return await rep(i, embed=emb("Ba9i walo f classement!"))
    lines = [f"**{n}.** <@{uid}> - {shown(u)}" for n, (uid, u) in enumerate(ordered, 1)]
    await rep(i, embed=emb(f"**Top {limit} - {type}**\n\n" + "\n".join(lines)))

@bot.tree.command(name="rank", description="Chof rank card dialek")
@safe()
async def rank_cmd(i: discord.Interaction):
    u = U(i.user.id)
    nxt = need(u["level"])
    pos, tot = rank_of(i.user.id)
    await rep(i, embed=emb(f"Rank dial {i.user.mention}", thumb=i.user.display_avatar.url, fields=[("Level", str(u["level"])), ("Rank", f"#{pos} / {tot}"), ("XP", f"{bar(u['xp'], nxt, 15)}\n{u['xp']}/{nxt}", False)]))

@bot.tree.command(name="afk", description="Dir rassek AFK")
@safe()
async def afk_cmd(i: discord.Interaction, reason: str = "Ma 3ndi sabab", duration: Literal['10min', '1h', '1day', 'custom'] = '1h', custom_minutes: app_commands.Range[int, 1, 10080] = 30):
    mins = {'10min': 10, '1h': 60, '1day': 1440, 'custom': custom_minutes}[duration]
    afk[i.user.id] = {"reason": reason, "until": now() + timedelta(minutes=mins)}
    await rep(i, embed=emb(f"{i.user.mention} daba AFK: **{reason}** ({mins} dqiqa)"))

JOBS = {"police": ["Mseki lik wa7ed hrami."], "doctor": ["3alajti 3 marda."], "teacher": ["Chr7ti dars."], "gamer": ["Rbe7ti tournoi."], "hacker": ["L9iti bug."], "streamer": ["Dert live."]}
SHOP = {"VIP": ("Role VIP", 5000, "Role VIP"), "Legend": ("Role Legend", 10000, "Role Legend"), "Color": ("Custom Color", 2000, "Color"), "XPBoost": ("XP Boost", 3000, "x2 XP 1h"), "Shield": ("Shield", 1500, "Anti-rob")}
ItemChoice = Literal['VIP', 'Legend', 'Color', 'XPBoost', 'Shield']

@bot.tree.command(name="daily", description="Khod flous dial lyoum")
@safe()
async def daily_cmd(i: discord.Interaction):
    u = U(i.user.id)
    today = now().date()
    if u["daily"] == today:
        return await fail(i, "Derti daily lyoum deja!")
    u["streak"] = u["streak"] + 1 if u["daily"] == today - timedelta(days=1) else 1
    total = random.randint(100, 300) + u["streak"] * 20
    u["money"] += total
    u["daily"] = today
    await rep(i, embed=emb(f"Khditi **{total}** flous! Streak: {u['streak']} yawm"))

@bot.tree.command(name="balance", description="Chof flous dialek")
@safe()
async def balance_cmd(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    u = U(m.id)
    await rep(i, embed=emb(f"Flous dial {m.mention}", fields=[("Wallet", fmt(u["money"])), ("Bank", fmt(u["bank"]))]))

@bot.tree.command(name="deposit", description="Dkhel flous l bank")
@safe()
async def deposit_cmd(i: discord.Interaction, amount: Literal['100', '500', '1000', 'all']):
    u = U(i.user.id)
    amt = u["money"] if amount == "all" else int(amount)
    if amt <= 0 or amt > u["money"]:
        return await fail(i, "Ma 3ndekch had l mablagh.")
    u["money"] -= amt
    u["bank"] += amt
    await rep(i, embed=emb(f"Dkhlti **{fmt(amt)}** l bank."))

@bot.tree.command(name="withdraw", description="Khrej flous mn bank")
@safe()
async def withdraw_cmd(i: discord.Interaction, amount: app_commands.Range[int, 1, 100000000]):
    u = U(i.user.id)
    if amount > u["bank"]:
        return await fail(i, "Ma 3ndekch had l mablagh f bank.")
    u["bank"] -= amount
    u["money"] += amount
    await rep(i, embed=emb(f"Khrjti **{fmt(amount)}** mn bank."))

@bot.tree.command(name="transfer", description="Sift flous l chi wa7ed")
@safe()
async def transfer_cmd(i: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, 100000000]):
    if member.bot or member.id == i.user.id:
        return await fail(i, "Ma tqdarch tsift l rassek.")
    u = U(i.user.id)
    if amount > u["money"]:
        return await fail(i, "Ma 3ndekch flous kafyin.")
    u["money"] -= amount
    U(member.id)["money"] += amount
    await rep(i, embed=emb(f"{i.user.mention} sift **{fmt(amount)}** l {member.mention}"))

@bot.tree.command(name="gamble", description="Lo3b b flous dialek")
@safe()
async def gamble_cmd(i: discord.Interaction, amount: app_commands.Range[int, 1, 1000000], game: Literal['coinflip', 'dice', 'slot', 'roulette'], pick: str = None):
    u = U(i.user.id)
    if amount > u["money"]:
        return await fail(i, "Ma 3ndekch flous kafyin.")
    pick = (pick or "").strip().lower()
    mult, detail = 0, ""
    if game == "coinflip":
        pick = pick if pick in ("ras", "ktaba") else random.choice(["ras", "ktaba"])
        res = random.choice(["ras", "ktaba"])
        mult = 2 if res == pick else 0
        detail = f"Khtarti **{pick}** w tla3 **{res}**"
    elif game == "dice":
        if not pick.isdigit() or not 1 <= int(pick) <= 6:
            return await fail(i, "F dice khtar raqm 1-6.")
        res = random.randint(1, 6)
        mult = 5 if res == int(pick) else 0
        detail = f"Khtarti **{pick}** w tla3 **{res}**"
    elif game == "slot":
        res = [random.choice(["🍒", "🍋", "🍇", "💎"]) for _ in range(3)]
        mult = 10 if len(set(res)) == 1 else 0
        detail = " | ".join(res)
    else:
        if pick not in ("red", "black"):
            return await fail(i, "F roulette khtar red awla black.")
        n = random.randint(0, 36)
        reds = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        col = "green" if n == 0 else ("red" if n in reds else "black")
        mult = 2 if col == pick else 0
        detail = f"Khtarti **{pick}** w tla3 **{n} ({col})**"
    net = amount * (mult - 1)
    u["money"] += net
    await rep(i, embed=emb(f"**{game}**\n{detail}\n\n" + (f"Rbe7ti **{fmt(amount*mult)}**" if mult else f"Khsarti **{fmt(amount)}**")))

@bot.tree.command(name="work", description="Khdem w rbe7 flous")
@safe()
async def work_cmd(i: discord.Interaction, job: Literal['police', 'doctor', 'teacher', 'gamer', 'hacker', 'streamer']):
    u = U(i.user.id)
    left = 3600 - (time.time() - u["work_last"])
    if left > 0:
        return await fail(i, f"Rje3 mn b3d **{int(left//60)} dqiqa**.")
    earn = random.randint(50, 200)
    u["money"] += earn
    u["job"] = job
    u["work_last"] = time.time()
    await rep(i, embed=emb(f"{random.choice(JOBS[job])}\nKhditi **{earn}** flous."))
    await add_xp(i.user, 15)

@bot.tree.command(name="rob", description="7awel tsre9 chi wa7ed")
@safe()
async def rob_cmd(i: discord.Interaction, member: discord.Member):
    if member.bot or member.id == i.user.id:
        return await fail(i, "Ma tqdarch tsre9 l rassek.")
    u, v = U(i.user.id), U(member.id)
    if v["money"] < 100:
        return await fail(i, "Had l member ma 3ndoch flous.")
    if random.random() < 0.4:
        stolen = max(1, int(v["money"] * 0.2))
        v["money"] -= stolen
        u["money"] += stolen
        await rep(i, embed=emb(f"Najaht! Srti **{fmt(stolen)}** mn {member.mention}"))
    else:
        fine = 50
        u["money"] -= fine
        v["money"] += fine
        await rep(i, embed=emb(f"T7bst! Khlst ghrama **{fine}** l {member.mention}"))

@bot.tree.command(name="shop", description="Chof l7anout")
@safe()
async def shop_cmd(i: discord.Interaction):
    fields = [(f"{v[0]} - {fmt(v[1])}", v[2], False) for v in SHOP.values()]
    await rep(i, embed=emb("**L7anout dial CYBER HEAVEN**", fields=fields))

@bot.tree.command(name="buy", description="Chri chi 7aja")
@safe()
async def buy_cmd(i: discord.Interaction, item: ItemChoice):
    u = U(i.user.id)
    label, price, _ = SHOP[item]
    if u["money"] < price:
        return await fail(i, "Ma 3ndekch flous kafyin.")
    u["money"] -= price
    u["inv"].append(item)
    await rep(i, embed=emb(f"Chriti **{label}** b {fmt(price)} flous."))

@bot.tree.command(name="inventory", description="Chof l7wayj dialek")
@safe()
async def inventory_cmd(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    c = Counter(U(m.id)["inv"])
    desc = "\n".join(f"{SHOP[k][0]} x{n}" for k, n in c.items()) or "Inventory khawi."
    await rep(i, embed=emb(f"Inventory dial {m.mention}\n\n{desc}"))

@bot.tree.command(name="use", description="St3mel chi 7aja")
@safe()
async def use_cmd(i: discord.Interaction, item: ItemChoice):
    u = U(i.user.id)
    if item not in u["inv"]:
        return await fail(i, "Ma 3ndekch had l 7aja.")
    if item == "XPBoost":
        u["inv"].remove("XPBoost")
        u["boost"] = time.time() + 3600
        return await rep(i, embed=emb("XP Boost tfa3l: x2 XP l 1 sa3a!"))
    await rep(i, embed=emb(f"St3melti **{item}**."))

BALL = ["Iyeh, 100%", "Bla chak", "Akid", "Ymkn", "Ma3raftch", "La, ma tdirhch", "Kolchi ghadi ymchi l khir", "Sbr w ghadi tchof"]
TRUTHS = ["Achno akbar khta3 dertiha?", "Chkoun akhir wa7ed kteb lik?", "Achno akthar 7aja kat5afha?"]
DARES = ["Sift voice message b sout robot.", "Beddel smiyt dialk l 10 dqayq.", "Kteb poeme 3la CYBER HEAVEN."]

@bot.tree.command(name="8ball", description="Sowel l 8ball")
@safe()
async def eightball_cmd(i: discord.Interaction, question: str):
    await rep(i, embed=emb(fields=[("Souwal", question, False), ("Jawab", random.choice(BALL), False)]))

@bot.tree.command(name="rps", description="Hjar wra9 m9as")
@safe()
async def rps_cmd(i: discord.Interaction, choice: Literal['hjar', 'wra9', 'm9as']):
    COUNTER = {"hjar": "wra9", "wra9": "m9as", "m9as": "hjar"}
    bot_pick = random.choice(list(COUNTER))
    if bot_pick == choice:
        res = "T3adol!"
    elif COUNTER[bot_pick] == choice:
        res = "Rbe7ti!"
    else:
        res = "Khsarti!"
    await rep(i, embed=emb(f"Nta: **{choice}** | Bot: **{bot_pick}**\n\n**{res}**"))

@bot.tree.command(name="coinflip", description="Rmi l 3omla")
@safe()
async def coinflip_cmd(i: discord.Interaction, choice: Literal['ras', 'ktaba']):
    res = random.choice(["ras", "ktaba"])
    await rep(i, embed=emb(f"Khtarti **{choice}** w tla3 **{res}**\n\n" + ("Rbe7ti!" if res == choice else "Khsarti!")))

@bot.tree.command(name="dice", description="Rmi zhar")
@safe()
async def dice_cmd(i: discord.Interaction, sides: Literal[6, 12, 20] = 6):
    res = random.randint(1, sides)
    await rep(i, embed=emb(f"Tla3 **{res}** (d{sides})")))

@bot.tree.command(name="slot", description="Slot machine")
@safe()
async def slot_cmd(i: discord.Interaction):
    res = [random.choice(["🍒", "🍋", "🍇", "💎", "7️⃣"]) for _ in range(3)]
    await rep(i, embed=emb(" | ".join(res) + "\n\n" + ("JACKPOT!" if len(set(res)) == 1 else "3awd jarreb!")))

@bot.tree.command(name="truth", description="Souwal dial l7a9i9a")
@safe()
async def truth_cmd(i: discord.Interaction):
    await rep(i, embed=emb(f"**Truth:** {random.choice(TRUTHS)}"))

@bot.tree.command(name="dare", description="Ta7addi")
@safe()
async def dare_cmd(i: discord.Interaction):
    await rep(i, embed=emb(f"**Dare:** {random.choice(DARES)}"))

@bot.tree.command(name="joke", description="Nokta")
@safe()
async def joke_cmd(i: discord.Interaction):
    await rep(i, embed=emb("Wa7ed 9al l sa7bo: ana dayr regime. 9al lih: kifach? 9al: kan3ti rassi l jou3 7ta ykhlsou l flous."))

@bot.tree.command(name="meme", description="Meme")
@safe()
async def meme_cmd(i: discord.Interaction):
    await rep(i, embed=emb("Change my mind: CYBER HEAVEN a7sen server", image="https://i.imgflip.com/24y43o.jpg"))

@bot.tree.command(name="ship", description="Chhal l7ob bin juj")
@safe()
async def ship_cmd(i: discord.Interaction, member1: discord.Member, member2: discord.Member = None):
    a, b = member1, member2 or i.user
    p = random.Random(min(a.id, b.id) * 31 + max(a.id, b.id)).randint(0, 100)
    await rep(i, embed=emb(f"{a.mention} + {b.mention}\n\n{bar(p, 100, 20)} **{p}%**"))

@bot.tree.command(name="hug", description="Sift hug")
@safe()
async def hug_cmd(i: discord.Interaction, member: discord.Member, type: Literal['hug', 'kiss', 'slap', 'pat'] = 'hug'):
    await rep(i, embed=emb(f"{i.user.mention} {type} {member.mention}"))

@bot.tree.command(name="quiz", description="Quiz")
@safe()
async def quiz_cmd(i: discord.Interaction, category: Literal['general', 'gaming', 'anime', 'football'] = 'general'):
    q = {"general": "Chhal fiha mn nhar f simana? Jawab: 7", "gaming": "Ina lo3ba fiha Creeper? Jawab: Minecraft", "anime": "Chkoun batal Naruto? Jawab: Naruto", "football": "Chkoun rbe7 coupe 2022? Jawab: Argentina"}[category]
    await rep(i, embed=emb(q))

DEL_SECS = {"0": 0, "1day": 86400, "7days": 604800}
TO_MINS = {"1min": 1, "10min": 10, "1h": 60, "1day": 1440}

@bot.tree.command(name="kick", description="Tred chi member")
@app_commands.default_permissions(kick_members=True)
@safe(eph=True, perm="kick_members")
async def kick_cmd(i: discord.Interaction, member: discord.Member, reason: str = "Bla sabab"):
    err = hier_error(i, member)
    if err:
        return await fail(i, err)
    await member.kick(reason=reason)
    await send_log(i.guild, "Kick", i.user, member, reason)
    await rep(i, embed=emb(f"T kicka **{member}**"), ephemeral=True)

@bot.tree.command(name="ban", description="Bani chi member")
@app_commands.default_permissions(ban_members=True)
@safe(eph=True, perm="ban_members")
async def ban_cmd(i: discord.Interaction, member: discord.Member, reason: str = "Bla sabab"):
    err = hier_error(i, member)
    if err:
        return await fail(i, err)
    await i.guild.ban(member, reason=reason)
    await send_log(i.guild, "Ban", i.user, member, reason)
    await rep(i, embed=emb(f"T banna **{member}**"), ephemeral=True)

@bot.tree.command(name="unban", description="Fek l ban b ID")
@app_commands.default_permissions(ban_members=True)
@safe(eph=True, perm="ban_members")
async def unban_cmd(i: discord.Interaction, user_id: str):
    await i.guild.unban(discord.Object(id=int(user_id)))
    await rep(i, embed=emb(f"T fek l ban 3la <@{user_id}>"), ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout")
@app_commands.default_permissions(moderate_members=True)
@safe(eph=True, perm="moderate_members")
async def timeout_cmd(i: discord.Interaction, member: discord.Member, duration: Literal['1min', '10min', '1h', '1day'], reason: str = "Bla sabab"):
    await member.timeout(timedelta(minutes=TO_MINS[duration]), reason=reason)
    await rep(i, embed=emb(f"{member.mention} f timeout l **{duration}**"), ephemeral=True)

@bot.tree.command(name="untimeout", description="Fek timeout")
@app_commands.default_permissions(moderate_members=True)
@safe(eph=True, perm="moderate_members")
async def untimeout_cmd(i: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await rep(i, embed=emb(f"T fek timeout 3la {member.mention}"), ephemeral=True)

@bot.tree.command(name="warn", description="Warn")
@app_commands.default_permissions(moderate_members=True)
@safe(eph=True, perm="moderate_members")
async def warn_cmd(i: discord.Interaction, member: discord.Member, reason: str):
    U(member.id)["warns"].append(dict(reason=reason, by=str(i.user), level=1, time=now()))
    await rep(i, embed=emb(f"{member.mention} t3ta warn. Total: {len(U(member.id)['warns'])}"), ephemeral=True)

@bot.tree.command(name="warnings", description="Chof warns")
@app_commands.default_permissions(moderate_members=True)
@safe(eph=True, perm="moderate_members")
async def warnings_cmd(i: discord.Interaction, member: discord.Member):
    w = U(member.id)["warns"]
    await rep(i, embed=emb(f"Warns dial {member.mention}: {len(w)}"), ephemeral=True)

@bot.tree.command(name="clearwarns", description="Mse7 warns")
@app_commands.default_permissions(moderate_members=True)
@safe(eph=True, perm="moderate_members")
async def clearwarns_cmd(i: discord.Interaction, member: discord.Member):
    U(member.id)["warns"].clear()
    await rep(i, embed=emb(f"T mse7o warns dial {member.mention}"), ephemeral=True)

@bot.tree.command(name="clear", description="Mse7 messages")
@app_commands.default_permissions(manage_messages=True)
@safe(eph=True, perm="manage_messages")
async def clear_cmd(i: discord.Interaction, amount: Literal[5, 10, 20, 50, 100]):
    deleted = await i.channel.purge(limit=amount)
    await rep(i, embed=emb(f"T mse7o **{len(deleted)}** message."), ephemeral=True)

@bot.tree.command(name="lock", description="Sed channel")
@app_commands.default_permissions(manage_channels=True)
@safe(eph=True, perm="manage_channels")
async def lock_cmd(i: discord.Interaction, channel: discord.TextChannel = None):
    ch = channel or i.channel
    ow = ch.overwrites_for(i.guild.default_role)
    ow.send_messages = False
    await ch.set_permissions(i.guild.default_role, overwrite=ow)
    await rep(i, embed=emb(f"T sedd {ch.mention}"), ephemeral=True)

@bot.tree.command(name="unlock", description="7ell channel")
@app_commands.default_permissions(manage_channels=True)
@safe(eph=True, perm="manage_channels")
async def unlock_cmd(i: discord.Interaction, channel: discord.TextChannel = None):
    ch = channel or i.channel
    ow = ch.overwrites_for(i.guild.default_role)
    ow.send_messages = None
    await ch.set_permissions(i.guild.default_role, overwrite=ow)
    await rep(i, embed=emb(f"T fte7 {ch.mention}"), ephemeral=True)

@bot.tree.command(name="slowmode", description="Slowmode")
@app_commands.default_permissions(manage_channels=True)
@safe(eph=True, perm="manage_channels")
async def slowmode_cmd(i: discord.Interaction, seconds: Literal[0, 5, 10, 30, 60], channel: discord.TextChannel = None):
    ch = channel or i.channel
    await ch.edit(slowmode_delay=seconds)
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

@bot.tree.command(name="send", description="Sift embed (ghir mol server)")
@safe(eph=True, owner=True)
async def send_cmd(i: discord.Interaction, message: str, room: discord.TextChannel, couleur: str = "e66cb6", image_link: str = None, title: str = "CYBER HEAVEN", ping: Literal['none', 'everyone', 'here'] = 'none'):
    try:
        await post_embed(room, message, parse_color(couleur), image_link, title, ping, None, None)
    except discord.Forbidden:
        return await fail(i, "Ma 3ndich sla7iya.")
    await rep(i, embed=emb(f"Sift l message l #{room.name} - mra wahda safi!"), ephemeral=True)

@bot.tree.command(name="send_rules", description="Sift l qawanin")
@app_commands.default_permissions(administrator=True)
@safe(eph=True, perm="administrator")
async def send_rules_cmd(i: discord.Interaction):
    ch = i.guild.get_channel(RULES_CHANNEL_ID)
    if not ch:
        return await fail(i, "Ma l9itch channel dial rules.")
    await ch.send(content="|| @everyone ||", embed=rules_embed(), allowed_mentions=discord.AllowedMentions(everyone=True))
    await rep(i, embed=emb(f"Sift l qawanin l #{ch.name}"), ephemeral=True)

@bot.tree.command(name="send_welcome", description="Sift welcome")
@app_commands.default_permissions(administrator=True)
@safe(eph=True, perm="administrator")
async def send_welcome_cmd(i: discord.Interaction):
    ch = i.guild.get_channel(WELCOME_CHANNEL_ID)
    if not ch:
        return await fail(i, "Ma l9itch channel dial welcome.")
    await ch.send(embed=welcome_embed())
    await rep(i, embed=emb(f"Sift welcome l #{ch.name}"), ephemeral=True)

@bot.tree.command(name="announce", description="Sift i3lan")
@app_commands.default_permissions(administrator=True)
@safe(eph=True, perm="administrator")
async def announce_cmd(i: discord.Interaction, message: str, room: discord.TextChannel, couleur: str = "e66cb6", image_link: str = None):
    await post_embed(room, message, parse_color(couleur), image_link, "ANNOUNCEMENT - CYBER HEAVEN", "everyone", None, None)
    await rep(i, embed=emb(f"Sift l i3lan l #{room.name}"), ephemeral=True)

@bot.tree.command(name="setup", description="7ded channel")
@app_commands.default_permissions(administrator=True)
@safe(eph=True, perm="administrator")
async def setup_cmd(i: discord.Interaction, type: Literal['log', 'starboard', 'suggest', 'staff'], channel: discord.TextChannel):
    cfg[type] = channel.id
    await rep(i, embed=emb(f"Channel dial **{type}** daba howa {channel.mention}"), ephemeral=True)

@bot.tree.command(name="ticket", description="7el ticket")
@safe(eph=True)
async def ticket_cmd(i: discord.Interaction, reason: Literal['support', 'report', 'suggestion', 'other'] = 'support'):
    for cid, t in tickets.items():
        if t["owner"] == i.user.id and i.guild.get_channel(cid):
            return await fail(i, f"3ndek ticket deja: <#{cid}>")
    ow = {i.guild.default_role: discord.PermissionOverwrite(view_channel=False), i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True), i.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)}
    name = re.sub(r"[^a-z0-9-]", "", i.user.name.lower()) or str(i.user.id)
    ch = await i.guild.create_text_channel(f"ticket-{name}", overwrites=ow, category=i.channel.category)
    tickets[ch.id] = {"owner": i.user.id, "claimed": None}
    await ch.send(content=i.user.mention, embed=emb(f"Mar7ba bik {i.user.mention}!\nSabab: **{reason}**"))
    await rep(i, embed=emb(f"T7ell ticket dialk: {ch.mention}"), ephemeral=True)

@bot.tree.command(name="close_ticket", description="Sed ticket")
@safe(eph=True)
async def close_ticket_cmd(i: discord.Interaction):
    t = tickets.get(i.channel.id)
    if not t:
        return await fail(i, "Hada machi ticket.")
    tickets.pop(i.channel.id, None)
    await i.channel.delete(reason="Ticket closed")

@bot.tree.command(name="add_user", description="Zid member l ticket")
@safe(eph=True)
async def add_user_cmd(i: discord.Interaction, member: discord.Member):
    await i.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
    await rep(i, embed=emb(f"T zad {member.mention} l ticket."), ephemeral=True)

@bot.tree.command(name="giveaway", description="Dir giveaway")
@app_commands.default_permissions(manage_guild=True)
@safe(eph=True, perm="manage_guild")
async def giveaway_cmd(i: discord.Interaction, prize: str, duration_minutes: Literal[5, 15, 60, 1440], winners: Literal[1, 2, 3] = 1):
    await rep(i, embed=emb(f"Giveaway lanca! Prize: **{prize}** - {winners} winner(s) - {duration_minutes} min"), ephemeral=True)

@bot.tree.command(name="poll", description="Dir sondage")
@app_commands.default_permissions(manage_messages=True)
@safe(eph=True, perm="manage_messages")
async def poll_cmd(i: discord.Interaction, question: str, option1: str, option2: str):
    await rep(i, embed=emb(f"**POLL**\n{question}\n\n1. {option1}\n2. {option2}"), ephemeral=True)

@bot.tree.command(name="counting_setup", description="Counting game")
@app_commands.default_permissions(manage_channels=True)
@safe(eph=True, perm="manage_channels")
async def counting_setup_cmd(i: discord.Interaction, channel: discord.TextChannel):
    counting["channel"] = channel.id
    counting["current"] = 0
    await channel.send(embed=emb("**Counting game!** Bda t3ed mn **1**."))
    await rep(i, embed=emb(f"Counting f {channel.mention} bda!"), ephemeral=True)

@bot.tree.command(name="suggest", description="Sift fikra")
@safe(eph=True)
async def suggest_cmd(i: discord.Interaction, idea: str):
    ch = chan(i.guild, "suggest", ("suggestions", "suggestion")) or i.channel
    await ch.send(embed=emb(f"**Suggestion jdida**\n\n{idea}", fields=[("Mn 3end", i.user.mention)]))
    await rep(i, embed=emb(f"Sift l fikra dialk l {ch.mention}"), ephemeral=True)

@bot.tree.command(name="report", description="Report b secret")
@safe(eph=True)
async def report_cmd(i: discord.Interaction, member: discord.Member, reason: str):
    ch = chan(i.guild, "staff", ("staff", "reports", "report")) or i.channel
    await ch.send(embed=emb("**Report jdid**", fields=[("Member", f"{member.mention}"), ("Sabab", reason, False)]))
    await rep(i, embed=emb("Sift l report l staff."), ephemeral=True)

@bot.tree.command(name="remind", description="Tfkerni")
@safe(eph=True)
async def remind_cmd(i: discord.Interaction, time: Literal['10min', '1h', '1day'], message: str):
    await rep(i, embed=emb(f"Ghadi nfkrek mn b3d **{time}**: {message}"), ephemeral=True)

@bot.tree.command(name="ask", description="Sowel l bot")
@safe()
async def ask_cmd(i: discord.Interaction, question: str):
    await rep(i, embed=emb(fields=[("Souwal", question, False), ("Jawab", random.choice(["Iyeh!", "Sbr w ghadi tchof.", "Dir li katchof mzyan."]), False)]))

@bot.tree.command(name="lyrics", description="Lyrics placeholder")
@safe()
async def lyrics_cmd(i: discord.Interaction, song: str):
    await rep(i, embed=emb(f"**{song}**\n\nPlaceholder lyrics."))

@bot.tree.command(name="nowplaying", description="Now playing placeholder")
@safe()
async def nowplaying_cmd(i: discord.Interaction):
    await rep(i, embed=emb("**Now playing (placeholder)**"))

@bot.tree.command(name="banner", description="Chof banner")
@safe()
async def banner_cmd(i: discord.Interaction, member: discord.Member = None):
    m = member or i.user
    u = await bot.fetch_user(m.id)
    if not u.banner:
        return await fail(i, "Ma 3ndoch banner.")
    await rep(i, embed=emb(f"Banner dial {m.mention}", image=u.banner.url))

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("TOKEN makaynch f Railway Variables!")
else:
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("Token ghalet")
