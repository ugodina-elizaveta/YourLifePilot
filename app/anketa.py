from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from app.config import (
    Q1_OPTIONS,
    Q2,
    Q2_TEXT,
    Q3,
    Q3_TEXT,
    Q4,
    Q4_TEXT,
    Q5,
    Q5_TEXT,
    STRESS_OPTIONS,
    TIME_OPTIONS,
    WAKE_OPTIONS,
    user_data_store,
    user_stats_store,
)
from app.database import db
from app.menu import get_keyboard


async def q1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    answer_index = int(data.split('_')[1])
    answer_text = Q1_OPTIONS[answer_index]
    user_data_store[user_id]['answers']['q1'] = answer_text

    if answer_index <= 1:
        if 'плохой сон' not in user_data_store[user_id]['scenario']:
            user_data_store[user_id]['scenario'].append('плохой сон')

    await query.edit_message_text("Ответ записан. Спасибо!")
    await query.message.reply_text(Q2_TEXT, reply_markup=get_keyboard(TIME_OPTIONS, "q2"))
    return Q2


async def q2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    answer_index = int(data.split('_')[1])
    answer_text = TIME_OPTIONS[answer_index]
    user_data_store[user_id]['answers']['q2'] = answer_text

    if answer_index >= 2:
        if 'хочу ложиться поздно' not in user_data_store[user_id]['scenario']:
            user_data_store[user_id]['scenario'].append('хочу ложиться поздно')

    await query.edit_message_text("Ответ записан.")
    await query.message.reply_text(Q3_TEXT, reply_markup=get_keyboard(TIME_OPTIONS, "q3"))
    return Q3


async def q3_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    answer_index = int(data.split('_')[1])
    answer_text = TIME_OPTIONS[answer_index]
    user_data_store[user_id]['answers']['q3'] = answer_text

    if answer_index >= 2:
        if 'ложусь поздно' not in user_data_store[user_id]['scenario']:
            user_data_store[user_id]['scenario'].append('ложусь поздно')

    await query.edit_message_text("Ответ записан.")
    await query.message.reply_text(Q4_TEXT, reply_markup=get_keyboard(WAKE_OPTIONS, "q4"))
    return Q4


async def q4_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    answer_index = int(data.split('_')[1])
    answer_text = WAKE_OPTIONS[answer_index]
    user_data_store[user_id]['answers']['q4'] = answer_text

    if answer_index == 2:
        if 'просыпаюсь разбитым' not in user_data_store[user_id]['scenario']:
            user_data_store[user_id]['scenario'].append('просыпаюсь разбитым')

    await query.edit_message_text("Ответ записан.")
    await query.message.reply_text(Q5_TEXT, reply_markup=get_keyboard(STRESS_OPTIONS, "q5"))
    return Q5


async def q5_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    answer_index = int(data.split('_')[1])
    answer_text = STRESS_OPTIONS[answer_index]
    user_data_store[user_id]['answers']['q5'] = answer_text

    if answer_index == 1:
        if 'днём высокий стресс' not in user_data_store[user_id]['scenario']:
            user_data_store[user_id]['scenario'].append('днём высокий стресс')

    # Онбординг завершен
    user_data_store[user_id]['onboarding_complete'] = True
    user_data_store[user_id]['scenario'] = list(set(user_data_store[user_id]['scenario']))

    # Сохраняем в базу данных (все поля, включая новые)
    await db.save_user(user_id, user_data_store[user_id])
    await db.save_user_stats(user_id, user_stats_store[user_id])

    await db.save_action(
        user_id,
        "onboarding",
        "completed",
        {
            "scenario": user_data_store[user_id]['scenario'],
            "age_group": user_data_store[user_id]['age_group'],
            "occupation": user_data_store[user_id]['occupation'],
        },
    )

    # Финальное сообщение с информацией об AI-чате
    final_message = (
        "🎉 *Спасибо за ответы!* Твой сценарий: "
        f"{', '.join(user_data_store[user_id]['scenario']) if user_data_store[user_id]['scenario'] else 'баланс'}.\n\n"
        "📅 Утренние сообщения будут приходить в *{}*, вечерние — в *{}*.\n\n"
        "🤖 *Важно!* Ты всегда можешь поговорить с AI-помощником.\n"
        "Просто напиши **/ai** и задай любой вопрос о стрессе, сне или просто поболтай.\n\n"
        "Я здесь, чтобы поддержать тебя каждый день! 🌟"
    ).format(user_data_store[user_id]['morning_time'], user_data_store[user_id]['evening_time'])

    await query.edit_message_text(final_message, parse_mode='Markdown')

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Онбординг отменён. Если захочешь начать заново, напиши /start.")
    return ConversationHandler.END
