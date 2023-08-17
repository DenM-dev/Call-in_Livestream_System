import discord
from discord.ext import tasks, commands
from typing import List, Dict
import re
import random
import sqlite3
import time
import os
import shutil

from discord_config import *


class LogsDatabase:
    def __init__(self) -> None:
        self.connection = sqlite3.connect("logs.db")
        self.cursor = self.connection.cursor()

        self.cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='logs'")
        if self.cursor.fetchone()[0]==0:
            ## Table doesn't exist. Create it
            self.cursor.execute("""
CREATE TABLE logs(
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(32),
    mod_id INT,
    mod_username VARCHAR(32),
    mod_display_name VARCHAR(32),
    member_id INT,
    member_username VARCHAR(32),
    member_display_name VARCHAR(32),
    details VARCHAR(250)
)
""")


    def insert_into_db(self, action, mod_id=-1, mod_username="", mod_display_name="", member_id=-1, member_username="", member_display_name="", details=""):
        query = f"""
        INSERT INTO logs
        (action, mod_id, mod_username, mod_display_name, member_id, member_username, member_display_name, details)
        VALUES ('{action}', {mod_id}, '{mod_username}', '{mod_display_name}', {member_id}, '{member_username}', '{member_display_name}', '{details}')
        """
        self.cursor.execute(query)
        self.connection.commit()
        return f"`[{action.upper().ljust(10)}]` "


    def channel_purge(self, mod: discord.Member, channel: discord.TextChannel):
        tag = self.insert_into_db(
            'purge',
            mod_id=mod.id,
            mod_display_name=mod.display_name,
            mod_username=mod.name,
            details=f"#{channel.name} - {channel.id}"
        )
        return tag + f"<#{channel.id}>. Used by `{mod.display_name}` (username: `{mod.name}`)"
    
    
    def clear_all(self, mod: discord.Member):
        tag = self.insert_into_db(
            'clear all',
            mod_id=mod.id,
            mod_display_name=mod.display_name,
            mod_username=mod.name,
        )
        return tag + f"Cleared server and kicked all callers. Used by `{mod.display_name}` (username: `{mod.name}`)"
    

    def clear_unqueued(self, mod: discord.Member):
        tag = self.insert_into_db(
            'clear unq',
            mod_id=mod.id,
            mod_display_name=mod.display_name,
            mod_username=mod.name,
        )
        return tag + f"Removed all unqueued users. Used by `{mod.display_name}` (username: `{mod.name}`)"


    def queue_full(self, member: discord.Member):
        tag = self.insert_into_db(
            'queue full',
            member_id=member.id,
            member_display_name=member.display_name,
            member_username=member.name,
        )
        return tag + f"`{member.display_name}`"


    def user_join(self, member: discord.Member):
        tag = self.insert_into_db(
            'join',
            member_id=member.id,
            member_display_name=member.display_name,
            member_username=member.name
        )
        return tag + f"{member.mention} (`{member.display_name}` — `{member.name}`)"
    

    def user_kick(self, mod: discord.Member, member: discord.Member, reason: str = ""):
        tag = self.insert_into_db(
            'kick',
            member_id=member.id,
            member_display_name=member.display_name,
            member_username=member.name,
            mod_id=mod.id,
            mod_display_name=mod.display_name,
            mod_username=mod.name,
            details=reason
        )
        return tag + f"`{member.display_name}`. Used by `{mod.display_name}` (username: `{mod.name}`. Reason: {reason})"
    

    def user_rename(self, member: discord.Member, new_name: str):
        tag = self.insert_into_db(
            'rename',
            member_id=member.id,
            member_display_name=member.display_name,
            member_username=member.name,
            details=f"{member.display_name} -> {new_name}"
        )
        return tag + f"{member.display_name} -> {new_name}"
    

    def user_role(self, member: discord.Member, role: discord.Role):
        tag = self.insert_into_db(
            'role',
            member_id=member.id,
            member_display_name=member.display_name,
            member_username=member.name,
            details=f"{role.name}"
        )
        return tag + f"Assigned `{role.name}` to `{member.display_name}`"


    def user_verify(self, mod: discord.Member, member: discord.Member):
        tag = self.insert_into_db(
            'verify',
            member_id=member.id,
            member_display_name=member.display_name,
            member_username=member.name,
            mod_id=mod.id,
            mod_display_name=mod.display_name,
            mod_username=mod.name,
        )
        return tag + f"{member.mention} (display: `{member.display_name}`, username: `{member.name}`). Verified by `{mod.display_name}` (username: `{mod.name}`)"

    def user_call(self, member: discord.Member):
        tag = self.insert_into_db(
            'call',
            member_id=member.id,
            member_display_name=member.display_name,
            member_username=member.name,
        )
        return tag + f"{member.mention} (display: `{member.display_name}`, username: `{member.name}`)"

    def user_call_end(self, member: discord.Member):
        tag = self.insert_into_db(
            'call end',
            member_id=member.id,
            member_display_name=member.display_name,
            member_username=member.name,
        )
        return tag + f"{member.mention} (display: `{member.display_name}`, username: `{member.name}`)"


