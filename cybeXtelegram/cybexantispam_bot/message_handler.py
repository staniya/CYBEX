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
#
# def log_event_to_channel(bot, msg, reason, chid, formats):
#     if msg.chat.username:
#         from_chatname = '<a href="https://t.me/{}">@{}</a>'.format(
#             msg.chat.username, msg.chat.username
#         )
#     else:
#         from_chatname = '#{}'.format(msg.chat.id)
#     user_display_name = format_user_display_name(msg.from_user)
#     from_info = (
#         'Chat: {}\nUser: <a href=tg://user?id={}">{}</a>'.format(
#             from_chatname, msg.from_user.id, user_display_name)
#     )
#     if 'forward' in formats:
#         try:
#             bot.forward_message(
#                 chid, msg.chat.id, msg.message_id
#             )
#         except Exception as ex:
#             db.fail.save({
#                 'date': datetime.utcnow(),
#                 'reason': str(ex),
#                 'traceback': format_exc(),
#                 'chat_id': msg.chat.id,
#                 'msg_id': msg.message_id,
#             })
#             if (
#                 'MESSAGE_ID_INVALID' in str(ex) or
#                 'message to forward not found' in str(ex)
#             ):
#                 logging.error(
#                     'Failed to forward spam message: {}'.format(ex)
#                 )
#             else:
#                 raise
#     if 'json' in formats:
#         msg_dump = msg.to_dict()
#         msg_dump['meta'] = {
#             'reason': reason,
#             'date': datetime.utcnow(),
#         }
#         dump = jsondate.dumps(msg_dump, indent=4, ensure_ascii=False)
#         dump = html.escape(dump)
#         content = '{}\n<pre>{}</pre>'.format(from_info, dump)
#         try:
#             bot.send_message(chid, content, parse_mode=ParseMode.HTML)
#         except Exception as ex:
#             if 'message is too long' in str(ex):
#                 logging.error('Failed to log message to channel: {}'.format(ex))
#             else:
#                 raise
#         if 'simple' in formats:
#             text = html.escape(msg.text or msg.caption)
#             content = (
#                 '{}\nReason: {}\nContent:\n<pre>{}</pre>'.format(
#                     from_info, reason, text)
#             )
#             bot.send_message(chid, content, parse_mode=ParseMode.HTML)

# def handle_stat(msg):
# if msg.chat.type != 'private':
#     if msg.text.strip() in (
#             '/stat', '/stat@cybexantispamrealbot', '/stat@cybexantispamrealtestbot',
#     ):
#         bot.delete_message(msg.chat.id, msg.message_id)
#     return
# days = []
# top_today = Counter()
# top_ystd = Counter()
# top_week = Counter()
# today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
# for x in range(7):
#     day = today - timedelta(days=x)
#     types = ['delete_sticker', 'delete_document', 'delete_photo', 'delete_audio',
#              'delete_voice', 'delete_video', 'delete_location', 'delete_contact',
#              'delete_video_note', 'delete_link']
#     # TODO fix the format for this
#     for t_type in types:
#         query = {'$and': [
#             {'type': t_type},
#             {'date': {'$gte': day}},
#             {'date': {'$lt': day + timedelta(days=1)}},
#         ]}
#         num = 0
#         for event in db.event.find(query):
#             num += 1
#             key = (
#                 '@%s' % event['chat_username'] if event['chat_username']
#                 else '#%d' % event['chat_id']
#             )
#             if day == today:
#                 top_today[key] += 1
#             if day == (today - timedelta(days=1)):
#                 top_ystd[key] += 1
#             top_week[key] += 1
#         days.insert(0, num)
# ret = 'Recent 7 days: %s' % ' | '.join([str(x) for x in days])
# ret += '\n\nTop today (%d):\n%s' % (
#     len(top_today),
#     '\n'.join('  %s (%d)' % x for x in top_today.most_common()
#               ))
# ret += '\n\nTop yesterday (%d):\n%s' % (
#     len(top_ystd),
#     '\n'.join('  %s (%d)' % x for x in top_ystd.most_common()
#               ))
# ret += '\n\nTop 10 week:\n%s' % '\n'.join('  %s (%d)' % x for x in top_week.most_common(10))
# bot.reply_to(msg, ret)