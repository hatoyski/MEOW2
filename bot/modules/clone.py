import random
import string

from telegram.ext import CommandHandler

from bot import (
    CLONE_LIMIT,
    LOGGER,
    STOP_DUPLICATE,
    Interval,
    dispatcher,
    download_dict,
    download_dict_lock,
)
from bot.helper.ext_utils.bot_utils import new_thread, get_readable_file_size
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot.helper.mirror_utils.upload_utils import gdriveTools
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import *


@new_thread
def cloneNode(update, context):
    args = update.message.text.split(" ", maxsplit=1)
    reply_to = update.message.reply_to_message
    if len(args) > 1:
        link = args[1]
    elif reply_to is not None:
        reply_text = reply_to.text
        link = reply_text.split('\n')[0]
    else:
        link = None
    if link is not None:
        gd = gdriveTools.GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        if res != "":
            sendMessage(res, context.bot, update)
            return
        if STOP_DUPLICATE:
            LOGGER.info("Checking File/Folder if already in Drive...")
            smsg, button = gd.drive_list(name, True, True)
            if smsg:
                msg3 = "Memeriksa File/Folder sudah ada di Drive\nBerikut adalah hasil pencarian:"
                sendMarkup(msg3, context.bot, update, button)
                return
        if CLONE_LIMIT is not None:
            LOGGER.info("Memeriksa Ukuran File/Folder...")
            if size > CLONE_LIMIT * 1024 ** 3:
                msg2 = f"Gagal, batas klon adalah {CLONE_LIMIT}.\nUkuran file/folder Anda {get_readable_file_size(size)}."
                sendMessage(msg2, context.bot, update)
                return
        if files < 10:
            msg = sendMessage(f"Kloning: <code>{link}</code>", context.bot, update)
            result, button = gd.clone(link)
            deleteMessage(context.bot, msg)
        else:
            drive = gdriveTools.GoogleDriveHelper(name)
            gid = ''.join(
                random.SystemRandom().choices(
                    string.ascii_letters + string.digits, k=12
                )
            )
            clone_status = CloneStatus(drive, size, update, gid)
            with download_dict_lock:
                download_dict[update.message.message_id] = clone_status
            sendStatusMessage(update, context.bot)
            result, button = drive.clone(link)
            with download_dict_lock:
                del download_dict[update.message.message_id]
                count = len(download_dict)
            try:
                if count == 0:
                    Interval[0].cancel()
                    del Interval[0]
                    delete_all_messages()
                else:
                    update_all_messages()
            except IndexError:
                pass
        if update.message.from_user.username:
            uname = f"@{update.message.from_user.username}"
        else:
            uname = f'<a href="tg://user?id={update.message.from_user.id}">{update.message.from_user.first_name}</a>'
        if uname is not None:
            cc = f"\n\n<b>Dari: </b>{uname}"
            men = f'{uname} '
        if button in ["cancelled", ""]:
            sendMessage(men + result, context.bot, update)
        else:
            sendMarkup(result + cc, context.bot, update, button)
    else:
        sendMessage(
            "Berikan Tautan yang Dapat Dibagikan G-Drive ke Klon.", context.bot, update
        )


clone_handler = CommandHandler(
    BotCommands.CloneCommand,
    cloneNode,
    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user,
    run_async=True,
)
dispatcher.add_handler(clone_handler)