class Captcha:
    def __init__(self):
        self.attempts = 0
        self.question = ""
        self.answer = ""
        self.time_sent = time.time()


class DiscordClient(commands.Bot):
    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default() #discord.Intents.all()
        intents.members = True
        intents.message_content = True
        kwargs.update({"intents": intents})

        kwargs.update({"command_prefix": "!"})
        
        super().__init__(*args, **kwargs)

        self.log = LogsDatabase()
        self.verified_users: List[discord.Member] = []
        self.unverified_users: List[discord.Member] = []
        self.unqueued_users: List[discord.Member] = []
        self.captchas: Dict[discord.Member, Captcha] = {}

        # self.server: discord.Guild = None
        # self.roles: List[discord.Role] = []
        # self.verified_role: discord.Role


    async def on_ready(self):
        print('Logged on as "{0}"'.format(self.user))

        self.server = self.guilds[0]

        caller_pattern = re.compile("Caller [0-9]+$")
        self.roles = [role for role in self.server.roles if caller_pattern.match(role.name)]
        self.roles.sort(key=lambda x: int(x.name[-2:])) ## Sort them from 1 to max
        if len(self.roles) == 0:
            raise Exception("No \"Caller #\" roles exist in this server.")
        
        self.roles = self.roles[:QUEUE_LIMIT]

        self.verified_role = discord.utils.get(self.server.roles, name=f"Verified")
        if self.verified_role is None:
            raise Exception("Verified role does not exist in server")
    
        self.moderator_role = discord.utils.get(self.server.roles, name=f"Moderator")
        if self.moderator_role is None:
            raise Exception("Moderator role does not exist in server")
        
        self.bot_role = discord.utils.get(self.server.roles, name=f"Bot")
        if self.bot_role is None:
            raise Exception("Bot role does not exist in server")
        
        self.moderator_channel = discord.utils.get(self.server.channels, name=f"moderator-only")
        if self.moderator_channel is None:
            raise Exception("#moderator-only text channel does not exist in server")
        
        self.bot_logs_channel = discord.utils.get(self.server.channels, name=f"bot-logs")
        if self.bot_logs_channel is None:
            raise Exception("#bot-logs text channel does not exist in server")
        
        self.live_voice_channel = discord.utils.get(self.server.channels, name=f"live-call")
        if self.live_voice_channel is None:
            raise Exception("#live-call voice channel does not exist in server")

        ## Populate with unverified and verified users (in case we reset the bot midway)
        for user in self.server.members:
            if self.bot_role in user.roles or self.moderator_role in user.roles:
                continue

            if self.verified_role in user.roles:
                self.verified_users.append(user)
                continue
            
            found = False
            for role in user.roles:
                if "Caller" in role.name:
                    self.unverified_users.append(user)
                    found = True
                    break
            
            if not found:
                self.unqueued_users.append(user)
        
        await self.process_unqueued()

        ## Add commands to the context menu
        self.register_commands()
        self.tree.copy_global_to(guild=self.server)
        await self.tree.sync(guild=self.server)

        ## Start background loop
        self.backgroundLoop.start()


    async def on_member_join(self, member: discord.Member):
        ## This requires Intents.members to be enabled.
        msg = self.log.user_join(member=member)
        await self.bot_logs_channel.send(msg)

        ## Don't let anyone sneak in a checkmark in their name to fake verification
        if VERIFICATION_SYMBOL in member.display_name:
            new_name = member.display_name.replace(VERIFICATION_SYMBOL, "_")
            await self.moderator_channel.send(f"{self.moderator_role.mention}. User {member.mention} attempted to join with a name that contains the verification symbol ({VERIFICATION_SYMBOL}). This may be an attempt at deception. The user's nickname has been changed to {new_name}.")
            msg = self.log.user_rename(member=member, new_name=new_name)
            await self.bot_logs_channel.send(msg)
            await member.edit(nick=new_name)

        ## Try to give the user a spot in the queue
        success = await self.assign_slot(member)
        if success:
            return
        
        ## If we can't find a slot, DM the user that there's no space
        ## Tell them to wait until a slot is available
        await member.send(FULL_QUEUE_MESSAGE) # DM the user

        self.unqueued_users.append(member)
        msg = self.log.queue_full(member=member)
        await self.bot_logs_channel.send(msg)

    
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        ## User has joined the channel
        if after.channel and after.channel.name=="live-call" \
            and (before.channel is None or before.channel.name!="live-call") \
            and not self.is_user_mod(member):
            

            ## Save name
            with open(os.path.join(CALLER_DATA_DIR, "caller_name.txt"), 'w', encoding="utf-8") as txt_file:
                name = member.display_name
                if name.startswith(VERIFICATION_SYMBOL):
                    name = name[1:]
                txt_file.write(name)
            
            ## Download pfp
            if member.avatar is None:
                shutil.copy("default_pfp.png", os.path.join(CALLER_DATA_DIR, "caller_pfp.png"))
            else:
                with open(os.path.join(CALLER_DATA_DIR, "caller_pfp.png"), 'wb') as png_file:
                    png_bytes = await member.avatar.read()
                    png_file.write(png_bytes)
            
            self.log.user_call(member)

        ## User has left the channel
        elif before.channel and before.channel.name=="live-call" \
            and (after.channel is None or after.channel.name!="live-call") \
            and not self.is_user_mod(member):

            fname_name = os.path.join(CALLER_DATA_DIR, "caller_name.txt")
            fname_pfp = os.path.join(CALLER_DATA_DIR, "caller_pfp.png")

            # if os.path.exists(fname_name):
            #     os.remove(fname_name)

            ## Save blank name
            with open(os.path.join(CALLER_DATA_DIR, "caller_name.txt"), 'w', encoding="utf-8") as txt_file:
                txt_file.write("")
            
            ## Delete pfp
            if os.path.exists(fname_pfp):
                os.remove(fname_pfp)
            
            self.log.user_call_end(member)


    def is_user_mod(self, user: discord.Member):
        return self.moderator_role in user.roles


    async def send_captcha(self, channel: discord.TextChannel, user: discord.Member):
        if user in self.captchas:
            captcha = self.captchas[user]
        else:
            captcha = Captcha()

        nums = [int(random.uniform(1, 10)), int(random.uniform(1, 10))]
        nums.sort(reverse=True)
        operation = random.choice(["+", "-", "*"])

        equation = f"{nums[0]} {operation} {nums[1]}"

        captcha.question = equation
        captcha.answer = str(eval(equation))
        captcha.attempts += 1
        captcha.time_sent = time.time()
        self.captchas[user] = captcha
        
        await channel.send(f"----\nTo help fight against spam, please answer the following question.\nWhat is {equation} = ?")


    async def assign_slot(self, member: discord.Member) -> bool:
        ## Return True on success
        ## Find the first free queue slot
        for role in self.roles:
            if len(role.members) == 0:
                role_num = int(role.name.split(" ")[1])
                text_channel: discord.TextChannel = discord.utils.get(self.server.channels, name=f"text{role_num}")
                voice_channel: discord.VoiceChannel = discord.utils.get(self.server.channels, name=f"voice{role_num}")

                ## Clear the channel of any earlier messages
                await text_channel.purge(limit=500)

                ## Let the user see the channels
                await member.add_roles(role, reason="Assigned spot in the queue")

                ## Message the user with the intro and rules
                await text_channel.send(ASSIGNED_ROLE_MESSAGE.format(
                    user_id = member.id,
                    voice_channel_id = voice_channel.id
                  )
                )

                if USE_CAPTCHA:
                    await self.send_captcha(text_channel, member)

                self.unverified_users.append(member)

                msg = self.log.user_role(member=member, role=role)
                await self.bot_logs_channel.send(msg)
                return True
        
        return False


    async def on_message(self, message: discord.Message):
        ## Wait for the user to try answering the captcha
        if not USE_CAPTCHA:
            return

        if message.author not in self.captchas:
            return

        member = message.author
        member_captcha = self.captchas[member]
        if self.verified_role in member.roles:
            del self.captchas[member]
        elif message.content == member_captcha.answer:
            await message.channel.send("Thank you. A moderator will be with you shortly.")
            del self.captchas[member]
        elif member_captcha.attempts <= 3:
            await message.channel.send("Incorrect. Try again.")
            await self.send_captcha(message.channel, member)
        else:
            await message.channel.send("Too many failed attempts.")
            await member.kick(reason="Failed to pass captcha after 3 attempts")
            del self.captchas[member]

            msg = self.log.user_kick(self.user, member, "Failed to pass captcha after 3 attempts")
            await self.bot_logs_channel.send(msg)


    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        user = payload.user
        if user in self.unqueued_users:
            self.unqueued_users.remove(user)
        if user in self.unverified_users:
            self.unverified_users.remove(user)
        if user in self.verified_users:
            self.verified_users.remove(user)
        
        await self.process_unqueued()
        
    
    async def process_unqueued(self):
        ## Try processing the rest of the queue
        if len(self.unqueued_users)>0:
            success = await self.assign_slot(self.unqueued_users[0])
            if success:
                del self.unqueued_users[0]


    @tasks.loop(seconds=10)
    async def backgroundLoop(self):
        ## Check if users have replied to the captcha
        ## Give them 2 minutes to do so
        to_delete = []
        for user, captcha in self.captchas.items():
            if self.verified_role in user.roles:
                to_delete.append(user)
            elif time.time() - captcha.time_sent > CAPTCHA_TIMEOUT_SECONDS:
                to_delete.append(user)
                await user.kick(reason=f"Failed to reply to captcha within {CAPTCHA_TIMEOUT_SECONDS} seconds")
                msg = self.log.user_kick(self.user, user, "Failed to reply to captcha within 2 minutes")
                await self.bot_logs_channel.send(msg)
        
        for user in to_delete:
            del self.captchas[user]


    def register_commands(self):
        # discord.Message, discord.User, discord.Member, or a typing.Union of discord.Member and discord.User

        @self.tree.context_menu(name="Purge Channel")
        async def purge(interaction: discord.Interaction, message: discord.Message):
            if not interaction.channel.name.startswith("text"):
                await interaction.response.send_message("You may only purge text channels in the queue", ephemeral=True)
                return
            
            count = 500
            await interaction.channel.purge(limit=count)
            await interaction.response.send_message("Purged", ephemeral=True, delete_after=2)

            msg = self.log.channel_purge(mod=interaction.user, channel=interaction.channel)
            await self.bot_logs_channel.send(msg)
            

        # @self.tree.context_menu(name="End Call with User")
        # async def end_call_with_user(interaction: discord.Interaction, member: discord.Member):
        #     if self.verified_role not in member.roles:
        #         await self.bot_logs_channel.send(f"`[UNVERFIED ]` Cannot move unverified user to call. {member.mention} (display: `{member.display_name}`, username: `{member.name}`)")
        #         await interaction.response.send_message("User is not verified. Could not be moved into the call.", ephemeral=True)
        #         return
            
        #     await member.move_to(None)
        #     await member.send(END_CALL_MESSAGE)
        #     await member.kick()

        #     await self.bot_logs_channel.send(f"`[END CALL  ]` Ended call with {member.mention} (display: `{member.display_name}`, username: `{member.name}`)")
        #     await interaction.response.send_message("Ended live call", ephemeral=True, delete_after=2)


        # @self.tree.context_menu(name="Move User into Call")
        # async def move_to_live_call(interaction: discord.Interaction, member: discord.Member):
        #     if self.verified_role not in member.roles:
        #         await self.bot_logs_channel.send(f"`[UNVERFIED ]` Cannot move unverified user to call. {member.mention} (display: `{member.display_name}`, username: `{member.name}`)")
        #         await interaction.response.send_message("User is not verified. Could not be moved into the call.", ephemeral=True)
        #         return
            
        #     await member.move_to(self.live_voice_channel)
        #     await self.bot_logs_channel.send(f"`[CALL      ]` Moved user in call. {member.mention} (display: `{member.display_name}`, username: `{member.name}`)")
        #     await interaction.response.send_message("Moved user to live call", ephemeral=True, delete_after=2)


        @self.tree.context_menu(name="Verify User")
        async def verify_user(interaction: discord.Interaction, member: discord.Member):
            await member.add_roles(self.verified_role)

            if not member.display_name.startswith(VERIFICATION_SYMBOL):
                new_nick = (VERIFICATION_SYMBOL+member.display_name)[:32]
                await member.edit(nick=new_nick)
            
            if member in self.unverified_users:
                self.unverified_users.remove(member)
            if member not in self.verified_users:
                self.verified_users.append(member)

            msg = self.log.user_verify(member=member, mod=interaction.user)
            await self.bot_logs_channel.send(msg)
            await interaction.response.send_message(f"Verified {member.mention}", ephemeral=True)
            # await interaction.response.send_message(f"Verified {member.mention}", ephemeral=True)
        

        @self.tree.context_menu(name="List Users")
        async def list_users(interaction: discord.Interaction, member: discord.Member):
            # bots = []
            # mods = []
            # users = []
            verified_users = []
            unverified_users = []
            unqueued_users = []

            # for user in self.server.members:
            #     if self.bot_role in user.roles:
            #         bots.append(user.mention)
            #     elif self.moderator_role in user.roles:
            #         mods.append(user.mention)
            #     # else:
            #     #     users.append(user.mention)
            
            def create_string_from_user_list(users):
                if len(users) == 0:
                    return "None"
                return "- " + "\n- ".join(users)

            def get_user_plus_channel(user: discord.Member):
                role_num = 0
                for role in user.roles:
                    if role.name.startswith("Caller"):
                        role_num = int(role.name.split(" ")[1])
                        break
                channel = discord.utils.get(self.server.channels, name=f"text{role_num}")
                return f"{user.mention} — <#{channel.id}>"

            for user in self.verified_users:
                verified_users.append(get_user_plus_channel(user))
            for user in self.unverified_users:
                unverified_users.append(get_user_plus_channel(user))
            for user in self.unqueued_users:
                unqueued_users.append(user.mention)
            
            # bots = create_string_from_user_list(bots)
            # mods = create_string_from_user_list(mods)
            verified_users = create_string_from_user_list(verified_users)
            unverified_users = create_string_from_user_list(unverified_users)
            unqueued_users = create_string_from_user_list(unqueued_users)

            msg = f"""
### Verified\n{verified_users}
### Unverified\n{unverified_users}
### Unqueued\n{unqueued_users}
"""

            await interaction.response.send_message(msg, ephemeral=True)
        

        @self.tree.context_menu(name="Clear All")
        async def clear_all(interaction: discord.Interaction, member: discord.Member):
            if member.id != self.user.id:
                await interaction.response.send_message(f"To clear all users and channels, run this command on {self.user.mention}.", ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True, thinking=True)
            
            msg = self.log.clear_all(mod=interaction.user)
            await self.bot_logs_channel.send(msg)

            for user in self.server.members:
                if self.moderator_role not in user.roles and self.bot_role not in user.roles:
                    await user.send(END_STREAM_MESSAGE)
                    await user.kick()
            
            for role in self.roles:
                role_num = int(role.name.split(" ")[1])
                text_channel = discord.utils.get(self.server.channels, name=f"text{role_num}")
                await text_channel.purge(limit=500)

            ## Clear all invites
            for invite in await self.server.invites():
                await invite.delete()

            # await interaction.response.send_message("Cleared All")
            await interaction.followup.send("Cleared All")
        
        @self.tree.context_menu(name="Remove Unqueued")
        async def remove_unqueued(interaction: discord.Interaction, member: discord.Member):
            if member.id != self.user.id:
                await interaction.response.send_message(f"To clear all unqueued users, run this command on {self.user.mention}.", ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True, thinking=True)
            
            msg = self.log.clear_unqueued(mod=interaction.user)
            await self.bot_logs_channel.send(msg)

            for user in list(self.unqueued_users):
                await user.send(END_STREAM_MESSAGE)
                await user.kick()
            
            ## Clear all invites
            for invite in await self.server.invites():
                await invite.delete()

            await interaction.followup.send("Removed Unqueued")
        
        @self.tree.context_menu(name="Create Invite")
        async def create_invite(interaction: discord.Interaction, member: discord.Member):
            await interaction.response.defer(thinking=True)
            
            text_channel = discord.utils.get(self.server.channels, name=f"general")
            inv = await text_channel.create_invite(max_age=INVITE_DURATION_SECONDS) # Valid for 3 hours

            # await interaction.response.send_message("Cleared All")
            await interaction.followup.send(inv)


if __name__ == "__main__":
    client = DiscordClient()
    client.run(DISCORD_TOKEN)