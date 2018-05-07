# def handle_link(msg):
#     urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', msg.text)
#     # RE_SIMPLE_LINK = re.compile(
#     #     r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",
#     #     re.X | re.I | re.U
#     # )
#     if urls:
#         bot.delete_message(msg.chat.id, msg.message_id)
#         db.event.save({
#             'type': 'delete_link',
#             'chat_id': msg.chat.id,
#             'chat_username': msg.chat.username,
#             'user_id': msg.from_user.id,
#             'username': msg.from_user.username,
#             'date': datetime.utcnow(),
#             'link': {
#                 'links': 'link deleted',
#             },
#         })


# @bot.message_handler(content_types=['sticker', 'document', 'photo', 'audio', 'voice',
#                                     'video', 'location', 'contact', 'video_note'])
# def handle_all_messages(msg):
#     if msg.chat.type in ('channel', 'private'):
#         return
#     # TODO figure out a way to add a link
#     delete_reason = [handle_sticker, handle_document, handle_photo, handle_audio, handle_voice,
#                      handle_video, handle_location, handle_contact, handle_video_note, get_delete_reason(msg)]
#     for delete in delete_reason:
#         to_delete, reason = delete
#         if to_delete:
#             try:
#                 bot.delete_message(msg.chat.id, msg.message_id)
#                 user_display_name = format_user_display_name(msg.from_user)
#                 event_key = (msg.chat.id, msg.from_user.id)
#                 if get_setting(GROUP_CONFIG, msg.chat.id, 'publog', True):
#                     # Notify about spam from same user only one time per hour
#                     if (
#                             event_key not in DELETE_EVENTS
#                             or DELETE_EVENTS[event_key] <
#                             (datetime.utcnow() - timedelta(hours=1))
#                     ):
#                         ret = 'Removed msg from <i>{}</i>. Reason: new user + {}'.format(
#                             html.escape(user_display_name), reason
#                         )
#                         bot.reply_to(msg.chat.id, ret, parse_mode='Markdown')
#                 DELETE_EVENTS[event_key] = datetime.utcnow()
#
#                 # ids = {GLOBAL_LOG_CHANNEL_ID['production']}
#                 # channel_id = get_setting(
#                 #     GROUP_CONFIG, msg.chat.id, 'log_channel_id'
#                 # )
#                 # if channel_id:
#                 #     ids.add(channel_id)
#                 # for chid in ids:
#                 #     formats = get_setting(
#                 #         GROUP_CONFIG, chid, 'logformats', default=['simple']
#                 #     )
#                 #     try:
#                 #         log_event_to_channel(bot, msg, reason, chid, formats)
#                 #     except Exception as ex:
#                 #         logging.exception(
#                 #             'Failed to send notification to channel [{}]'.format(
#                 #                 chid
#                 #             )
#                 #         )
#             except Exception as ex:
#                 db.fail.save({
#                     'date': datetime.utcnow(),
#                     'reason': str(ex),
#                     'traceback': format_exc(),
#                     'chat_id': msg.chat.id,
#                     'msg_id': msg.message_id,
#                 })
#                 if (
#                         'message to delete not found' in str(ex)
#                         # or "message can\'t be deleted" in str(ex)
#                         or "be delete" in str(ex)
#                         or "MESSAGE_ID_INVALID" in str(ex)
#                         or 'message to forward not found' in str(ex)
#                 ):
#                     logging.error('Failed to process spam message: {}'.format(
#                         ex))
#                 else:
#                     raise
