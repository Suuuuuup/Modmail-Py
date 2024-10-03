import discord
import mysql.connector
from discord.ext import commands
from discord.ui import Button, View

# Configuration du bot et de la base de données
TOKEN = 'TOKEN_DE_TON_BOT'
PREFIX = "+"
MODMAIL_CATEGORY_ID =   # Remplace par l'ID de la catégorie où les tickets seront créés
MODERATOR_ROLE_ID =   # Remplace par l'ID du rôle de modérateur

db_config = {
    'user': '',
    'password': '',
    'host': '',
    'database': ''
}

def connect_db():
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()
        print("✅ Connexion à la base de données réussie !")
        return db, cursor
    except mysql.connector.Error as err:
        print(f"❌ Erreur de connexion à la base de données : {err}")
        return None, None

db, cursor = connect_db()


bot = commands.Bot(command_prefix=PREFIX, intents=discord.Intents.all())


class CloseTicketView(View):
    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.red)
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
        if role in interaction.user.roles:
            query = "SELECT user_id FROM tickets WHERE channel_id = %s"
            cursor.execute(query, (interaction.channel.id,))
            result = cursor.fetchone()

            if result:
                user_id = result[0]
                user = bot.get_user(user_id)

                
                query = "UPDATE tickets SET status = 'closed' WHERE channel_id = %s"
                cursor.execute(query, (interaction.channel.id,))
                db.commit()

                
                if user:
                    try:
                        await user.send("Votre ticket a été fermé par un modérateur.")
                    except discord.Forbidden:
                        print(f"Impossible d'envoyer un message à {user} (DM bloqués).")

            await interaction.response.send_message("Le ticket va être fermé.", ephemeral=True)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("Vous n'avez pas les permissions pour fermer ce ticket.", ephemeral=True)

@bot.event
async def on_ready():
    print("========================================")
    print(f"🎉 {bot.user.name} est prêt à fonctionner !")
    print(f"🤖 Bot ID : {bot.user.id}")
    
    if db and cursor:
        print("💾 Statut de la base de données : Connecté")
    else:
        print("💾 Statut de la base de données : Erreur de connexion")

    print(f"📂 Catégorie de ModMail : {MODMAIL_CATEGORY_ID}")
    print(f"🔧 Préfixe des commandes : {PREFIX}")
    print("========================================")
    print("Le bot est maintenant prêt à recevoir des messages !")

async def restrict_channel_permissions(channel, guild):
    moderator_role = discord.utils.get(guild.roles, id=MODERATOR_ROLE_ID)
    if not moderator_role:
        print(f"❌ Le rôle avec l'ID {MODERATOR_ROLE_ID} n'existe pas.")
        return  
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        moderator_role: discord.PermissionOverwrite(read_messages=True)
    }
    await channel.edit(overwrites=overwrites)

@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel) and not message.author.bot:
        query = "SELECT channel_id FROM tickets WHERE user_id = %s AND status = 'open'"
        cursor.execute(query, (message.author.id,))
        result = cursor.fetchone()

        if result:

            channel = bot.get_channel(result[0])
            if channel:
                await channel.send(f"**{message.author}**: {message.content}")
        else:
            guild = discord.utils.get(bot.guilds)
            category = discord.utils.get(guild.categories, id=MODMAIL_CATEGORY_ID)
            channel = await guild.create_text_channel(f'ticket-{message.author.name}', category=category)

            await restrict_channel_permissions(channel, guild)

            query = "INSERT INTO tickets (user_id, channel_id) VALUES (%s, %s)"
            cursor.execute(query, (message.author.id, channel.id))
            db.commit()

            embed = discord.Embed(title="Ticket ouvert", description=f"Ticket créé pour **{message.author}**.", color=discord.Color.green())
            await channel.send(embed=embed, view=CloseTicketView())

            await channel.send(f"**{message.author}**: {message.content}")
            
        await message.author.send("Votre message a été transmis aux modérateurs.")
    else:
        await bot.process_commands(message)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def reopen(ctx):
    if ctx.channel.category and ctx.channel.category.id == MODMAIL_CATEGORY_ID:
        query = "UPDATE tickets SET status = 'open' WHERE channel_id = %s"
        cursor.execute(query, (ctx.channel.id,))
        db.commit()
        await ctx.send("Le ticket a été rouvert.")
    else:
        await ctx.send("Cette commande ne peut être utilisée que dans un ticket ModMail.")

bot.run(TOKEN)
