import discord
import re
import time
import asyncio
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from typing import List, Optional

class WarView(View):
    def __init__(self, cog, mode: str, march_times: List[int], target_name: str, landing_time: int = 0):
        super().__init__(timeout=None)
        self.cog = cog
        self.mode = mode
        self.march_times = march_times
        self.target_name = target_name
        self.landing_time = landing_time
        self.running = False
        self.current_task = None

    @discord.ui.button(label="🔄 Reset", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def reset_timer(self, interaction: discord.Interaction, button: Button):
        if self.current_task:
            self.current_task.cancel()
            self.current_task = None
        self.running = False
        
        embed = self.cog.generate_embed(
            mode=self.mode,
            times_list=self.march_times, 
            target_name=self.target_name, 
            landing_time=self.landing_time,
            base_ts=int(time.time()), 
            status="preview"
        )
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="🚀 Start Sequence", style=discord.ButtonStyle.danger, emoji="🔥")
    async def start_countdown(self, interaction: discord.Interaction, button: Button):
        if self.running:
            return await interaction.response.send_message("⚠️ Sequence already running!", ephemeral=True)
        
        self.running = True
        await interaction.response.defer()
        self.current_task = asyncio.create_task(self.run_sequence(interaction.message))

    async def run_sequence(self, message: discord.Message):
        try:
            locked_base_ts = int(time.time()) + 5
            
            for i in range(5, 0, -1):
                embed = self.cog.generate_embed(
                    mode=self.mode,
                    times_list=self.march_times, 
                    target_name=self.target_name,
                    landing_time=self.landing_time,
                    base_ts=locked_base_ts,
                    status="countdown", 
                    countdown_val=i
                )
                await message.edit(embed=embed)
                await asyncio.sleep(1.0)

            real_base_ts = int(time.time())

            triggers = []
            max_t = max(self.march_times)
            
            if self.mode == "defense" and self.landing_time > 0:
                impact_time = real_base_ts + self.landing_time
            else:
                impact_time = real_base_ts + max_t

            for t in self.march_times:
                launch_at = impact_time - t
                triggers.append(launch_at)
            
            triggers = sorted(list(set(triggers)))

            for trigger_ts in triggers:
                wait = trigger_ts - time.time()
                if wait > 0:
                    await asyncio.sleep(wait)
                
                embed = self.cog.generate_embed(
                    mode=self.mode,
                    times_list=self.march_times, 
                    target_name=self.target_name,
                    landing_time=self.landing_time,
                    base_ts=real_base_ts,
                    status="active"
                )
                try: await message.edit(embed=embed)
                except: break

        except asyncio.CancelledError:
            pass
        finally:
            self.running = False

class WarCalculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_seconds(self, time_str: str) -> int:
        time_str = str(time_str).lower().strip()
        if time_str.isdigit(): return int(time_str)
        if ":" in time_str:
            parts = time_str.split(":")
            if len(parts) == 2:
                try: return int(parts[0]) * 60 + int(parts[1])
                except: pass
        match_m = re.search(r"(\d+)m", time_str)
        match_s = re.search(r"(\d+)s", time_str)
        s = 0
        if match_m: s += int(match_m.group(1)) * 60
        if match_s: s += int(match_s.group(1))
        return s if s > 0 else 0

    def get_ordinal(self, n: int) -> str:
        if 11 <= (n % 100) <= 13: return f"{n}th"
        return f"{n}{ {1:'st', 2:'nd', 3:'rd'}.get(n%10, 'th') }"

    def generate_embed(
        self, 
        mode: str,
        times_list: List[int], 
        target_name: str, 
        landing_time: int,
        base_ts: int, 
        status: str = "preview",
        countdown_val: int = 0
    ) -> discord.Embed:
        
        current_now = time.time()
        max_t = max(times_list)

        if mode == "defense" and landing_time > 0:
            impact_ts = base_ts + landing_time
            title_prefix = "🛡️ Defense"
            desc_extra = f"🛑 Enemy Landing: **{landing_time}s**"
            main_color = discord.Color.blue()
        else:
            impact_ts = base_ts + max_t
            title_prefix = "⚔️ Attack" if mode == "attack" else "🛡️ Sync Defense"
            desc_extra = f"🐢 Max Travel: **{max_t}s**"
            main_color = discord.Color.dark_red() if mode == "attack" else discord.Color.dark_blue()

        results = []
        for t in times_list:
            launch_ts = impact_ts - t
            wait_seconds = launch_ts - base_ts
            is_go = current_now >= (launch_ts - 0.2)
            is_late = (wait_seconds < 0)

            results.append({
                "travel": t, 
                "wait": wait_seconds, 
                "launch_ts": launch_ts, 
                "is_go": is_go,
                "is_late": is_late
            })
        
        results.sort(key=lambda x: x['wait'])

        if status == "preview":
            desc = f"🎯 Target: **{target_name}**\n{desc_extra}\n(Preview Mode)"
            color = discord.Color.light_grey()
        elif status == "countdown":
            desc = f"# ⚠️ PREPARE: {countdown_val}...\n🎯 Target: **{target_name}**"
            color = discord.Color.orange()
        else:
            desc = f"# 🚀 SEQUENCE ACTIVE\n🎯 Target: **{target_name}**"
            color = discord.Color.green()

        embed = discord.Embed(title=f"{title_prefix} Manager", description=desc, color=color)
        copy_lines = [f"--- {mode.upper()} Plan: {target_name} ---"]

        for index, res in enumerate(results):
            travel = res['travel']
            wait = res['wait']
            launch_ts = int(res['launch_ts'])
            
            t_disp = f"{travel}s"
            if travel >= 60: t_disp += f" ({travel//60}:{travel%60:02d})"

            if index == 0 and not res['is_late']:
                field_name = f"1️⃣ Starter ({t_disp})"
            else:
                field_name = f"{index+1}️⃣ {self.get_ordinal(index+1)} Team ({t_disp})"

            if res['is_late']:
                icon = "💀"
                content = "**TOO LATE!** (Travel > Impact)"
                copy_str = "SKIP"
            else:
                if status == "preview":
                    icon = "🔵"
                    content = "**Start Immediately**" if wait == 0 else f"Wait **{wait}s** after Start"
                    copy_str = "GO NOW" if wait == 0 else f"Wait {wait}s"
                
                elif status == "countdown":
                    icon = "⛔"
                    content = "**STANDBY...**"
                    copy_str = "..."
                
                else:
                    if res['is_go']:
                        icon = "✅"
                        content = "🚀 **MARCH NOW!**"
                        copy_str = "GO!"
                    else:
                        icon = "⏳"
                        content = f"Wait **{wait}s**\n⏰ March: <t:{launch_ts}:T> (**<t:{launch_ts}:R>**)"
                        copy_str = f"Wait {wait}s"

            embed.add_field(name=field_name, value=f"{icon} {content}", inline=False)
            copy_lines.append(f"[Team {index+1}]: {copy_str}")

        embed.add_field(name="📋 Copy Text", value=f"```yaml\n{chr(10).join(copy_lines)}\n```", inline=False)
        
        return embed

    @app_commands.command(name="rally_attack", description="Calculate synchronized attack (Swarm).")
    @app_commands.describe(
        march_times="e.g. '45 30 60'",
        target_name="Target Name"
    )
    async def rally_attack(self, interaction: discord.Interaction, march_times: str, target_name: str = "Enemy"):
        raw = march_times.replace(",", " ").split()
        data = [self.parse_seconds(x) for x in raw if self.parse_seconds(x) > 0]
        
        if len(data) < 2: return await interaction.response.send_message("❌ Need at least 2 times.", ephemeral=True)

        embed = self.generate_embed("attack", data, target_name, 0, int(time.time()), "preview")
        await interaction.response.send_message(embed=embed, view=WarView(self, "attack", data, target_name, 0))

    @app_commands.command(name="rally_defense", description="Calculate defense/reinforcement timing.")
    @app_commands.describe(
        march_times="e.g. '45 30 60'",
        landing_time="Enemy landing in (seconds). Leave 0 for simple sync.",
        target_name="Structure Name"
    )
    async def rally_defense(self, interaction: discord.Interaction, march_times: str, landing_time: int = 0, target_name: str = "Structure"):
        raw = march_times.replace(",", " ").split()
        data = [self.parse_seconds(x) for x in raw if self.parse_seconds(x) > 0]
        
        if len(data) < 1: return await interaction.response.send_message("❌ Need at least 1 time.", ephemeral=True)

        embed = self.generate_embed("defense", data, target_name, landing_time, int(time.time()), "preview")
        await interaction.response.send_message(embed=embed, view=WarView(self, "defense", data, target_name, landing_time))

async def setup(bot):
    await bot.add_cog(WarCalculator(bot))
