import sqlite3

import psycopg2; import discord; from discord.ext import commands;import os; from dotenv import load_dotenv; from discord import app_commands

from banco import Database

load_dotenv()
db = Database()

# python -m pip install -U discord.py
#python -m pip install python-dotenv
# banco  rodada  , escalcao , time , Torneio 
# tem que fazer toda vez os zips por conta do Banco de dados e imagens
intents = discord.Intents.all()
bot = commands.Bot('!', intents=intents)
botao_ativado = False

torneio_nome = "Torneio Draft"; numero_titulares = 8 ; numero_reservas = numero_titulares + 2

def somente_capitao(interaction: discord.Interaction ):
    cargo_capitao = discord.utils.get(interaction.user.roles, name="Capitao")
    return cargo_capitao is not None

@bot.event
async def on_ready():
    print(f'Logged in as ({bot.user.id})')

@bot.command()
async def sinc(ctx):
    comandos = await bot.tree.sync()
    
    print(f"Bot conectado: {bot.user}")
    print("Comandos:")
        
    for comando in comandos:
            print(f"/{comando.name}")
   

@bot.tree.command(description="Escolha os jogadores do seu time para a rodada")
async def time_escalacao(interaction: discord.Interaction, numero_rodada:int):
    escalados = []
    view = discord.ui.View()
    canal = interaction.channel
    nome_cargo = canal.name.replace("-", " ").title()
    print(f"Nome do cargo: {nome_cargo}")
    
    cargo = discord.utils.get(interaction.guild.roles, name=f"{nome_cargo}")
    if cargo is None:
        print(f"Cargo '{nome_cargo}' não encontrado.")
        await interaction.response.send_message("Cargo não encontrado.")
        return

    membros = [member for member in cargo.members]
  
#==============================cria embed=========================================
    embed = discord.Embed(
        title=f"Ola {cargo.name} , escolha seus jogadores para essa semana! ",
        description=f"**Escolha seus jogadores do time {cargo.name} , para essa semana. Boa Sorte a todos!** \n " + f"Escalacao da rodada {numero_rodada}",
        color=discord.Color.blue()
        )
    embed.add_field(
        name=f"", value=' \n  '.join(escalados) if escalados else "Nem um jogador escalado", inline=False 
    )
        
 #==============================adiciona imagem=========================================
    embed.set_image(url=f"attachment://Logo Draft.jpg")
    imagem = discord.File("Logo Draft.jpg","Logo Draft.jpg")
    
#================================cria botao=========================================
    async def cria_botao(membrinhos):
        botao = discord.ui.Button(label=membrinhos.display_name , style=discord.ButtonStyle.primary, custom_id=f"{membrinhos.id}")
        async def botao_nome(interaction: discord.Interaction  , membro = membrinhos , butao = botao):
            
            if not somente_capitao(interaction):
                await interaction.response.send_message("Apenas o capitão pode selecionar os jogadores.", ephemeral=True)
                return
            
            if membro.mention not in escalados:
              escalados.append(f"{membro.mention}")
            butao.disabled = True
            tiulares = escalados[:numero_titulares]
            substituos = escalados[numero_titulares:numero_reservas]
            texto_titulares = "\n".join(tiulares) if tiulares else "Nemnhum jogador escalado, Selecione os nomes de quem vai ser escalado"
            texto_substitutos = "\n".join(substituos) if substituos else "Nemnhum jogador selecionado, escolha seus substitutos"

            embed.set_field_at(
                 index=0,name=f"Titulares do time {cargo.name} ",value=texto_titulares,inline=False)
            if len(embed.fields) > numero_titulares - 1 :
                 embed.set_field_at(
                     index=1,name="Substitutos",value=texto_substitutos,inline=False
                 )
            else:
                    embed.add_field(name="",value="",inline=False
                   )
             
            await interaction.response.edit_message(embed=embed , view=view, allowed_mentions=discord.AllowedMentions(users=True) )

        view.add_item(botao)
        botao.callback = botao_nome
        
    for x in membros:
        await cria_botao(x)
#==============================Confirmar Button=========================================

    confirmbotao = discord.ui.Button(label="Confirmar", style=discord.ButtonStyle.success, custom_id="confirm_button")
    async def confirm_botao(interaction: discord.Interaction  ):
       if not somente_capitao(interaction):
           await interaction.response.send_message("Apenas o capitão pode confirmar a escalação.", ephemeral=True)
           return
       if len(escalados) < numero_reservas:
           await interaction.response.send_message(f"Voce nao selecionou a quantidade suficiente de player para a rodada a quantidade e {numero_reservas}")
           return
           
        # vai mandar a escalacao para o banco de dados
       r_time_sigla = db.execute_query("SELECT sigla FROM timeInfo WHERE time = ?", (nome_cargo,))
       print("r_time_sigla", r_time_sigla)
       
       if r_time_sigla is  None:
           await interaction.response.send_message(f"Não foi possível encontrar a sigla do time {nome_cargo} no banco de dados.", ephemeral=True)
           return
       time_sigla = r_time_sigla[0][0]
       for jogadores in escalados:
           db.insert_query("""INSERT INTO escalacao (rodada, jogador, posicao, time_sigla, torneio_nome) VALUES (?, ?, ?, ?, ?)""", (numero_rodada, jogadores, escalados.index(jogadores)+1, time_sigla, torneio_nome))

       view.clear_items() 
       await interaction.response.edit_message(embed=embed,view=view)

    confirmbotao.callback = confirm_botao
    view.add_item(confirmbotao)


