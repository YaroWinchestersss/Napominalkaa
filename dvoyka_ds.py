import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Словарь для хранения напоминаний
reminders = {}
# Словарь для повторных напоминаний
repeated_reminders = {}

# ID каналов
REMINDER_CHANNEL_ID = 1343276661638168666  # Канал для напоминаний
CREATE_REMINDER_CHANNEL_ID = 1343276686640287754  # Канал для создания напоминаний

@bot.event
async def on_ready():
    print(f'Бот {bot.user} готов к работе!')
    check_reminders.start()

@bot.command(name="напомни")
async def set_reminder(ctx, date: str, time: str, *, message: str):
    # Проверяем, что команда вызвана в правильном канале
    if ctx.channel.id != CREATE_REMINDER_CHANNEL_ID:
        await ctx.send(f"Используйте канал <#{CREATE_REMINDER_CHANNEL_ID}> для создания напоминаний.")
        return

    try:
        # Парсим дату и время
        reminder_time = datetime.strptime(f"{date} {time}", "%d.%m.%Y %H:%M")

        # Проверяем, что время напоминания ещё не прошло
        if reminder_time <= datetime.now():
            await ctx.send("Указанное время уже прошло. Пожалуйста, укажите будущую дату и время.")
            return

        # Сохраняем напоминание
        if ctx.author.id not in reminders:
            reminders[ctx.author.id] = []
        reminders[ctx.author.id].append((reminder_time, message))

        # Вычисляем оставшееся время
        time_left = reminder_time - datetime.now()
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Формируем строку с оставшимся временем
        time_left_str = f"{days} дней, {hours} часов, {minutes} минут"

        await ctx.send(
            f"Напоминание установлено на {reminder_time.strftime('%d.%m.%Y %H:%M')}.\n"
            f"Осталось: {time_left_str}."
        )

    except ValueError:
        await ctx.send("Неверный формат даты или времени. Используйте формат: `!напомни дд.мм.гггг чч:мм <сообщение>`.")

@tasks.loop(seconds=10)
async def check_reminders():
    now = datetime.now()
    for user_id, user_reminders in list(reminders.items()):
        for reminder in list(user_reminders):
            reminder_time, message = reminder
            if now >= reminder_time:
                # Получаем канал для напоминаний
                reminder_channel = bot.get_channel(REMINDER_CHANNEL_ID)
                if reminder_channel:
                    # Упоминаем пользователя три раза с задержкой в 3 секунды
                    for _ in range(3):
                        await reminder_channel.send(f"<@{user_id}>")
                        await asyncio.sleep(3)  # Задержка в 3 секунды

                    # Создаем Embed
                    embed = discord.Embed(
                        title="Напоминание",
                        description=message,
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="Время", value=reminder_time.strftime('%d.%m.%Y %H:%M'), inline=False)
                    embed.set_footer(text="Забудишь -- сосал")

                    # Отправляем Embed
                    reminder_message = await reminder_channel.send(embed=embed)

                    # Добавляем реакции
                    await reminder_message.add_reaction("✅")  # Галочка
                    await reminder_message.add_reaction("❌")  # Крестик

                # Удаляем напоминание из списка
                user_reminders.remove(reminder)

@bot.event
async def on_reaction_add(reaction, user):
    # Проверяем, что реакция добавлена к сообщению с Embed
    if user.bot:  # Игнорируем реакции бота
        return

    if reaction.message.embeds and reaction.message.embeds[0].title == "Напоминание":
        reminder_channel = bot.get_channel(REMINDER_CHANNEL_ID)
        if reminder_channel and reaction.message.channel.id == REMINDER_CHANNEL_ID:
            if str(reaction.emoji) == "❌":  # Если нажат крестик
                await reminder_channel.send(f'<@{user.id}>, Через сколько сделаешь? ("1m" "1h")')

                def check(m):
                    return m.author == user and m.channel == reminder_channel

                try:
                    # Ждем ответа пользователя
                    msg = await bot.wait_for("message", timeout=60, check=check)
                    time_input = msg.content

                    # Парсим время
                    if time_input.endswith('m'):
                        delta = timedelta(minutes=int(time_input[:-1]))
                    elif time_input.endswith('h'):
                        delta = timedelta(hours=int(time_input[:-1]))
                    else:
                        await reminder_channel.send("Неверный формат времени. Используйте, например, '20m' или '1h'.")
                        return

                    # Устанавливаем новое напоминание
                    new_reminder_time = datetime.now() + delta
                    if user.id not in reminders:
                        reminders[user.id] = []
                    reminders[user.id].append((new_reminder_time, reaction.message.embeds[0].description))
                    await reminder_channel.send(f"Новое напоминание установлено на {new_reminder_time.strftime('%d.%m.%Y %H:%M')}.")

                except asyncio.TimeoutError:
                    await reminder_channel.send("Время ожидания истекло. Попробуйте снова.")

            elif str(reaction.emoji) == "✅":  # Если нажата галочка
                # Добавляем пользователя в список для повторных напоминаний
                repeated_reminders[user.id] = reaction.message.embeds[0].description
                await reminder_channel.send(f"<@{user.id}>, Напоминание установлено")

@tasks.loop(minutes=30)
async def repeat_reminders():
    now = datetime.now()
    for user_id, message in list(repeated_reminders.items()):
        reminder_channel = bot.get_channel(REMINDER_CHANNEL_ID)
        if reminder_channel:
            await reminder_channel.send(f"<@{user_id}> {message}")

@bot.command(name="стоп")
async def stop_reminders(ctx):
    if ctx.author.id in repeated_reminders:
        del repeated_reminders[ctx.author.id]
        await ctx.send("Повторные напоминания остановлены.")
    else:
        await ctx.send("У вас нет активных повторных напоминаний.")

bot.run('MTM0MzI3NjE1NTgwNDg0ODEyOA.GhAEOk.pGHygj9pS3Dy-EVDDbPcRNODn8mHBG18j9B7OM')  # Замените на ваш токен