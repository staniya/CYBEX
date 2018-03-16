#!/usr/bin/env python
#
# A library that provides a Python interface to the Telegram Bot API
# Copyright (C) 2015-2018
# Leandro Toledo de Souza <devs@python-telegram-bot.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser Public License for more details.
#
# You should have received a copy of the GNU Lesser Public License
# along with this program.  If not, see [http://www.gnu.org/licenses/].
import pytest

from telegram import User, Update


@pytest.fixture(scope='function')
def json_dict():
    return {
        'id': TestUser.id,
        'is_bot': TestUser.is_bot,
        'first_name': TestUser.first_name,
        'last_name': TestUser.last_name,
        'username': TestUser.username,
        'language_code': TestUser.language_code
    }


@pytest.fixture(scope='function')
def user(bot):
    return User(TestUser.id, TestUser.first_name, TestUser.is_bot, last_name=TestUser.last_name,
                username=TestUser.username, language_code=TestUser.language_code, bot=bot)


class TestUser(object):
    id = 1
    is_bot = True
    first_name = 'first_name'
    last_name = 'last_name'
    username = 'username'
    language_code = 'en_us'

    def test_de_json(self, json_dict, bot):
        user = User.de_json(json_dict, bot)

        assert user.id == self.id
        assert user.is_bot == self.is_bot
        assert user.first_name == self.first_name
        assert user.last_name == self.last_name
        assert user.username == self.username
        assert user.language_code == self.language_code

    def test_de_json_without_username(self, json_dict, bot):
        del json_dict['username']

        user = User.de_json(json_dict, bot)

        assert user.id == self.id
        assert user.is_bot == self.is_bot
        assert user.first_name == self.first_name
        assert user.last_name == self.last_name
        assert user.username is None
        assert user.language_code == self.language_code

    def test_de_json_without_username_and_last_name(self, json_dict, bot):
        del json_dict['username']
        del json_dict['last_name']

        user = User.de_json(json_dict, bot)

        assert user.id == self.id
        assert user.is_bot == self.is_bot
        assert user.first_name == self.first_name
        assert user.last_name is None
        assert user.username is None
        assert user.language_code == self.language_code

    def test_name(self, user):
        assert user.name == '@username'
        user.username = None
        assert user.name == 'first_name last_name'
        user.last_name = None
        assert user.name == 'first_name'
        user.username = self.username
        assert user.name == '@username'

    def test_full_name(self, user):
        assert user.full_name == 'first_name last_name'
        user.last_name = None
        assert user.full_name == 'first_name'

    def test_get_profile_photos(self, monkeypatch, user):
        def test(_, *args, **kwargs):
            return args[0] == user.id

        monkeypatch.setattr('telegram.Bot.get_user_profile_photos', test)
        assert user.get_profile_photos()

    def test_instance_method_send_message(self, monkeypatch, user):
        def test(*args, **kwargs):
            return kwargs['chat_id'] == user.id and args[1] == 'test'

        monkeypatch.setattr('telegram.Bot.send_message', test)
        assert user.send_message('test')

    def test_instance_method_send_audio(self, monkeypatch, user):
        def test(*args, **kwargs):
            return kwargs['chat_id'] == user.id and kwargs['audio'] == 'test_audio'

        monkeypatch.setattr('telegram.Bot.send_audio', test)
        assert user.send_audio(audio='test_audio')

    def test_instance_method_send_document(self, monkeypatch, user):
        def test(*args, **kwargs):
            return kwargs['chat_id'] == user.id and kwargs['document'] == 'test_document'

        monkeypatch.setattr('telegram.Bot.send_document', test)
        assert user.send_document(document='test_document')

    def test_instance_method_send_sticker(self, monkeypatch, user):
        def test(*args, **kwargs):
            return kwargs['chat_id'] == user.id and kwargs['sticker'] == 'test_sticker'

        monkeypatch.setattr('telegram.Bot.send_sticker', test)
        assert user.send_sticker(sticker='test_sticker')

    def test_instance_method_send_video(self, monkeypatch, user):
        def test(*args, **kwargs):
            return kwargs['chat_id'] == user.id and kwargs['video'] == 'test_video'

        monkeypatch.setattr('telegram.Bot.send_video', test)
        assert user.send_video(video='test_video')

    def test_instance_method_send_video_note(self, monkeypatch, user):
        def test(*args, **kwargs):
            return kwargs['chat_id'] == user.id and kwargs['video_note'] == 'test_video_note'

        monkeypatch.setattr('telegram.Bot.send_video_note', test)
        assert user.send_video_note(video_note='test_video_note')

    def test_instance_method_send_voice(self, monkeypatch, user):
        def test(*args, **kwargs):
            return kwargs['chat_id'] == user.id and kwargs['voice'] == 'test_voice'

        monkeypatch.setattr('telegram.Bot.send_voice', test)
        assert user.send_voice(voice='test_voice')

    def test_equality(self):
        a = User(self.id, self.first_name, self.is_bot, self.last_name)
        b = User(self.id, self.first_name, self.is_bot, self.last_name)
        c = User(self.id, self.first_name, self.is_bot)
        d = User(0, self.first_name, self.is_bot, self.last_name)
        e = Update(self.id)

        assert a == b
        assert hash(a) == hash(b)
        assert a is not b

        assert a == c
        assert hash(a) == hash(c)

        assert a != d
        assert hash(a) != hash(d)

        assert a != e
        assert hash(a) != hash(e)