#======================================reset botao=========================================
    resetbutton = discord.ui.Button(label="Reset", style=discord.ButtonStyle.danger, custom_id="reset_button")
    async def reset_botao(interaction: discord.Interaction  ):
        if not somente_capitao(interaction):
            await interaction.response.send_message("Apenas o capitão pode resetar a escalação.", ephemeral=True)
            return
        escalados.clear()
        for item in view.children:
            if isinstance(item, discord.ui.Button) and item.custom_id != "reset_button":
                item.disabled = False
    
        embed.set_field_at(
                   index=0,name=f"Selecione Novamente os player que serao escalados",value="",inline=False 
               )
        embed.set_field_at( index=1 , name= "", value="", inline= False)
        await interaction.response.edit_message(embed=embed , view=view)
        await interaction.followup.send("Botão reset clicado, Sua escalacao foi resetada! Selecione novamente os jogadores.", ephemeral = True) 
    resetbutton.callback = reset_botao
    view.add_item(resetbutton)


#==============================Aparecer as coisas colocadas =========================================
    await interaction.response.send_message(
        view = view , embed = embed , file = imagem)

#atravez do cargo puxar a escalacao do banco de dados e mostrar na tela select time 1 e time 2 
@bot.tree.command(description="Mostra o confronto entre os times")
async def partida(interaction: discord.Interaction, numero_rodada:int, time_a:str, time_b:str):

    resultado =db.execute_query("SELECT jogador FROM escalacao WHERE time_sigla = ? AND rodada = ? ORDER BY posicao", (time_a, numero_rodada))
    

    resultadob =db.execute_query("SELECT jogador FROM escalacao WHERE time_sigla = ? AND rodada = ?", (time_b, numero_rodada))
    
    capitoes_a =db.execute_query("SELECT capitao, vice_capitao FROM timeInfo WHERE sigla = ?",(time_a,))
    
    capitoes_b = db.execute_query("SELECT capitao, vice_capitao FROM timeInfo WHERE sigla = ?",(time_b,))
    
    if capitoes_a:
        capintao_a = capitoes_a[0][0]
        vicepintao_a = capitoes_a[0][1]
        
    if capitoes_b:
        capintao_b = capitoes_b[0][0]
        vicepintao_b = capitoes_b[0][1]
        
    escalacao_a =[linha[0] for linha in resultado];escalacao_b =[linha[0] for linha in resultadob]

    confronto = []
    confronto.append("**TITULARES**")
    for jogador_a,jogador_b in zip(escalacao_a[:numero_titulares],escalacao_b[:numero_titulares]):
            confronto.append(f'{jogador_a} VS {jogador_b} ')
    reservas_a = escalacao_a[numero_titulares:]
    reservas_b = escalacao_b[numero_titulares:]
    confronto.append("")
    confronto.append("**SUBSTITUTOS**")

    if reservas_a:
     confronto.append(
        f"**{time_a.upper()}:** " + " ".join(reservas_a)
    )

    if reservas_b:
     confronto.append(
        f"**{time_b.upper()}:** " + " ".join(reservas_b)
    )
    confronto.append("")
    confronto.append("**CAPITÃES**")
    confronto.append(f"**{time_a.upper()}** : {capintao_a} e {vicepintao_a} \n" + f"**{time_b.upper()}** :{capintao_b} e {vicepintao_b}")
    

    await interaction.response.send_message(
        "**Boa Sorte e bom jogos a todos!** \n " + "\n".join(confronto), allowed_mentions=discord.AllowedMentions(users=True)
    )

@bot.tree.command(description="Adicionar time ao banco de dados SIGLA SER EM MINUSCULO")
async def add_time(interaction: discord.Interaction, time:str, capitao:str, vice_capitao:str, sigla:str):
    
    try:
        db.insert_query("INSERT INTO timeInfo (time, capitao, vice_capitao, sigla) VALUES (?, ?, ?, ?)", (time, capitao, vice_capitao, sigla))

        await interaction.response.send_message(f"Time {time} adicionado com sucesso!", ephemeral=True)
    except sqlite3.IntegrityError:
        await interaction.response.send_message(f"Erro: O time {time} ou a sigla {sigla} já existe no banco de dados.", ephemeral=True)
    

@bot.tree.command(description="Remover time do banco de dados")
async def remove_time(interaction: discord.Interaction, sigla:str):

    db.insert_query("DELETE FROM timeInfo WHERE sigla = ?", (sigla,))
    if db.cursor.rowcount > 0:
        db.conn.commit()
        await interaction.response.send_message(f"Time com sigla {sigla} removido com sucesso!", ephemeral=True)
    else:
        await interaction.response.send_message(f"Erro: Nenhum time encontrado com a sigla {sigla}.", ephemeral=True)
    db.close()
    
@bot.tree.command(description="Limpar todos os dados das tabelas")
async def limpar_tabela(interaction: discord.Interaction):
    db.limpar_tabela("escalacao")
    db.limpar_tabela("timeInfo")
    await interaction.response.send_message("Todas as tabelas foram limpas com sucesso!", ephemeral=True)

bot.run(os.getenv('BOT_TOKEN'))