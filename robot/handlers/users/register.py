import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db.utils import IntegrityError
from asgiref.sync import sync_to_async

from aiogram import types
from aiogram.dispatcher import FSMContext

from loader import dp
from const_texts import *

from robot.models import TelegramUser
from robot.states import UserRegister
from robot.keyboards.default import make_buttons, contact_request_button


@dp.message_handler(text=c_register)
async def register(message: types.Message):
    await UserRegister.username.set()
    await message.answer(
        text=c_input_phone_number,
        reply_markup=contact_request_button
    )


@dp.message_handler(state=UserRegister.username, content_types='contact')
async def register(message: types.Message, state: FSMContext):
    phone_number = message.contact.phone_number
    if not phone_number.startswith("+"):
        phone_number = "+" + phone_number

    user = await get_user_model().objects.filter(username=phone_number).afirst()
    if user:
        telegram_user = await TelegramUser.objects.aget(chat_id=message.from_user.id)
        await sync_to_async(telegram_user.set_user)(user)
        await message.answer(
            text=c_successfully_register,
            reply_markup=make_buttons([c_about_us])
        )
        logging.info(f"{user.username} user was successfully connected")
        await state.finish()
        return

    await UserRegister.next()
    await message.answer(
        text=c_input_first_name,
        reply_markup=make_buttons(
            words=[message.from_user.first_name, c_cancel]
        )
    )

    await state.update_data(username=phone_number)


@dp.message_handler(state=UserRegister.first_name)
async def register(message: types.Message, state: FSMContext):
    await UserRegister.next()
    await message.answer(
        text=c_input_last_name,
        reply_markup=make_buttons(
            words=[message.from_user.last_name, c_cancel]
        )
    )
    await state.update_data(first_name=message.text)


@dp.message_handler(state=UserRegister.last_name)
async def register(message: types.Message, state: FSMContext):
    await UserRegister.next()
    await message.answer(
        text=c_input_password,
        reply_markup=make_buttons(
            words=[c_cancel]
        )
    )
    await state.update_data(last_name=message.text)


@dp.message_handler(state=UserRegister.password)
async def register(message: types.Message, state: FSMContext):
    password = message.text
    if len(password) < 4:
        await message.answer(
            text=c_input_password_again
        )
        await message.delete()
        return

    user_info = await state.get_data()

    try:
        user = await get_user_model().objects.acreate(
            username=user_info.get('username'),
            first_name=user_info.get('first_name'),
            last_name=user_info.get('last_name'),
            password=make_password(password)
        )
        telegram_user = await TelegramUser.objects.aget(chat_id=message.from_user.id)
        await sync_to_async(telegram_user.set_user)(user)
        await message.answer(
            text=c_successfully_register,
            reply_markup=make_buttons([c_about_us])
        )
    except IntegrityError:
        await message.answer(
            text=c_registeration_failed,
            reply_markup=make_buttons([c_register])
        )

    await message.delete()
    await state.finish()

    logging.info(f"{user.username} user was successfully created")
